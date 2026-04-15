# Step 2: Automated BOQ (Bill of Quantities) Panel UI

**상태**: ✅ 구현 완료  
**완료일**: 2026-04-15

---

## 배경 / 문제

백엔드에 `GET /api/boq/{filename}` 엔드포인트가 이미 완성되어 있었으나,
프론트엔드에서 결과를 표시하는 UI가 전혀 없었다.

사용자는 BOQ 데이터를 보려면 직접 API를 호출해야 했음.

---

## 구현 내용

### 신규 파일

**`frontend/src/components/BOQPanel.jsx`**
- IFC 파일이 선택된 상태에서 "물량 산출 실행" 버튼 클릭 시 `/api/boq/{filename}` 호출
- 타입별 요약 카드 (IfcWall, IfcSlab, IfcColumn, IfcDoor, IfcWindow 등)
- 각 카드 클릭 시 세부 수량 데이터 아코디언 펼침
  - 길이(m), 면적(m²), 외측면적(m²), 내측면적(m²), 총체적(m³), 순체적(m³)
- 전체 합산 카드 (모든 타입의 수치 합산)
- 로딩 스피너, 에러 표시, 파일 미선택 안내 포함

### 수정된 파일

**`frontend/src/App.jsx`**
- `BOQPanel` 임포트 추가
- 탭 상태 타입을 `'chat' | 'modeling' | 'boq'`로 확장
- 우측 패널에 `📊 BOQ` 세 번째 탭 버튼 추가
- `activeTab === 'boq'` 시 `<BOQPanel activeFile={activeFile} />` 렌더링

---

## UI 구조

```
[💬 AI Assistant] [🏗️ Modeling] [📊 BOQ]  ← 탭 버튼 (신규)
─────────────────────────────────────────
  파일: Ifc4_SampleHouse.ifc
  ┌─────────────────────────────┐
  │  [물량 산출 실행]            │  ← 버튼 클릭 → /api/boq 호출
  └─────────────────────────────┘

  ▼ 타입별 요약
  🧱 Wall  (12개)  ▼─ 펼치면 수치 표시
  ▬ Slab   (3개)
  🚪 Door  (8개)
  🪟 Window (6개)

  ─────────────────
  📊 전체 합산
  총 체적: 45.123 m³
  ...
```

---

## 백엔드 데이터 구조 (기존 API)

`GET /api/boq/{filename}` 응답 예시:
```json
{
  "success": true,
  "filename": "Ifc4_SampleHouse.ifc",
  "boq": {
    "summary": {
      "IfcWall": {
        "count": 12,
        "GrossVolume": 15.234,
        "NetVolume": 14.100,
        "Length": 45.0,
        "GrossSideArea": 135.0
      },
      ...
    },
    "details": { ... }
  }
}
```

---

## 다음 단계

- [ ] BOQ 결과 CSV/Excel 내보내기 버튼 추가
- [ ] 타입별 개별 요소 목록 드릴다운 (details 데이터 활용)
