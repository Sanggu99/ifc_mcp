"""
[MCP Tool 2] IFC Data Extractor for LLM
IFC 파일의 공간 구조, 객체 리스트, 속성, 수량, 바운딩 박스 정보를
LLM이 이해할 수 있는 JSON 형태로 요약하여 반환하는 MCP 도구
"""

from pathlib import Path


UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def register_ifc_extractor_tool(mcp):
    """FastMCP 인스턴스에 IFC 데이터 추출 도구를 등록합니다."""

    @mcp.tool()
    def extract_ifc_data(filename: str) -> dict:
        """
        IFC 파일의 구조, 객체 리스트, 속성, 수량 정보를 JSON으로 요약합니다.
        LLM이 모델을 파악하기 위한 시야 확보용 도구입니다.

        Args:
            filename: IFC 파일 이름 (uploads 또는 outputs 폴더 내)

        Returns:
            IFC 모델의 전체 구조와 요소 정보를 포함한 JSON 딕셔너리
        """
        from services.ifc_utils import (
            open_ifc,
            get_spatial_structure,
            get_model_summary,
        )

        # Look for file in both directories
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

            # 1. Spatial structure
            spatial = get_spatial_structure(model)

            # 2. Model summary
            summary = get_model_summary(model)
            total_elements = sum(
                count
                for ifc_type, count in summary.items()
                if not ifc_type.startswith("IfcSite")
                and not ifc_type.startswith("IfcBuilding")
                and not ifc_type.startswith("IfcProject")
            )

            # 3. Schema info
            schema = model.schema

            # 4. File metadata
            header_info = {}
            try:
                if model.header:
                    desc = model.header.file_description
                    if desc:
                        header_info["description"] = str(desc.description) if hasattr(desc, "description") else ""
                    fname = model.header.file_name
                    if fname:
                        header_info["author"] = str(fname.author) if hasattr(fname, "author") else ""
                        header_info["organization"] = str(fname.organization) if hasattr(fname, "organization") else ""
            except Exception:
                pass

            return {
                "success": True,
                "schema": schema,
                "file_info": header_info,
                "project": _extract_project_info(model),
                "spatial_structure": spatial,
                "summary": {
                    "total_elements": total_elements,
                    "by_type": summary,
                },
            }

        except Exception as e:
            return {
                "error": f"IFC 데이터 추출 중 오류 발생: {str(e)}",
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    def list_ifc_elements(
        filename: str,
        element_type: str = "IfcProduct",
        storey_name: str = "",
    ) -> dict:
        """
        IFC 파일 내 특정 타입의 요소 목록을 반환합니다.

        Args:
            filename: IFC 파일 이름
            element_type: 필터링할 IFC 타입 (기본값: IfcProduct = 전체)
            storey_name: 특정 층 이름으로 필터 (빈 문자열이면 전체)

        Returns:
            요소 목록 (ID, 이름, 타입, 위치 등)
        """
        from services.ifc_utils import (
            open_ifc,
            filter_elements,
            get_element_global_position,
            get_element_bounding_box,
        )
        import ifcopenshell.util.element

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

            target_filter = {"type": element_type}
            if storey_name:
                target_filter["storey"] = storey_name

            elements = filter_elements(model, target_filter)

            result_list = []
            for elem in elements:
                elem_data = {
                    "id": elem.GlobalId,
                    "type": elem.is_a(),
                    "name": getattr(elem, "Name", "") or "",
                }

                # Position
                pos = get_element_global_position(elem)
                if pos:
                    elem_data["position"] = pos

                # Bounding box
                bbox = get_element_bounding_box(model, elem)
                if bbox:
                    elem_data["bounding_box"] = bbox

                # Key properties
                try:
                    psets = ifcopenshell.util.element.get_psets(elem)
                    if psets:
                        clean_psets = {}
                        for pset_name, pset_data in psets.items():
                            clean = {
                                k: v
                                for k, v in pset_data.items()
                                if k != "id" and v is not None
                            }
                            if clean:
                                clean_psets[pset_name] = clean
                        if clean_psets:
                            elem_data["properties"] = clean_psets
                except Exception:
                    pass

                result_list.append(elem_data)

            return {
                "success": True,
                "filename": filename,
                "element_type": element_type,
                "count": len(result_list),
                "elements": result_list,
            }

        except Exception as e:
            return {
                "error": f"요소 목록 조회 중 오류 발생: {str(e)}",
                "error_type": type(e).__name__,
            }


def _extract_project_info(model) -> dict:
    """IFC 프로젝트 기본 정보를 추출합니다."""
    info = {}
    projects = model.by_type("IfcProject")
    if projects:
        project = projects[0]
        info["name"] = getattr(project, "Name", "") or ""
        info["description"] = getattr(project, "Description", "") or ""
        info["global_id"] = project.GlobalId

        # Units
        try:
            units = []
            if project.UnitsInContext:
                for unit in project.UnitsInContext.Units:
                    if unit.is_a("IfcSIUnit"):
                        units.append(
                            {
                                "type": str(unit.UnitType),
                                "name": str(unit.Name) if unit.Name else "",
                                "prefix": str(unit.Prefix) if unit.Prefix else "",
                            }
                        )
            info["units"] = units
        except Exception:
            pass

    return info
