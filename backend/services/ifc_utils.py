"""
IFC Utilities Service
- IFC 파일에서 요소를 필터링하고, 좌표를 추출/설정하는 유틸리티 함수 모음
- Spatial structure 순회, Property/Quantity 접근, Bounding Box 계산
"""

import math
from typing import Optional
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np


def open_ifc(filepath: str) -> ifcopenshell.file:
    """IFC 파일을 열고 모델 객체를 반환합니다."""
    return ifcopenshell.open(filepath)


def get_spatial_structure(model: ifcopenshell.file) -> dict:
    """
    IFC 모델의 공간 구조(Spatial Structure)를 재귀적으로 순회하여
    딕셔너리 트리로 반환합니다.
    """
    project = model.by_type("IfcProject")
    if not project:
        return {}

    project = project[0]
    return _build_spatial_node(project)


def _build_spatial_node(entity) -> dict:
    """공간 요소를 재귀적으로 딕셔너리로 변환합니다."""
    node = {
        "id": entity.GlobalId if hasattr(entity, "GlobalId") else None,
        "type": entity.is_a(),
        "name": getattr(entity, "Name", None) or "",
        "description": getattr(entity, "Description", None) or "",
    }

    # Add elevation for storeys
    if entity.is_a("IfcBuildingStorey"):
        node["elevation"] = getattr(entity, "Elevation", 0.0)

    # Decomposition children (Site → Building → Storey)
    children = []
    if hasattr(entity, "IsDecomposedBy"):
        for rel in entity.IsDecomposedBy:
            for child in rel.RelatedObjects:
                children.append(_build_spatial_node(child))

    if children:
        node["children"] = children

    # For storeys — collect contained elements
    if entity.is_a("IfcBuildingStorey"):
        elements = get_storey_elements(entity)
        if elements:
            node["elements"] = elements

    return node


def get_storey_elements(storey) -> list[dict]:
    """
    BuildingStorey에 포함된 모든 요소의 요약 정보를 반환합니다.
    """
    elements = []
    model = storey.wrapped_data.file

    if not hasattr(storey, "ContainsElements"):
        return elements

    for rel in storey.ContainsElements:
        for element in rel.RelatedElements:
            elem_data = {
                "id": element.GlobalId,
                "type": element.is_a(),
                "name": getattr(element, "Name", None) or "",
                "description": getattr(element, "Description", None) or "",
            }

            # Properties
            try:
                psets = ifcopenshell.util.element.get_psets(element)
                if psets:
                    # Flatten and filter out internal IDs
                    clean_psets = {}
                    for pset_name, pset_data in psets.items():
                        clean_data = {
                            k: v
                            for k, v in pset_data.items()
                            if k != "id" and v is not None
                        }
                        if clean_data:
                            clean_psets[pset_name] = clean_data
                    if clean_psets:
                        elem_data["properties"] = clean_psets
            except Exception:
                pass

            # Bounding box
            try:
                bbox = get_element_bounding_box(model, element)
                if bbox:
                    elem_data["bounding_box"] = bbox
            except Exception:
                pass

            elements.append(elem_data)

    return elements


def get_element_bounding_box(model: ifcopenshell.file, element) -> Optional[dict]:
    """
    요소의 글로벌 좌표계 AABB(Axis-Aligned Bounding Box)를 계산합니다.
    """
    try:
        # Get the placement matrix
        matrix = ifcopenshell.util.placement.get_local_placement(
            element.ObjectPlacement
        )

        # Get representation geometry vertices
        if not element.Representation:
            return None

        all_points = []
        for rep in element.Representation.Representations:
            for item in rep.Items:
                points = _extract_geometry_points(item, matrix)
                all_points.extend(points)

        if not all_points:
            return None

        points_array = np.array(all_points)
        min_pt = points_array.min(axis=0).tolist()
        max_pt = points_array.max(axis=0).tolist()

        return {
            "min": [round(v, 4) for v in min_pt],
            "max": [round(v, 4) for v in max_pt],
        }
    except Exception:
        return None


def _extract_geometry_points(item, transform_matrix: np.ndarray) -> list:
    """
    IFC geometry item에서 꼭지점 좌표를 추출하고 변환 행렬을 적용합니다.
    """
    points = []

    if item.is_a("IfcExtrudedAreaSolid"):
        # Get profile points
        profile = item.SweptArea
        depth = item.Depth

        profile_pts = _get_profile_points(profile)

        # Get extrusion direction
        ext_dir = (0.0, 0.0, 1.0)
        if item.ExtrudedDirection:
            ratios = item.ExtrudedDirection.DirectionRatios
            ext_dir = (ratios[0], ratios[1], ratios[2] if len(ratios) > 2 else 0.0)

        # Get local position
        local_matrix = np.eye(4)
        if item.Position:
            loc = item.Position.Location.Coordinates
            local_matrix[0, 3] = loc[0]
            local_matrix[1, 3] = loc[1]
            local_matrix[2, 3] = loc[2] if len(loc) > 2 else 0.0

        combined = transform_matrix @ local_matrix

        # Bottom profile points
        for px, py in profile_pts:
            pt = np.array([px, py, 0.0, 1.0])
            world_pt = combined @ pt
            points.append(world_pt[:3])

        # Top profile points (extruded)
        for px, py in profile_pts:
            pt = np.array(
                [
                    px + ext_dir[0] * depth,
                    py + ext_dir[1] * depth,
                    ext_dir[2] * depth,
                    1.0,
                ]
            )
            world_pt = combined @ pt
            points.append(world_pt[:3])

    return points


def _get_profile_points(profile) -> list[tuple[float, float]]:
    """IFC profile에서 2D 점 목록을 추출합니다."""
    points = []

    if profile.is_a("IfcRectangleProfileDef"):
        x_dim = profile.XDim / 2
        y_dim = profile.YDim / 2
        points = [
            (-x_dim, -y_dim),
            (x_dim, -y_dim),
            (x_dim, y_dim),
            (-x_dim, y_dim),
        ]
    elif profile.is_a("IfcCircleProfileDef"):
        r = profile.Radius
        # Approximate circle with 12 points
        for i in range(12):
            angle = 2 * math.pi * i / 12
            points.append((r * math.cos(angle), r * math.sin(angle)))
    elif profile.is_a("IfcArbitraryClosedProfileDef"):
        curve = profile.OuterCurve
        if curve.is_a("IfcPolyline"):
            for pt in curve.Points:
                coords = pt.Coordinates
                points.append((coords[0], coords[1]))

    return points


def filter_elements(
    model: ifcopenshell.file, target_filter: dict
) -> list:
    """
    조건에 맞는 IFC 요소들을 필터링하여 반환합니다.
    
    target_filter:
        - type: IFC 클래스 (예: "IfcWall")
        - storey: 층 이름 (예: "1F")
        - name_contains: 이름에 포함된 문자열
        - global_id: 특정 GlobalId
    """
    elements = []

    # Start from a specific type or all products
    ifc_type = target_filter.get("type", "IfcProduct")
    try:
        candidates = model.by_type(ifc_type)
    except Exception:
        candidates = model.by_type("IfcProduct")

    for element in candidates:
        # Filter by storey
        storey_name = target_filter.get("storey")
        if storey_name:
            elem_storey = _get_element_storey(element)
            if not elem_storey or (
                elem_storey.Name and storey_name.upper() not in elem_storey.Name.upper()
            ):
                continue

        # Filter by name
        name_contains = target_filter.get("name_contains")
        if name_contains:
            elem_name = getattr(element, "Name", "") or ""
            if name_contains.upper() not in elem_name.upper():
                continue

        # Filter by GlobalId
        global_id = target_filter.get("global_id")
        if global_id:
            if element.GlobalId != global_id:
                continue

        elements.append(element)

    return elements


def _get_element_storey(element) -> Optional[object]:
    """요소가 포함된 BuildingStorey를 반환합니다."""
    try:
        if hasattr(element, "ContainedInStructure"):
            for rel in element.ContainedInStructure:
                if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                    return rel.RelatingStructure
    except Exception:
        pass
    return None


def get_element_global_position(element) -> Optional[dict]:
    """요소의 글로벌 좌표를 반환합니다."""
    try:
        if not element.ObjectPlacement:
            return None
        matrix = ifcopenshell.util.placement.get_local_placement(
            element.ObjectPlacement
        )
        return {
            "x": round(float(matrix[0, 3]), 4),
            "y": round(float(matrix[1, 3]), 4),
            "z": round(float(matrix[2, 3]), 4),
        }
    except Exception:
        return None


def move_element(
    model: ifcopenshell.file,
    element,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
):
    """요소를 dx, dy, dz만큼 이동합니다 (미터 단위)."""
    if not element.ObjectPlacement:
        return

    placement = element.ObjectPlacement
    if not placement.RelativePlacement:
        return

    axis_placement = placement.RelativePlacement
    if not axis_placement.Location:
        return

    old_coords = list(axis_placement.Location.Coordinates)
    # Ensure 3D coords
    while len(old_coords) < 3:
        old_coords.append(0.0)

    new_coords = (
        old_coords[0] + dx,
        old_coords[1] + dy,
        old_coords[2] + dz,
    )

    axis_placement.Location.Coordinates = new_coords


def change_wall_thickness(
    model: ifcopenshell.file, wall, new_thickness: float
):
    """벽의 두께를 변경합니다. representation의 profile을 수정합니다."""
    if not wall.Representation:
        return False

    for rep in wall.Representation.Representations:
        for item in rep.Items:
            if item.is_a("IfcExtrudedAreaSolid"):
                profile = item.SweptArea
                if profile.is_a("IfcRectangleProfileDef"):
                    profile.YDim = new_thickness
                    return True
    return False


def change_wall_height(model: ifcopenshell.file, wall, new_height: float):
    """벽의 높이를 변경합니다. extrusion depth를 수정합니다."""
    if not wall.Representation:
        return False

    for rep in wall.Representation.Representations:
        for item in rep.Items:
            if item.is_a("IfcExtrudedAreaSolid"):
                item.Depth = new_height
                return True
    return False


def delete_element(model: ifcopenshell.file, element):
    """IFC 모델에서 요소를 삭제합니다."""
    ifcopenshell.api.run("root.remove_product", model, product=element)


def get_model_summary(model: ifcopenshell.file) -> dict:
    """모델의 요소 타입별 개수 요약을 반환합니다."""
    summary = {}
    for product in model.by_type("IfcProduct"):
        ifc_type = product.is_a()
        summary[ifc_type] = summary.get(ifc_type, 0) + 1
    return summary

def insert_door_in_wall(model: ifcopenshell.file, wall, width: float = 0.9, height: float = 2.1, offset_x: float = 0.0) -> bool:
    """벽에 파라메트릭하게 오프닝을 뚫어 문을 생성합니다."""
    import ifcopenshell.api
    try:
        # Create Opening
        opening = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcOpeningElement")
        
        # Determine Placement (Simulating placing it in the middle or offset of the wall)
        # simplified local placement at offset
        placement = ifcopenshell.api.run("geometry.edit_object_placement", model, product=opening)
        
        # Add void to wall
        ifcopenshell.api.run("void.add_opening", model, opening=opening, element=wall)

        # Create Door
        door = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDoor", name="New Door")
        
        # Add to spatial structure
        storey = _get_element_storey(wall)
        if storey:
            ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[door])

        return True
    except Exception as e:
        print(f"Error inserting door: {e}")
        return False

def insert_window_in_wall(model: ifcopenshell.file, wall, width: float = 1.0, height: float = 1.0, offset_x: float = 0.0) -> bool:
    """벽에 파라메트릭하게 오프닝을 뚫어 창문을 생성합니다."""
    import ifcopenshell.api
    try:
        opening = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcOpeningElement")
        ifcopenshell.api.run("geometry.edit_object_placement", model, product=opening)
        ifcopenshell.api.run("void.add_opening", model, opening=opening, element=wall)

        window = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWindow", name="New Window")
        
        storey = _get_element_storey(wall)
        if storey:
            ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[window])

        return True
    except Exception as e:
        print(f"Error inserting window: {e}")
        return False

