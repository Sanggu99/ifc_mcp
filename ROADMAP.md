# IFC MCP Studio - Product Roadmap

본 문서는 IFC MCP Studio의 프로덕션 레벨 고도화를 위한 단계별 로드맵입니다. 자율형 에이전트(Autonomous Agent) 사이클에 의해 지속적으로 업데이트 됩니다.

## 🟢 Phase 1: MVP & Core Integration (Current - Completed)
- [x] **CAD to BIM**: `ezdxf` + `IfcOpenShell`을 이용한 DXF 레이어 및 지오메트리 기반 자동 객체 분류 및 IFC4 변환.
- [x] **Web Visualization**: `web-ifc` 및 Three.js를 활용한 브라우저 네이티브 3D 뷰어 구축.
- [x] **AI MCP Server**: FastMCP와 Gemini를 연동하여 모델 데이터 분석 및 기본 수정(이동/삭제/속성) 도구 구현.
- [x] **App Shell**: React/Tailwind 기반의 글래스모피즘 통합 대시보드 UI.

## 🟡 Phase 2: Lightweight Web-BIM Authoring (Next Steps)
- [ ] **Interactive 3D Selection**: 브라우저 뷰어에서 3D 객체(문, 벽 등)를 클릭하여 선택하고 패널에 정보를 표출하는 Raycast 기반 상호작용.
- [ ] **Context-Aware AI Modification**: 선택된 객체(Context)를 바탕으로 "이 벽의 두께를 늘려줘"와 같이 타겟팅된 LLM 자연어 제어.
- [ ] **Parametric Creation**: 백엔드(IfcOpenShell)에서 Boolean 연산을 적용하여, 벽에 문이나 창문을 자연어 명령으로 새로 삽입하는 기능.
- [ ] **Automated BOQ**: 2D 도면 기반 사고를 대체할 수 있는 체적/면적/길이 기준의 자동 물량 산출(Bill of Quantities) 데이터 추출 도구.

## ⚪ Phase 3: Collaborative Production Environment
- [ ] **Version Control & Undo/Redo**: 모델 수정 이력을 관리하고, 수정 전/후를 비교(Diff)할 수 있는 버전 관리 시스템 확보.
- [ ] **BCF (BIM Collaboration Format) Integration**: LLM이 파악한 오류나 코멘트를 BCF 포맷 기반의 이슈로 생성하여 서버 연동.
- [ ] **Multi-User Sync**: Yjs / WebSockets을 통한 실시간 다중 사용자 모델 조회 및 동시 수정 알림 기능.
- [ ] **Cloud Storage System**: 로컬 파일 시스템 의존을 탈피해 S3 & PostgreSQL 기반 상태 관리 전환.
