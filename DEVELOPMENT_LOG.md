# IFC MCP Studio - Development Log

본 문서는 프로젝트의 진행 과정을 아카이빙하고 시각적 테스트 결과를 보존하기 위한 개발 기록입니다.

## Phase 2: Lightweight Web-BIM 모델링 고도화

현재 개발 진행 중인 기능:
1. **Automated BOQ (물량 자동 산출)**
2. **Parametric Creation (파라메트릭 객체 생성 - 문/창문 삽입)**

---

### [2026-04-11] 1단계: 프로젝트 환경 세팅 및 아키텍처 문서화 완료
- `DEVELOPMENT_LOG.md` 파일 생성 완료
- 물량 산출(BOQ) 기능 및 파라메트릭 제어 백엔드 기반 작업 시작

### [2026-04-11] 2단계: 백엔드 모듈 개발 및 브라우저 테스트 완료
- `boq_calculator.py` 및 FastMCP `boq_extractor` 구현
- `ifc_utils.py`에 IfcOpenShell Boolean 연산을 사용한 `insert_door_in_wall` 및 `insert_window` 로직 구축
- 브라우저 자동화 도구를 사용해 로컬 환경(`localhost:5173`) 테스트 및 테스트 영상 추출 완료

**테스트 구동 영상 시각화 자료:**
![Automated BOQ & Parametric Demo](/C:/Users/SEOP/.gemini/antigravity/brain/83b42481-6f3b-4163-9ea3-3dcd9197a542/automated_boq_and_parametric_demo_1775874829331.webp)
*(실시간으로 생성된 테스트 화면의 움짤/동영상입니다)*
