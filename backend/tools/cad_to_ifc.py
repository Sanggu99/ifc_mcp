"""
[MCP Tool 1] CAD to IFC Converter
DXF CAD 파일을 파싱하여 IFC BIM 파일로 변환하는 MCP 도구
"""

import os
from pathlib import Path


UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def register_cad_to_ifc_tool(mcp):
    """FastMCP 인스턴스에 CAD→IFC 변환 도구를 등록합니다."""

    @mcp.tool()
    def convert_cad_to_ifc(
        filename: str,
        wall_height: float = 3.0,
        wall_thickness: float = 0.2,
        slab_thickness: float = 0.3,
        project_name: str = "CAD to IFC Conversion",
    ) -> dict:
        """
        DXF CAD 파일을 IFC BIM 파일로 변환합니다.

        Args:
            filename: 업로드된 DXF 파일 이름 (uploads 폴더 내)
            wall_height: 벽 높이 (미터, 기본값 3.0)
            wall_thickness: 벽 두께 (미터, 기본값 0.2)
            slab_thickness: 슬래브 두께 (미터, 기본값 0.3)
            project_name: IFC 프로젝트 이름

        Returns:
            변환 결과 요약 (생성된 객체 수, 출력 파일 경로 등)
        """
        from services.dxf_parser import parse_dxf
        from services.ifc_builder import build_ifc_from_dxf

        input_path = UPLOAD_DIR / filename
        if not input_path.exists():
            return {"error": f"파일을 찾을 수 없습니다: {filename}"}

        if not filename.lower().endswith((".dxf",)):
            return {"error": "DXF 파일만 지원됩니다."}

        # Output filename: same name but .ifc extension
        output_filename = Path(filename).stem + ".ifc"
        output_path = OUTPUT_DIR / output_filename
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Parse DXF
            parse_result = parse_dxf(str(input_path))

            # Step 2: Build IFC from parsed data
            stats = build_ifc_from_dxf(
                parse_result=parse_result,
                output_path=str(output_path),
                wall_height=wall_height,
                wall_thickness=wall_thickness,
                slab_thickness=slab_thickness,
                project_name=project_name,
            )

            return {
                "success": True,
                "message": f"변환 완료: {output_filename}",
                "output_file": output_filename,
                "statistics": stats,
                "layers_detected": parse_result.layers,
                "unit_scale": parse_result.unit_scale,
                "input_entities": {
                    "lines": len(parse_result.lines),
                    "polylines": len(parse_result.polylines),
                    "circles": len(parse_result.circles),
                    "arcs": len(parse_result.arcs),
                    "wall_candidates": len(parse_result.wall_candidates),
                    "slab_candidates": len(parse_result.slab_candidates),
                },
            }

        except Exception as e:
            return {
                "error": f"변환 중 오류 발생: {str(e)}",
                "error_type": type(e).__name__,
            }
