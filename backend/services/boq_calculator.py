"""
BOQ (Bill of Quantities) Calculator Service
- IFC 모델에서 각 객체의 체적, 면적, 길이 등 기본 물량 데이터를 추출 및 집계합니다.
"""

import math
from typing import Dict, List, Any
import ifcopenshell
import ifcopenshell.util.element

def calculate_boq(model: ifcopenshell.file) -> Dict[str, Any]:
    """
    모델의 전체 물량을 산출하여 반환합니다.
    요소 타잎(IfcWall, IfcSlab 등)을 기준으로 그룹화하며,
    각 요소의 Qto_*BaseQuantities 값을 추출하여 합산합니다.
    """
    boq_data = {
        "summary": {},  # type 별 총합 집계
        "details": {}   # type 별 개별 객체 리스트
    }

    # 계산 대상 IFC 타입들
    target_types = ["IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn", "IfcBeam", "IfcDoor", "IfcWindow"]
    
    products = []
    for t in target_types:
        try:
            products.extend(model.by_type(t))
        except Exception:
            pass
            
    if not products:
        try:
            products = model.by_type("IfcProduct")
        except Exception:
            pass

    for product in products:
        element_type = product.is_a()
        
        # Init struct
        if element_type not in boq_data["summary"]:
            boq_data["summary"][element_type] = {
                "count": 0,
                "GrossVolume": 0.0,
                "NetVolume": 0.0,
                "GrossSideArea": 0.0,
                "NetSideArea": 0.0,
                "Length": 0.0,
                "Area": 0.0,
            }
            boq_data["details"][element_type] = []

        boq_data["summary"][element_type]["count"] += 1
        
        # Psets 및 Qsets 추출
        psets = ifcopenshell.util.element.get_psets(product)
        extracted_quantities = {}
        
        if psets:
            for pset_name, pset_data in psets.items():
                # Qto_ (Quantity Take-off) 로 시작하는 프로퍼티 셋에서 물량 추출
                if pset_name.startswith("Qto_") or "Quantities" in pset_name:
                    for qty_name, qty_value in pset_data.items():
                        if qty_name == "id":
                            continue
                            
                        # 숫자인 경우에만 합산
                        if isinstance(qty_value, (int, float)):
                            extracted_quantities[qty_name] = qty_value
                            
                            # Summary 에 합산 추적
                            if qty_name in boq_data["summary"][element_type]:
                                boq_data["summary"][element_type][qty_name] += qty_value
                            else:
                                boq_data["summary"][element_type][qty_name] = qty_value

        # 상세 데이터 기록
        storey = _get_element_storey_name(product)
        detail_item = {
            "id": product.GlobalId,
            "name": getattr(product, "Name", "") or "",
            "storey": storey,
            "quantities": extracted_quantities
        }
        boq_data["details"][element_type].append(detail_item)

    # 포매팅: 소수점 3자리로 정리
    for t, quantities in boq_data["summary"].items():
        for k, v in quantities.items():
            if isinstance(v, float):
                boq_data["summary"][t][k] = round(v, 3)

    return boq_data

def _get_element_storey_name(element) -> str:
    """요소가 속한 층의 이름을 반환합니다."""
    try:
        if hasattr(element, "ContainedInStructure"):
            for rel in element.ContainedInStructure:
                if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                    return getattr(rel.RelatingStructure, "Name", "") or ""
    except Exception:
        pass
    return "Unknown"
