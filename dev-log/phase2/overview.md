# Phase 2 개발 계획 — Lightweight Web-BIM Authoring

**시작일**: 2026-04-15  
**목표**: 3D 뷰어에서의 상호작용과 AI 자연어 제어를 강화하고, BOQ 데이터 시각화를 완성한다.

---

## 구현 목표 항목

| 번호 | 기능 | 상태 | 문서 |
|------|------|------|------|
| Step 1 | Interactive 3D Selection | ✅ 완료 (Phase 1에서 구현됨) | [step1-3d-selection.md](./step1-3d-selection.md) |
| Step 2 | Automated BOQ Panel UI | ✅ 구현 완료 | [step2-boq-panel.md](./step2-boq-panel.md) |
| Step 3 | Context-Aware AI 고도화 | 🟡 진행 예정 | [step3-context-ai.md](./step3-context-ai.md) |
| Step 4 | Parametric Creation 고도화 | ⚪ 예정 | [step4-parametric.md](./step4-parametric.md) |

---

## 기술 아키텍처

```
Frontend (React)
  ├── IFCViewer.jsx       ← Three.js + web-ifc, Raycast 선택
  ├── ChatPanel.jsx       ← Gemini LLM 채팅, context_id 전달
  ├── ModelingPanel.jsx   ← BIM 객체 생성/수정 UI
  └── BOQPanel.jsx        ← ★ 새로 추가: 물량 산출 UI

Backend (FastAPI)
  ├── /api/chat           ← Gemini LLM 자연어 처리
  ├── /api/boq/{file}     ← BOQ 데이터 제공 (기존)
  ├── /api/extract        ← IFC 속성 추출
  └── /api/model/modify   ← BIM 객체 수정
```

---

## Phase 2에서 해결할 문제

1. **BOQ UI 없음** — 백엔드 `/api/boq/{filename}` 엔드포인트는 완성되어 있으나
   프론트엔드에서 결과를 보여주는 패널이 없다.
   → `BOQPanel.jsx` 컴포넌트 신규 제작 + App.jsx 3번째 탭 추가

2. **선택 요소 속성 표시 제한** — 현재 선택 시 타입과 치수만 표시됨.
   실제 IFC pset(속성)을 백엔드에서 가져와 표시하는 기능 미비.

3. **에러 피드백 부족** — LLM 응답 오류 시 사용자에게 명확한 메시지가 없음.
