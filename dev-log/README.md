# IFC MCP Studio — 개발 로그

## 개요

이 폴더는 IFC MCP Studio의 단계별 개발 과정을 기록합니다.
각 Phase별로 구현 내용, 기술 결정, 문제 해결 과정을 정리합니다.

---

## 로드맵 진행 현황

| Phase | 상태 | 기간 |
|-------|------|------|
| Phase 1: MVP & Core Integration | ✅ 완료 | - |
| Phase 2: Lightweight Web-BIM Authoring | 🟡 진행 중 | 2026-04-15 ~ |
| Phase 3: Collaborative Production | ⚪ 예정 | - |

---

## 폴더 구조

```
dev-log/
  README.md                 ← 이 파일 (전체 개요)
  phase1-completed.md       ← Phase 1 완료 내역
  phase2/
    overview.md             ← Phase 2 전체 계획
    step1-3d-selection.md   ← Step 1: 3D 객체 선택 (완료)
    step2-boq-panel.md      ← Step 2: BOQ 패널 UI 구현
    step3-context-ai.md     ← Step 3: Context-Aware AI 고도화 (예정)
    step4-parametric.md     ← Step 4: Parametric 생성 고도화 (예정)
```

---

## 빌드 & 실행 방법

### 백엔드
```powershell
$env:GEMINI_API_KEY = "키입력"
cd "c:\Users\SEOP\Desktop\ifc mcp"
py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 프론트엔드
```powershell
cd "c:\Users\SEOP\Desktop\ifc mcp\frontend"
npm run dev -- --host 127.0.0.1 --port 5173
```

### 접속 URL
- 프론트엔드: http://127.0.0.1:5173
- 백엔드 API: http://127.0.0.1:8000
- API 문서: http://127.0.0.1:8000/docs
