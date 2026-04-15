# Phase 1 완료 기록

**완료일**: 2026-04-15  
**Status**: ✅ 완료

---

## 구현된 기능 목록

### 1. CAD to BIM 변환 파이프라인
- **라이브러리**: `ezdxf` + `IfcOpenShell`
- `backend/services/dxf_parser.py` — DXF 레이어/지오메트리 파싱
- `backend/services/ifc_builder.py` — IFC4 파일 빌드 (벽체, 슬래브, 기둥)
- 병렬 선(Parallel lines) 감지 → 자동 벽체(IfcWall) 생성
- REST API: `POST /api/convert`

### 2. 3D 웹 뷰어
- **라이브러리**: `web-ifc` + `Three.js`
- `frontend/src/components/IFCViewer.jsx`
- IFC 파일 스트리밍 렌더링 (StreamAllMeshes)
- OrbitControls 기반 카메라 조작
- Raycast 기반 3D 객체 클릭 선택 (expressID 추출)
- 선택 시 초록 Emissive 하이라이트
- IFC 타입별 색상 팔레트 (벽/창문/문/기둥 등)

### 3. AI MCP Server
- **프레임워크**: FastAPI + FastMCP
- **LLM**: Google Gemini API (gemini-2.0-flash)
- MCP 도구 등록:
  - `convert_cad_to_ifc` — DXF→IFC 변환
  - `extract_ifc_data` — IFC 모델 정보 추출
  - `modify_ifc_elements` — 이동/삭제/두께/높이 변경
  - `calculate_boq` — 물량 산출
- LLM 응답에서 JSON 도구 호출 파싱 후 자동 실행
- `context_id` (Express ID)를 시스템 프롬프트에 포함 → Context-Aware 수정 지원

### 4. React 대시보드 UI
- **스택**: React 19 + Vite 8 + Tailwind CSS 4
- 글래스모피즘 다크 테마
- 컴포넌트 구성:
  - `App.jsx` — 전체 레이아웃 및 상태 관리
  - `Header.jsx` — 서버 상태 표시
  - `Sidebar.jsx` — 파일 목록 (업로드/다운로드/삭제)
  - `FileUpload.jsx` — DXF/IFC 업로드 + 변환 트리거
  - `IFCViewer.jsx` — 3D 뷰어
  - `ChatPanel.jsx` — AI 채팅 UI
  - `ModelingPanel.jsx` — BIM 객체 생성/수정 도구

---

## 기술 결정 사항

| 결정 | 이유 |
|------|------|
| web-ifc 직접 사용 (not @thatopen/components) | WASM 경로 문제 회피, 더 안정적 |
| FastMCP over 직접 MCP 구현 | 빠른 MCP 도구 등록, FastAPI 마운팅 지원 |
| Gemini 2.0 Flash | 낮은 지연, 도구 호출 JSON 파싱에 적합 |
| StreamAllMeshes | 대형 IFC 파일도 메모리 효율적으로 렌더링 |

---

## 알려진 한계 (Phase 2에서 해결 예정)

- BOQ 결과 프론트엔드 표시 UI 없음
- 선택 요소의 상세 IFC 속성 패널 없음
- 서버 재시작 시 GEMINI_API_KEY 재설정 필요 (dotenv 미적용)
