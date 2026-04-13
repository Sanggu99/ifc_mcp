"""
[MCP Tool 4] Automated BOQ Extractor
IFC 모델에서 객체별 물량 정보를 추출하여 AI에게 제공하는 도구
"""

from pathlib import Path

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def register_boq_extractor_tool(mcp):
    """FastMCP 인스턴스에 BOQ 산출 도구를 등록합니다."""

    @mcp.tool()
    def calculate_boq(filename: str) -> dict:
        """
        IFC 파일의 지오메트리와 속성을 분석하여 요소별/층별 물량 데이터를 산출합니다.
        
        Args:
            filename: 물량을 산출할 IFC 파일 이름 (outputs 또는 uploads 폴더 내)
            
        Returns:
            요소 타입별 요약 물량 (갯수, 체적, 면적, 길이 등) 및 상세 내역
        """
        from services.ifc_utils import open_ifc
        from services.boq_calculator import calculate_boq as calc_boq

        filepath = None
        for directory in [OUTPUT_DIR, UPLOAD_DIR]:
            candidate = directory / filename
            if candidate.exists():
                filepath = candidate
                break

        if not filepath:
            return {"error": f"파일을 찾을 수 없습니다: {filename}"}

        try:
            model = open_ifc(str(filepath))
            boq_result = calc_boq(model)
            
            return {
                "success": True,
                "filename": filename,
                "boq": boq_result
            }

        except Exception as e:
            return {
                "error": f"BOQ 산출 중 오류 발생: {str(e)}",
                "error_type": type(e).__name__,
            }
