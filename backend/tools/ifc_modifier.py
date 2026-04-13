"""
[MCP Tool 3] Natural Language IFC Modifier
LLM이 내린 지시(필터 + 액션)를 매개변수로 받아,
실제 IFC 파일의 좌표와 속성을 수정하고 저장하는 MCP 도구
"""

from pathlib import Path


UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def register_ifc_modifier_tool(mcp):
    """FastMCP 인스턴스에 IFC 수정 도구를 등록합니다."""

    @mcp.tool()
    def modify_ifc_elements(
        filename: str,
        action: str,
        target_filter: dict,
        parameters: dict,
    ) -> dict:
        """
        IFC 파일의 요소를 필터링하여 속성/위치/크기를 수정합니다.

        Args:
            filename: IFC 파일 이름 (outputs 폴더 내)
            action: 수행할 액션 타입
                - "change_thickness": 벽 두께 변경
                - "change_height": 벽/요소 높이 변경
                - "move": 요소 이동
                - "delete": 요소 삭제
                - "set_property": 커스텀 속성 설정
            target_filter: 대상 요소 필터
                - type: IFC 클래스 (예: "IfcWall")
                - storey: 층 이름 (예: "1F")
                - name_contains: 이름에 포함된 문자열
                - global_id: 특정 GlobalId
            parameters: 액션별 매개변수
                - change_thickness: {"value": 0.2}  (미터)
                - change_height: {"value": 3.5}  (미터)
                - move: {"dx": 1.0, "dy": 0.0, "dz": 0.0}  (미터)
                - delete: {}
                - set_property: {"pset_name": "...", "property_name": "...", "value": ...}

        Returns:
            수정 결과 요약 (수정된 요소 수, 변경 내역 등)
        """
        from services.ifc_utils import (
            open_ifc,
            filter_elements,
            move_element,
            change_wall_thickness,
            change_wall_height,
            delete_element,
            get_element_global_position,
            insert_door_in_wall,
            insert_window_in_wall
        )

        filepath = None
        for directory in [OUTPUT_DIR, UPLOAD_DIR]:
            candidate = directory / filename
            if candidate.exists():
                filepath = candidate
                break

        if not filepath:
            return {"error": f"파일을 찾을 수 없습니다: {filename}"}

        valid_actions = [
            "change_thickness",
            "change_height",
            "move",
            "delete",
            "set_property",
            "insert_door",
            "insert_window"
        ]
        if action not in valid_actions:
            return {
                "error": f"유효하지 않은 액션: {action}. 가능한 액션: {valid_actions}"
            }

        try:
            model = open_ifc(str(filepath))

            # Filter target elements
            elements = filter_elements(model, target_filter)

            if not elements:
                return {
                    "success": False,
                    "message": "필터 조건에 맞는 요소를 찾지 못했습니다.",
                    "filter_used": target_filter,
                }

            modified_count = 0
            modifications = []

            for element in elements:
                elem_info = {
                    "id": element.GlobalId,
                    "type": element.is_a(),
                    "name": getattr(element, "Name", "") or "",
                }

                if action == "change_thickness":
                    value = parameters.get("value", 0.2)
                    success = change_wall_thickness(model, element, value)
                    if success:
                        modified_count += 1
                        elem_info["change"] = f"두께 → {value}m"
                        modifications.append(elem_info)

                elif action == "change_height":
                    value = parameters.get("value", 3.0)
                    success = change_wall_height(model, element, value)
                    if success:
                        modified_count += 1
                        elem_info["change"] = f"높이 → {value}m"
                        modifications.append(elem_info)

                elif action == "move":
                    dx = parameters.get("dx", 0.0)
                    dy = parameters.get("dy", 0.0)
                    dz = parameters.get("dz", 0.0)

                    old_pos = get_element_global_position(element)
                    move_element(model, element, dx, dy, dz)
                    new_pos = get_element_global_position(element)

                    modified_count += 1
                    elem_info["change"] = f"이동: ({dx}, {dy}, {dz})m"
                    elem_info["old_position"] = old_pos
                    elem_info["new_position"] = new_pos
                    modifications.append(elem_info)

                elif action == "delete":
                    delete_element(model, element)
                    modified_count += 1
                    elem_info["change"] = "삭제됨"
                    modifications.append(elem_info)

                elif action == "insert_door":
                    success = insert_door_in_wall(model, element)
                    if success:
                        modified_count += 1
                        elem_info["change"] = "문 생성됨"
                        modifications.append(elem_info)

                elif action == "insert_window":
                    success = insert_window_in_wall(model, element)
                    if success:
                        modified_count += 1
                        elem_info["change"] = "창문 생성됨"
                        modifications.append(elem_info)

                elif action == "set_property":
                    import ifcopenshell.api

                    pset_name = parameters.get("pset_name", "CustomProperties")
                    property_name = parameters.get("property_name")
                    value = parameters.get("value")

                    if not property_name:
                        elem_info["error"] = "property_name이 필요합니다."
                        modifications.append(elem_info)
                        continue

                    # Find or create property set
                    pset = None
                    if hasattr(element, "IsDefinedBy"):
                        for rel in element.IsDefinedBy:
                            if rel.is_a("IfcRelDefinesByProperties"):
                                prop_def = rel.RelatingPropertyDefinition
                                if (
                                    prop_def.is_a("IfcPropertySet")
                                    and prop_def.Name == pset_name
                                ):
                                    pset = prop_def
                                    break

                    if not pset:
                        pset = ifcopenshell.api.run(
                            "pset.add_pset",
                            model,
                            product=element,
                            name=pset_name,
                        )

                    ifcopenshell.api.run(
                        "pset.edit_pset",
                        model,
                        pset=pset,
                        properties={property_name: value},
                    )

                    modified_count += 1
                    elem_info["change"] = (
                        f"속성 설정: {pset_name}.{property_name} = {value}"
                    )
                    modifications.append(elem_info)

            # Save modified file
            model.write(str(filepath))

            return {
                "success": True,
                "message": f"{modified_count}개 요소가 수정되었습니다.",
                "filename": filename,
                "action": action,
                "modified_count": modified_count,
                "total_matched": len(elements),
                "modifications": modifications,
            }

        except Exception as e:
            return {
                "error": f"IFC 수정 중 오류 발생: {str(e)}",
                "error_type": type(e).__name__,
            }
