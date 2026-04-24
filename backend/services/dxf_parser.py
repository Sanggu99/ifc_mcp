"""
DXF Parser Service
- ezdxf를 사용하여 DXF 파일에서 LINE, LWPOLYLINE, CIRCLE, ARC 엔티티를 파싱합니다.
- 레이어 이름 기반으로 BIM 객체 타입을 휴리스틱 매핑합니다.
- 좌표를 mm → m 변환합니다 (DXF는 보통 mm 단위).
"""

import math
from dataclasses import dataclass, field
from typing import Optional
import ezdxf


# ── Layer-to-IFC type mapping ──────────────────────────────────────────────
LAYER_TYPE_MAP = {
    # Wall keywords
    "WALL": "IfcWall",
    "A-WALL": "IfcWall",
    "S-WALL": "IfcWall",
    "RC": "IfcWall",
    "CONC": "IfcWall",
    "WAXM": "IfcWall",
    "벽": "IfcWall",
    # Slab / Floor keywords
    "SLAB": "IfcSlab",
    "FLOOR": "IfcSlab",
    "A-SLAB": "IfcSlab",
    "A-FLOOR": "IfcSlab",
    "바닥": "IfcSlab",
    # Column keywords
    "COLUMN": "IfcColumn",
    "COL": "IfcColumn",
    "A-COLS": "IfcColumn",
    "기둥": "IfcColumn",
    # Door keywords
    "DOOR": "IfcDoor",
    "A-DOOR": "IfcDoor",
    "문": "IfcDoor",
    # Window keywords
    "WINDOW": "IfcWindow",
    "WIN": "IfcWindow",
    "A-GLAZ": "IfcWindow",
    "창": "IfcWindow",
    # Beam keywords
    "BEAM": "IfcBeam",
    "A-BEAM": "IfcBeam",
    "보": "IfcBeam",
    # Stair keywords
    "STAIR": "IfcStair",
    "A-STAIR": "IfcStair",
    "계단": "IfcStair",
}


@dataclass
class Point2D:
    x: float
    y: float


@dataclass
class Point3D:
    x: float
    y: float
    z: float = 0.0


@dataclass
class LineSegment:
    start: Point3D
    end: Point3D
    layer: str = ""
    ifc_type: str = "IfcBuildingElementProxy"
    color: Optional[tuple] = None  # (r, g, b)


@dataclass
class PolylineData:
    points: list[Point3D] = field(default_factory=list)
    is_closed: bool = False
    layer: str = ""
    ifc_type: str = "IfcBuildingElementProxy"
    color: Optional[tuple] = None  # (r, g, b)


@dataclass
class CircleData:
    center: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    radius: float = 0.0
    layer: str = ""
    ifc_type: str = "IfcBuildingElementProxy"


@dataclass
class ArcData:
    center: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    radius: float = 0.0
    start_angle: float = 0.0
    end_angle: float = 360.0
    layer: str = ""
    ifc_type: str = "IfcBuildingElementProxy"


@dataclass
class DXFParseResult:
    """DXF 파싱 결과를 담는 컨테이너"""
    lines: list[LineSegment] = field(default_factory=list)
    polylines: list[PolylineData] = field(default_factory=list)
    circles: list[CircleData] = field(default_factory=list)
    arcs: list[ArcData] = field(default_factory=list)
    layers: dict[str, str] = field(default_factory=dict)   # layer_name → ifc_type
    unit_scale: float = 0.001  # mm → m
    wall_candidates: list = field(default_factory=list)     # 벽 후보 선분 쌍
    slab_candidates: list = field(default_factory=list)     # 슬래브 후보 닫힌 폴리라인


def classify_layer(layer_name: str) -> str:
    """레이어 이름에서 BIM 객체 타입을 추론합니다."""
    upper = layer_name.upper().strip()

    # Exact match first
    if upper in LAYER_TYPE_MAP:
        return LAYER_TYPE_MAP[upper]

    # Partial match (keyword in layer name)
    for keyword, ifc_type in LAYER_TYPE_MAP.items():
        if keyword in upper:
            return ifc_type

    return "IfcBuildingElementProxy"


def detect_unit_scale(doc: ezdxf.document.Drawing) -> float:
    """DXF 파일의 단위를 감지하여 미터로의 변환 계수를 반환합니다."""
    try:
        insunits = doc.header.get("$INSUNITS", 0)
    except Exception:
        insunits = 0

    unit_to_meter = {
        0: 0.001,    # Unitless → assume mm
        1: 0.0254,   # Inches
        2: 0.3048,   # Feet
        3: 1.609344e3,  # Miles (unlikely but handle)
        4: 0.001,    # Millimeters
        5: 0.01,     # Centimeters
        6: 1.0,      # Meters
        7: 1000.0,   # Kilometers
        8: 0.0000254,   # Microinches
        9: 0.001,    # Mils (1/1000 inch) → 0.0000254
        10: 0.9144,  # Yards
        11: 1e-10,   # Angstroms
        12: 1e-9,    # Nanometers
        13: 1e-6,    # Microns
        14: 0.1,     # Decimeters
    }
    return unit_to_meter.get(insunits, 0.001)


def parse_dxf(filepath: str) -> DXFParseResult:
    """
    DXF 파일을 파싱하여 구조화된 데이터를 반환합니다.
    
    레이어 이름이 정리되어 있지 않더라도 지오메트리 형태를 분석하여
    자동으로 벽/슬래브/기둥 등을 추론합니다.
    
    Args:
        filepath: DXF 파일 경로
        
    Returns:
        DXFParseResult: 파싱된 엔티티들과 레이어 정보
    """
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    unit_scale = detect_unit_scale(doc)

    result = DXFParseResult(unit_scale=unit_scale)


    # ── Collect all layers and classify ────────────────────────────────
    has_known_layers = False
    for layer in doc.layers:
        layer_name = layer.dxf.name
        ifc_type = classify_layer(layer_name)
        result.layers[layer_name] = ifc_type
        if ifc_type != "IfcBuildingElementProxy":
            has_known_layers = True

    # 레이어 색상 캐시 (ACI)
    layer_aci_map = {layer.dxf.name: layer.color for layer in doc.layers}


    # ── Parse LINE entities ────────────────────────────────────────────

    for entity in msp.query("LINE"):
        layer_name = entity.dxf.layer
        ifc_type = result.layers.get(layer_name, classify_layer(layer_name))

        start = entity.dxf.start
        end = entity.dxf.end

        # 색상 추출: true color → 엔티티 ACI → 레이어 ACI
        color = None
        try:
            aci = getattr(entity.dxf, 'color', None)
            true_color = getattr(entity.dxf, 'true_color', None)
            layer_aci = layer_aci_map.get(layer_name)
            print(f"[DEBUG] LINE layer={layer_name} entity.aci={aci} entity.true_color={true_color} layer_aci={layer_aci}")
            if true_color:
                color = ezdxf.colors.int2rgb(true_color)
            else:
                if not aci or aci in (0, 256):
                    aci = layer_aci
                if aci and aci not in (0, 256):
                    color = ezdxf.colors.aci_to_true_color(aci)
            print(f"[DEBUG] LINE FINAL layer={layer_name} color={color}")
        except Exception as e:
            print(f"[ERROR] LINE color extract: {e}")
            color = None

        line = LineSegment(
            start=Point3D(
                x=start.x * unit_scale,
                y=start.y * unit_scale,
                z=start.z * unit_scale,
            ),
            end=Point3D(
                x=end.x * unit_scale,
                y=end.y * unit_scale,
                z=end.z * unit_scale,
            ),
            layer=layer_name,
            ifc_type=ifc_type,
            color=color,
        )
        result.lines.append(line)



    # ── Parse LWPOLYLINE entities ──────────────────────────────────────

    for entity in msp.query("LWPOLYLINE"):
        layer_name = entity.dxf.layer
        ifc_type = result.layers.get(layer_name, classify_layer(layer_name))

        points = []
        for x, y in entity.get_points(format="xy"):
            points.append(Point3D(
                x=x * unit_scale,
                y=y * unit_scale,
                z=0.0,
            ))

        is_closed = entity.closed
        color = None
        try:
            aci = getattr(entity.dxf, 'color', None)
            true_color = getattr(entity.dxf, 'true_color', None)
            layer_aci = layer_aci_map.get(layer_name)
            print(f"[DEBUG] LWPOLYLINE layer={layer_name} entity.aci={aci} entity.true_color={true_color} layer_aci={layer_aci}")
            if true_color:
                color = ezdxf.colors.int2rgb(true_color)
            else:
                if not aci or aci in (0, 256):
                    aci = layer_aci
                if aci and aci not in (0, 256):
                    color = ezdxf.colors.aci_to_true_color(aci)
            print(f"[DEBUG] LWPOLYLINE FINAL layer={layer_name} color={color}")
        except Exception as e:
            print(f"[ERROR] LWPOLYLINE color extract: {e}")
            color = None

        poly = PolylineData(
            points=points,
            is_closed=is_closed,
            layer=layer_name,
            ifc_type=ifc_type,
            color=color,
        )
        result.polylines.append(poly)

        # 닫힌 폴리라인은 슬래브 후보
        if is_closed and ifc_type in ("IfcSlab", "IfcBuildingElementProxy"):
            result.slab_candidates.append(poly)

    # ── Parse POLYLINE (3D) entities ───────────────────────────────────
    for entity in msp.query("POLYLINE"):
        layer_name = entity.dxf.layer
        ifc_type = result.layers.get(layer_name, classify_layer(layer_name))

        points = []
        for vertex in entity.vertices:
            loc = vertex.dxf.location
            points.append(Point3D(
                x=loc.x * unit_scale,
                y=loc.y * unit_scale,
                z=loc.z * unit_scale,
            ))

        is_closed = entity.is_closed
        poly = PolylineData(
            points=points,
            is_closed=is_closed,
            layer=layer_name,
            ifc_type=ifc_type,
        )
        result.polylines.append(poly)

    # ── Parse CIRCLE entities ──────────────────────────────────────────
    for entity in msp.query("CIRCLE"):
        layer_name = entity.dxf.layer
        ifc_type = result.layers.get(layer_name, classify_layer(layer_name))

        center = entity.dxf.center
        circle = CircleData(
            center=Point3D(
                x=center.x * unit_scale,
                y=center.y * unit_scale,
                z=center.z * unit_scale,
            ),
            radius=entity.dxf.radius * unit_scale,
            layer=layer_name,
            ifc_type=ifc_type,
        )
        result.circles.append(circle)

    # ── Parse ARC entities ─────────────────────────────────────────────
    for entity in msp.query("ARC"):
        layer_name = entity.dxf.layer
        ifc_type = result.layers.get(layer_name, classify_layer(layer_name))

        center = entity.dxf.center
        arc = ArcData(
            center=Point3D(
                x=center.x * unit_scale,
                y=center.y * unit_scale,
                z=center.z * unit_scale,
            ),
            radius=entity.dxf.radius * unit_scale,
            start_angle=entity.dxf.start_angle,
            end_angle=entity.dxf.end_angle,
            layer=layer_name,
            ifc_type=ifc_type,
        )
        result.arcs.append(arc)

    # ── Geometry-based auto-classification ─────────────────────────────
    # 레이어 이름이 정리되지 않은 경우, 지오메트리를 분석하여 자동 분류
    if not has_known_layers:
        _auto_classify_by_geometry(result)
    else:
        # 명시적 벽 레이어의 선분만 벽 후보로 검색
        wall_lines = [l for l in result.lines if l.ifc_type == "IfcWall"]
        result.wall_candidates = _find_wall_line_pairs(wall_lines)

    return result


def _auto_classify_by_geometry(result: DXFParseResult):
    """
    레이어 이름이 정리되지 않은 DXF 파일에서
    지오메트리 형태를 분석하여 BIM 객체 타입을 자동으로 추론합니다.
    
    1) 모든 LINE에서 평행 선분 쌍 → 벽(IfcWall)
    2) 닫힌 직사각형 폴리라인(넓은 면적) → 슬래브(IfcSlab)
    3) 작은 원 → 기둥(IfcColumn)
    4) 나머지 선분 → 벽으로 취급 (건축 CAD의 대부분이 벽)
    """
    # 1) 모든 LINE에서 벽 후보(평행 선분 쌍) 찾기
    result.wall_candidates = _find_wall_line_pairs(result.lines)
    
    # 벽 후보로 선택된 선분은 IfcWall로 재분류
    wall_line_ids = set()
    for line_a, line_b in result.wall_candidates:
        line_a.ifc_type = "IfcWall"
        line_b.ifc_type = "IfcWall"
        wall_line_ids.add(id(line_a))
        wall_line_ids.add(id(line_b))

    # 2) 닫힌 폴리라인 분석
    for poly in result.polylines:
        if not poly.is_closed or len(poly.points) < 3:
            continue

        area = _polygon_area(poly.points)
        perimeter = _polygon_perimeter(poly.points)

        if area < 0.01:  # 너무 작은 폴리라인은 무시
            continue

        # 큰 면적의 직사각형 → 슬래브
        # aspect ratio가 합리적이고 면적이 2㎡ 이상이면 슬래브
        if area > 2.0 and len(poly.points) == 4:
            poly.ifc_type = "IfcSlab"
            result.slab_candidates.append(poly)
        elif area > 5.0:
            # 면적이 크면 슬래브
            poly.ifc_type = "IfcSlab"
            result.slab_candidates.append(poly)
        elif perimeter > 0 and area / perimeter < 0.15:
            # 좁고 긴 닫힌 폴리라인 → 벽의 외곽선일 가능성
            poly.ifc_type = "IfcWall"
        else:
            poly.ifc_type = "IfcBuildingElementProxy"

    # 3) 작은 원 → 기둥
    for circle in result.circles:
        if 0.05 <= circle.radius <= 0.5:
            circle.ifc_type = "IfcColumn"
        elif circle.radius < 0.05:
            circle.ifc_type = "IfcBuildingElementProxy"

    # 4) 벽 후보가 아닌 나머지 LINE → 벽으로 추론
    #    건축 CAD 도면에서 대부분의 선분은 벽을 나타냄
    for line in result.lines:
        if id(line) not in wall_line_ids and line.ifc_type == "IfcBuildingElementProxy":
            line_length = math.sqrt(
                (line.end.x - line.start.x) ** 2 +
                (line.end.y - line.start.y) ** 2
            )
            # 0.3m~50m 길이의 선분은 벽으로 간주
            if 0.3 <= line_length <= 50.0:
                line.ifc_type = "IfcWall"

    # 레이어 분류 결과 업데이트
    layer_types = {}
    for line in result.lines:
        if line.layer not in layer_types:
            layer_types[line.layer] = {}
        layer_types[line.layer][line.ifc_type] = layer_types[line.layer].get(line.ifc_type, 0) + 1
    for poly in result.polylines:
        if poly.layer not in layer_types:
            layer_types[poly.layer] = {}
        layer_types[poly.layer][poly.ifc_type] = layer_types[poly.layer].get(poly.ifc_type, 0) + 1

    # 각 레이어의 최다 타입으로 레이어 분류 업데이트
    for layer_name, type_counts in layer_types.items():
        if type_counts:
            dominant_type = max(type_counts, key=type_counts.get)
            result.layers[layer_name] = f"{dominant_type} (auto-detected)"


def _polygon_area(points: list[Point3D]) -> float:
    """다각형의 면적을 Shoelace formula로 계산합니다 (㎡)."""
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i].x * points[j].y
        area -= points[j].x * points[i].y
    return abs(area) / 2.0


def _polygon_perimeter(points: list[Point3D]) -> float:
    """다각형의 둘레를 계산합니다 (m)."""
    n = len(points)
    perimeter = 0.0
    for i in range(n):
        j = (i + 1) % n
        dx = points[j].x - points[i].x
        dy = points[j].y - points[i].y
        perimeter += math.sqrt(dx * dx + dy * dy)
    return perimeter


def _find_wall_line_pairs(lines: list[LineSegment]) -> list[tuple[LineSegment, LineSegment]]:
    """
    평행 선분 쌍을 찾아 벽 후보로 반환합니다.
    CAD에서 벽은 보통 두 개의 평행 선분으로 표현됩니다.
    """
    pairs = []
    used = set()
    tolerance = 0.01  # 1cm tolerance

    for i, line_a in enumerate(lines):
        if i in used:
            continue

        dir_a = _line_direction(line_a)
        if dir_a is None:
            continue

        for j in range(i + 1, len(lines)):
            if j in used:
                continue

            line_b = lines[j]
            dir_b = _line_direction(line_b)
            if dir_b is None:
                continue

            # Check if parallel (cross product near zero)
            cross = abs(dir_a[0] * dir_b[1] - dir_a[1] * dir_b[0])
            if cross < tolerance:
                # Check if they overlap in projection
                dist = _parallel_distance(line_a, line_b, dir_a)
                if dist is not None and 0.05 < dist < 1.0:  # 5cm~1m → reasonable wall thickness
                    pairs.append((line_a, line_b))
                    used.add(i)
                    used.add(j)
                    break

    return pairs


def _line_direction(line: LineSegment) -> Optional[tuple[float, float]]:
    """선분의 2D 단위 방향 벡터를 반환합니다."""
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1e-9:
        return None
    return (dx / length, dy / length)


def _parallel_distance(
    line_a: LineSegment, line_b: LineSegment, direction: tuple[float, float]
) -> Optional[float]:
    """두 평행 선분 사이의 수직 거리를 계산합니다."""
    # Normal to direction
    nx, ny = -direction[1], direction[0]
    # Vector from line_a start to line_b start
    vx = line_b.start.x - line_a.start.x
    vy = line_b.start.y - line_a.start.y
    dist = abs(nx * vx + ny * vy)
    return dist

