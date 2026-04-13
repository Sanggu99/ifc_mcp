"""
IFC Builder Service
- IfcOpenShell API를 사용하여 IFC4 파일을 생성합니다.
- 프로젝트 계층(Project → Site → Building → Storey) 설정
- IfcWall, IfcSlab, IfcColumn 등의 BIM 객체를 Extruded Profile로 생성합니다.
- 단위: 미터(m), 좌표계: IfcLocalPlacement 기반
"""

import uuid
import math
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid
import numpy as np
from typing import Optional

from .dxf_parser import (
    DXFParseResult,
    LineSegment,
    PolylineData,
    Point3D,
)


def _create_guid() -> str:
    return ifcopenshell.guid.compress(uuid.uuid1().hex)


def create_ifc_project(
    project_name: str = "CAD to IFC Project",
    site_name: str = "Default Site",
    building_name: str = "Default Building",
    storey_name: str = "1F",
    storey_elevation: float = 0.0,
) -> tuple:
    """
    새 IFC4 모델을 생성하고 기본 공간 계층을 설정합니다.
    
    Returns:
        (model, project, site, building, storey, body_context) 튜플
    """
    model = ifcopenshell.file(schema="IFC4")

    # Project
    project = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcProject", name=project_name
    )

    # Units — SI (meters)
    ifcopenshell.api.run("unit.assign_unit", model)

    # Geometric representation contexts
    ctx = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    body_context = ifcopenshell.api.run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=ctx,
    )

    # Spatial hierarchy: Site → Building → Storey
    site = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcSite", name=site_name
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, relating_object=project, products=[site]
    )

    building = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuilding", name=building_name
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, relating_object=site, products=[building]
    )

    storey = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuildingStorey", name=storey_name
    )
    storey.Elevation = storey_elevation
    ifcopenshell.api.run(
        "aggregate.assign_object", model, relating_object=building, products=[storey]
    )

    return model, project, site, building, storey, body_context


def create_wall_from_line(
    model,
    storey,
    body_context,
    start: Point3D,
    end: Point3D,
    height: float = 3.0,
    thickness: float = 0.2,
    name: str = "Wall",
) -> object:
    """
    두 점(start, end)을 잇는 선분을 기반으로 IfcWall을 생성합니다.
    벽의 중심선이 선분 위에 놓이며, thickness만큼 양쪽으로 돌출됩니다.
    """
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.sqrt(dx * dx + dy * dy)

    if length < 1e-6:
        return None

    # Wall direction angle
    angle = math.atan2(dy, dx)

    # Create wall entity
    wall = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcWall", name=name
    )

    # Object placement — position at start point, rotated to wall direction
    _set_object_placement(model, wall, storey, start.x, start.y, start.z, angle)

    # Wall representation — extruded rectangle profile
    representation = ifcopenshell.api.run(
        "geometry.add_wall_representation",
        model,
        context=body_context,
        length=length,
        height=height,
        thickness=thickness,
    )
    ifcopenshell.api.run(
        "geometry.assign_representation",
        model,
        product=wall,
        representation=representation,
    )

    # Assign to storey
    ifcopenshell.api.run(
        "spatial.assign_container", model, relating_structure=storey, products=[wall]
    )

    return wall


def create_wall_from_parallel_lines(
    model,
    storey,
    body_context,
    line_a: LineSegment,
    line_b: LineSegment,
    height: float = 3.0,
    name: str = "Wall",
) -> object:
    """
    평행 선분 쌍으로부터 벽을 생성합니다.
    두 선분의 중심선을 벽의 중심으로, 두 선분 사이 거리를 벽 두께로 사용합니다.
    """
    # Centerline start = midpoint of line_a.start and line_b.start
    cx_start = (line_a.start.x + line_b.start.x) / 2
    cy_start = (line_a.start.y + line_b.start.y) / 2
    cz_start = (line_a.start.z + line_b.start.z) / 2

    cx_end = (line_a.end.x + line_b.end.x) / 2
    cy_end = (line_a.end.y + line_b.end.y) / 2
    cz_end = (line_a.end.z + line_b.end.z) / 2

    # Thickness = distance between parallel lines
    dist_start = math.sqrt(
        (line_a.start.x - line_b.start.x) ** 2
        + (line_a.start.y - line_b.start.y) ** 2
    )
    dist_end = math.sqrt(
        (line_a.end.x - line_b.end.x) ** 2 + (line_a.end.y - line_b.end.y) ** 2
    )
    thickness = (dist_start + dist_end) / 2

    return create_wall_from_line(
        model,
        storey,
        body_context,
        start=Point3D(cx_start, cy_start, cz_start),
        end=Point3D(cx_end, cy_end, cz_end),
        height=height,
        thickness=thickness,
        name=name,
    )


def create_slab_from_polyline(
    model,
    storey,
    body_context,
    polyline: PolylineData,
    thickness: float = 0.3,
    name: str = "Slab",
) -> object:
    """
    닫힌 폴리라인으로부터 IfcSlab을 생성합니다.
    폴리라인의 2D 꼭지점들을 ArbitraryClosedProfileDef로 정의하고 하방으로 돌출합니다.
    """
    if len(polyline.points) < 3:
        return None

    slab = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcSlab", name=name
    )

    # Calculate centroid for placement
    pts = polyline.points
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    cz = pts[0].z if pts else 0.0

    _set_object_placement(model, slab, storey, cx, cy, cz, 0.0)

    # Build polyline points relative to centroid
    local_points = [(p.x - cx, p.y - cy) for p in pts]

    # Create arbitrary closed profile
    ifc_points = [model.create_entity("IfcCartesianPoint", Coordinates=[float(px), float(py)]) for px, py in local_points]
    # Close the polyline by appending the first point
    ifc_points.append(ifc_points[0])

    polyline_entity = model.create_entity(
        "IfcPolyline", Points=ifc_points
    )
    profile = model.create_entity(
        "IfcArbitraryClosedProfileDef",
        ProfileType="AREA",
        OuterCurve=polyline_entity,
    )

    # Extrusion direction: downward (negative Z)
    direction = model.create_entity(
        "IfcDirection", DirectionRatios=(0.0, 0.0, -1.0)
    )
    position = model.create_entity(
        "IfcAxis2Placement3D",
        Location=model.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0]),
    )
    solid = model.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=position,
        ExtrudedDirection=direction,
        Depth=thickness,
    )

    shape = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=body_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )
    product_shape = model.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    slab.Representation = product_shape

    # Assign to storey
    ifcopenshell.api.run(
        "spatial.assign_container", model, relating_structure=storey, products=[slab]
    )

    return slab


def create_column(
    model,
    storey,
    body_context,
    position: Point3D,
    radius: float = 0.2,
    height: float = 3.0,
    name: str = "Column",
) -> object:
    """
    원형 단면의 IfcColumn을 생성합니다.
    """
    column = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcColumn", name=name
    )

    _set_object_placement(model, column, storey, position.x, position.y, position.z, 0.0)

    # Circular profile
    profile = model.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Radius=radius,
    )

    direction = model.create_entity(
        "IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)
    )
    axis_position = model.create_entity(
        "IfcAxis2Placement3D",
        Location=model.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0]),
    )
    solid = model.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=axis_position,
        ExtrudedDirection=direction,
        Depth=height,
    )

    shape = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=body_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )
    product_shape = model.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    column.Representation = product_shape

    ifcopenshell.api.run(
        "spatial.assign_container", model, relating_structure=storey, products=[column]
    )

    return column


def create_generic_element(
    model,
    storey,
    body_context,
    polyline: PolylineData,
    height: float = 1.0,
    name: str = "Element",
) -> object:
    """
    분류 불가 요소를 IfcBuildingElementProxy로 생성합니다.
    닫힌 폴리라인의 경우 돌출, 열린 폴리라인의 경우 두께를 주어 돌출합니다.
    """
    if len(polyline.points) < 2:
        return None

    element = ifcopenshell.api.run(
        "root.create_entity",
        model,
        ifc_class="IfcBuildingElementProxy",
        name=name,
    )

    pts = polyline.points
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    cz = pts[0].z if pts else 0.0

    _set_object_placement(model, element, storey, cx, cy, cz, 0.0)

    local_points = [(p.x - cx, p.y - cy) for p in pts]

    if polyline.is_closed and len(pts) >= 3:
        # Closed polyline → arbitrary closed profile extrusion
        ifc_points = [
            model.create_entity("IfcCartesianPoint", Coordinates=[float(px), float(py)])
            for px, py in local_points
        ]
        ifc_points.append(ifc_points[0])
        curve = model.create_entity("IfcPolyline", Points=ifc_points)
        profile = model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            OuterCurve=curve,
        )
    else:
        # Open polyline → thin rectangle along the path (use bounding box)
        min_x = min(p[0] for p in local_points)
        max_x = max(p[0] for p in local_points)
        min_y = min(p[1] for p in local_points)
        max_y = max(p[1] for p in local_points)
        width = max(max_x - min_x, 0.01)
        depth = max(max_y - min_y, 0.01)
        profile = model.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            XDim=width,
            YDim=depth,
        )

    direction = model.create_entity(
        "IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)
    )
    axis_position = model.create_entity(
        "IfcAxis2Placement3D",
        Location=model.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0]),
    )
    solid = model.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=axis_position,
        ExtrudedDirection=direction,
        Depth=height,
    )

    shape = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=body_context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )
    product_shape = model.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    element.Representation = product_shape

    ifcopenshell.api.run(
        "spatial.assign_container", model, relating_structure=storey, products=[element]
    )

    return element


def build_ifc_from_dxf(
    parse_result: DXFParseResult,
    output_path: str,
    wall_height: float = 3.0,
    wall_thickness: float = 0.2,
    slab_thickness: float = 0.3,
    project_name: str = "CAD to IFC Conversion",
) -> dict:
    """
    DXF 파싱 결과를 IFC 파일로 변환합니다.
    
    Returns:
        변환 결과 요약 딕셔너리
    """
    model, project, site, building, storey, body_context = create_ifc_project(
        project_name=project_name,
    )

    stats = {
        "walls": 0,
        "slabs": 0,
        "columns": 0,
        "generic_elements": 0,
        "skipped": 0,
    }

    # ── 1) Create walls from identified parallel line pairs ─────────
    processed_wall_lines = set()
    for idx, (line_a, line_b) in enumerate(parse_result.wall_candidates):
        wall = create_wall_from_parallel_lines(
            model, storey, body_context,
            line_a, line_b,
            height=wall_height,
            name=f"Wall_{idx + 1:03d}",
        )
        if wall:
            stats["walls"] += 1
            processed_wall_lines.add(id(line_a))
            processed_wall_lines.add(id(line_b))

    # ── 2) Create walls from remaining wall-layer lines ──────────────
    for idx, line in enumerate(parse_result.lines):
        if id(line) in processed_wall_lines:
            continue
        if line.ifc_type == "IfcWall":
            wall = create_wall_from_line(
                model, storey, body_context,
                start=line.start,
                end=line.end,
                height=wall_height,
                thickness=wall_thickness,
                name=f"Wall_L_{idx + 1:03d}",
            )
            if wall:
                stats["walls"] += 1

    # ── 3) Create slabs from closed polylines on slab layers ─────────
    for idx, poly in enumerate(parse_result.polylines):
        if poly.ifc_type == "IfcSlab" and poly.is_closed:
            slab = create_slab_from_polyline(
                model, storey, body_context,
                polyline=poly,
                thickness=slab_thickness,
                name=f"Slab_{idx + 1:03d}",
            )
            if slab:
                stats["slabs"] += 1

    # ── 4) Create columns from circles on column layers ──────────────
    for idx, circle in enumerate(parse_result.circles):
        if circle.ifc_type == "IfcColumn":
            col = create_column(
                model, storey, body_context,
                position=circle.center,
                radius=circle.radius,
                height=wall_height,
                name=f"Column_{idx + 1:03d}",
            )
            if col:
                stats["columns"] += 1

    # ── 5) Create generic elements from remaining polylines ──────────
    for idx, poly in enumerate(parse_result.polylines):
        if poly.ifc_type not in ("IfcWall", "IfcSlab", "IfcColumn"):
            elem = create_generic_element(
                model, storey, body_context,
                polyline=poly,
                height=1.0,
                name=f"Element_{idx + 1:03d}",
            )
            if elem:
                stats["generic_elements"] += 1

    # ── 6) Create walls from wall-layer polylines (open) ─────────────
    for idx, poly in enumerate(parse_result.polylines):
        if poly.ifc_type == "IfcWall" and not poly.is_closed and len(poly.points) >= 2:
            # Convert polyline segments to individual walls
            for seg_idx in range(len(poly.points) - 1):
                p1 = poly.points[seg_idx]
                p2 = poly.points[seg_idx + 1]
                wall = create_wall_from_line(
                    model, storey, body_context,
                    start=p1, end=p2,
                    height=wall_height,
                    thickness=wall_thickness,
                    name=f"Wall_P_{idx + 1:03d}_{seg_idx + 1}",
                )
                if wall:
                    stats["walls"] += 1

    # ── Save ──────────────────────────────────────────────────────────
    model.write(output_path)

    stats["total"] = sum(stats.values()) - stats.get("skipped", 0)
    stats["output_path"] = output_path

    return stats


def _set_object_placement(
    model, product, relative_to, x: float, y: float, z: float, angle: float
):
    """
    IFC 요소에 IfcLocalPlacement를 설정합니다.
    
    Args:
        model: IFC model
        product: 배치할 IFC element
        relative_to: 부모 공간 요소 (storey 등)
        x, y, z: 위치 (미터)
        angle: Z축 회전 각도 (라디안)
    """
    # Find parent placement
    parent_placement = None
    if hasattr(relative_to, "ObjectPlacement") and relative_to.ObjectPlacement:
        parent_placement = relative_to.ObjectPlacement

    # Location point
    location = model.create_entity(
        "IfcCartesianPoint", Coordinates=[float(x), float(y), float(z)]
    )

    # Axis (Z-up) and RefDirection (rotated X-axis)
    axis = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    ref_direction = model.create_entity(
        "IfcDirection",
        DirectionRatios=(math.cos(angle), math.sin(angle), 0.0),
    )

    axis_placement = model.create_entity(
        "IfcAxis2Placement3D",
        Location=location,
        Axis=axis,
        RefDirection=ref_direction,
    )

    local_placement = model.create_entity(
        "IfcLocalPlacement",
        PlacementRelTo=parent_placement,
        RelativePlacement=axis_placement,
    )

    product.ObjectPlacement = local_placement
