"""
IFC MCP Server — Main Entry Point
FastAPI + FastMCP 통합 서버
- REST API: 파일 업로드/다운로드, 채팅
- MCP: CAD→IFC 변환, IFC 데이터 추출, IFC 수정 도구
- Gemini API 연동 자연어 처리
"""

import os
import sys
import json
import shutil
import re
from pathlib import Path
from typing import Optional

# ── Load .env ──────────────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from fastmcp import FastMCP

# ── Directory Setup ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Add backend to path for imports
sys.path.insert(0, str(BASE_DIR))

# ── FastAPI App ──────────────────────────────────────────────────────
app = FastAPI(
    title="IFC MCP Server",
    description="CAD→IFC 변환, IFC 분석 및 수정을 위한 MCP 서버",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import sys
    print(f"Validation error: {exc.errors()}", file=sys.stderr)
    print(f"Body: {exc.body}", file=sys.stderr)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

# ── FastMCP Setup ────────────────────────────────────────────────────
mcp = FastMCP("IFC Processing Tools")

# Register MCP Tools
from tools.cad_to_ifc import register_cad_to_ifc_tool
from tools.ifc_extractor import register_ifc_extractor_tool
from tools.ifc_modifier import register_ifc_modifier_tool
from tools.boq_extractor import register_boq_extractor_tool

register_cad_to_ifc_tool(mcp)
register_ifc_extractor_tool(mcp)
register_ifc_modifier_tool(mcp)
register_boq_extractor_tool(mcp)

# Mount MCP on FastAPI
mcp_app = mcp.http_app(path="/mcp")
app.mount("/mcp", mcp_app)

# ── Gemini API Configuration ────────────────────────────────────────
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or os.environ.get("GOOGLE_GENAI_API_KEY")
)
print(f"[startup] GEMINI_API_KEY set: {bool(GEMINI_API_KEY)} | prefix: {GEMINI_API_KEY[:12] if GEMINI_API_KEY else 'None'}")


def get_gemini_client():
    """Gemini API 클라이언트를 반환합니다."""
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY가 설정되지 않아 Gemini LLM을 사용할 수 없습니다.")
        return None

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        return client
    except Exception as e:
        print(f"Warning: Gemini client init failed: {e}")
        return None


# ── Pydantic Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    filename: Optional[str] = None
    history: list[dict] = []
    context_id: Optional[int] = None


class ConvertRequest(BaseModel):
    filename: str
    wall_height: float = 3.0
    wall_thickness: float = 0.2
    slab_thickness: float = 0.3


class CreateElementRequest(BaseModel):
    filename: str
    type: str  # "Wall", "Column", "Door", "Window"
    parameters: dict  # height, thickness, width, x, y, z, etc.


class ExtrudeRequest(BaseModel):
    filename: str
    target_layer: str
    height_mm: float
    thickness_mm: float = 200.0
    plane: str = "XY"


class ModifyElementRequest(BaseModel):
    filename: str
    express_id: int
    action: str  # "move", "delete", "resize", "set_property"
    parameters: dict


# ── REST API Endpoints ──────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "IFC MCP Server"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 (DXF 또는 IFC)"""
    if not file.filename:
        raise HTTPException(400, "파일 이름이 없습니다.")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".dxf", ".ifc"):
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다: {ext}. DXF 또는 IFC만 업로드 가능합니다.")

    # Save file
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_size = save_path.stat().st_size

    return {
        "success": True,
        "filename": file.filename,
        "size": file_size,
        "type": ext[1:].upper(),
        "message": f"파일 업로드 완료: {file.filename}",
    }


@app.get("/api/files")
async def list_files():
    """업로드 및 출력 파일 목록"""
    files = []

    for directory, source in [(UPLOAD_DIR, "upload"), (OUTPUT_DIR, "output")]:
        if directory.exists():
            for filepath in directory.iterdir():
                if filepath.is_file() and filepath.suffix.lower() in (".dxf", ".ifc"):
                    files.append(
                        {
                            "filename": filepath.name,
                            "source": source,
                            "size": filepath.stat().st_size,
                            "type": filepath.suffix[1:].upper(),
                            "modified": filepath.stat().st_mtime,
                        }
                    )

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files}


@app.get("/api/files/{filename}")
async def download_file(filename: str):
    """파일 다운로드"""
    for directory in [OUTPUT_DIR, UPLOAD_DIR]:
        filepath = directory / filename
        if filepath.exists():
            return FileResponse(
                path=str(filepath),
                filename=filename,
                media_type="application/octet-stream",
            )

    raise HTTPException(404, f"파일을 찾을 수 없습니다: {filename}")


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """파일 삭제"""
    deleted = False
    for directory in [OUTPUT_DIR, UPLOAD_DIR]:
        filepath = directory / filename
        if filepath.exists():
            filepath.unlink()
            deleted = True

    if not deleted:
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {filename}")

    return {"success": True, "message": f"파일 삭제 완료: {filename}"}


@app.post("/api/convert")
async def convert_cad(request: ConvertRequest):
    """CAD→IFC 변환 REST endpoint"""
    from services.dxf_parser import parse_dxf
    from services.ifc_builder import build_ifc_from_dxf

    input_path = UPLOAD_DIR / request.filename
    if not input_path.exists():
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {request.filename}")

    output_filename = Path(request.filename).stem + ".ifc"
    output_path = OUTPUT_DIR / output_filename

    try:
        parse_result = parse_dxf(str(input_path))
        stats = build_ifc_from_dxf(
            parse_result=parse_result,
            output_path=str(output_path),
            wall_height=request.wall_height,
            wall_thickness=request.wall_thickness,
            slab_thickness=request.slab_thickness,
        )

        return {
            "success": True,
            "output_file": output_filename,
            "statistics": stats,
            "layers": parse_result.layers,
        }
    except Exception as e:
        raise HTTPException(500, f"변환 오류: {str(e)}")


@app.get("/api/dxf/view/{filename}")
async def get_dxf_view(filename: str):
    """DXF 파일의 기하 정보를 JSON으로 반환 (웹 뷰어용)"""
    from services.dxf_parser import parse_dxf

    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {filename}")

    try:
        parse_result = parse_dxf(str(filepath))

        # 프론트엔드에서 그리기 쉬운 형태로 가공
        def rgb_to_hex(rgb):
            if rgb and isinstance(rgb, (tuple, list)) and len(rgb) == 3:
                return '#{:02x}{:02x}{:02x}'.format(*[max(0, min(255, int(v))) for v in rgb])
            return None

        view_data = {
            "lines": [
                {
                    "start": [l.start.x, l.start.y, l.start.z],
                    "end": [l.end.x, l.end.y, l.end.z],
                    "layer": l.layer,
                    "color": rgb_to_hex(l.color) if l.color else None
                } for l in parse_result.lines
            ],
            "polylines": [
                {
                    "points": [[p.x, p.y, p.z] for p in poly.points],
                    "is_closed": poly.is_closed,
                    "layer": poly.layer,
                    "color": rgb_to_hex(poly.color) if poly.color else None
                } for poly in parse_result.polylines
            ],
            "layers": list(parse_result.layers.keys()),
            "unit_scale": parse_result.unit_scale
        }

        return view_data
    except Exception as e:
        raise HTTPException(500, f"DXF 읽기 오류: {str(e)}")


@app.post("/api/dxf/extrude")
async def extrude_dxf_layer(request: ExtrudeRequest):
    """DXF의 특정 레이어를 Z축으로 돌출시켜 IFC 파일(벽)을 생성합니다."""
    from services.dxf_parser import parse_dxf
    from services.ifc_builder import build_ifc_from_dxf

    input_path = UPLOAD_DIR / request.filename
    if not input_path.exists():
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {request.filename}")

    output_filename = Path(request.filename).stem + f"_{request.target_layer}_extruded.ifc"
    output_path = OUTPUT_DIR / output_filename

    try:
        parse_result = parse_dxf(str(input_path))
        
        # 평면 조절 로직 (XY, XZ, YZ)
        if request.plane == "XZ":
            # XZ 평면에 그려진 도면을 XY 평면으로 변환
            for l in parse_result.lines:
                l.start.y, l.start.z = l.start.z, -l.start.y
                l.end.y, l.end.z = l.end.z, -l.end.y
            for poly in parse_result.polylines:
                for p in poly.points:
                    p.y, p.z = p.z, -p.y
            for circle in parse_result.circles:
                circle.center.y, circle.center.z = circle.center.z, -circle.center.y
        elif request.plane == "YZ":
            # YZ 평면에 그려진 도면을 XY 평면으로 변환
            for l in parse_result.lines:
                l.start.x, l.start.y, l.start.z = l.start.y, l.start.z, l.start.x
                l.end.x, l.end.y, l.end.z = l.end.y, l.end.z, l.end.x
            for poly in parse_result.polylines:
                for p in poly.points:
                    p.x, p.y, p.z = p.y, p.z, p.x
            for circle in parse_result.circles:
                circle.center.x, circle.center.y, circle.center.z = circle.center.y, circle.center.z, circle.center.x

        # 선택된 레이어의 라인들을 벽체 후보로 설정
        wall_lines = [l for l in parse_result.lines if l.layer == request.target_layer]
        
        # dxf_parser의 내부 함수를 이용해 평행한 쌍을 찾거나 모든 선을 벽으로 처리할 수 있음.
        # 여기서는 단순화를 위해 target_layer의 모든 선을 벽으로 처리 (단일 선분 기반)
        from services.dxf_parser import _find_wall_line_pairs
        
        # 만약 쌍이 찾아지면 쌍을 쓰고, 아니면 각각의 라인을 벽체로 만듦
        pairs = _find_wall_line_pairs(wall_lines)
        if pairs:
            parse_result.wall_candidates = pairs
        else:
            # 두께를 주어 단일 라인에서 벽 생성하도록 처리 (ifc_builder에서 단일 라인도 벽으로 처리하도록 지원 필요하지만, 현재는 쌍으로 처리함)
            # 임시로 단일 라인도 쌍으로 흉내내거나 ifc_builder 로직에 맞춤.
            # 가장 확실한 방법은 ifc_builder의 build_ifc_from_dxf 호출 시 target_layer를 필터링하는 것.
            pass

        # ifc_builder를 호출하여 벽체 생성
        # 높이 및 두께 단위는 미터
        height_m = request.height_mm / 1000.0
        thickness_m = request.thickness_mm / 1000.0

        # ifc_builder가 wall_candidates만 사용하므로 target layer에 맞게 설정
        # (원래의 _find_wall_line_pairs는 평행한 선을 찾으므로, target_layer만 필터링한 후 찾습니다)
        parse_result.wall_candidates = _find_wall_line_pairs(wall_lines)

        stats = build_ifc_from_dxf(
            parse_result=parse_result,
            output_path=str(output_path),
            wall_height=height_m,
            wall_thickness=thickness_m,
            slab_thickness=0.3
        )

        return {
            "success": True,
            "output_file": output_filename,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(500, f"돌출 오류: {str(e)}")


@app.post("/api/extract")
async def extract_data(filename: str):
    """IFC 데이터 추출 REST endpoint"""
    from services.ifc_utils import open_ifc, get_spatial_structure, get_model_summary

    filepath = None
    for directory in [OUTPUT_DIR, UPLOAD_DIR]:
        candidate = directory / filename
        if candidate.exists():
            filepath = candidate
            break

    if not filepath:
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {filename}")

    try:
        model = open_ifc(str(filepath))
        spatial = get_spatial_structure(model)
        summary = get_model_summary(model)

        return {
            "success": True,
            "spatial_structure": spatial,
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(500, f"데이터 추출 오류: {str(e)}")


@app.get("/api/boq/{filename}")
async def get_boq(filename: str):
    """IFC 물량 산출(BOQ) REST endpoint"""
    from services.ifc_utils import open_ifc
    from services.boq_calculator import calculate_boq

    filepath = None
    for directory in [OUTPUT_DIR, UPLOAD_DIR]:
        candidate = directory / filename
        if candidate.exists():
            filepath = candidate
            break

    if not filepath:
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {filename}")

    try:
        model = open_ifc(str(filepath))
        boq_data = calculate_boq(model)

        return {
            "success": True,
            "filename": filename,
            "boq": boq_data,
        }
    except Exception as e:
        raise HTTPException(500, f"물량 산출 오류: {str(e)}")


@app.post("/api/chat")
async def chat_with_llm(request: ChatRequest):
    """
    Gemini LLM을 통한 자연어 IFC 처리 채팅
    LLM이 사용자의 자연어를 분석하여 적절한 도구를 호출합니다.
    """
    if not GEMINI_API_KEY:
        return await _rule_based_chat(request)

    client = get_gemini_client()
    if not client:
        return await _rule_based_chat(request)

    try:
        # Build context about available files
        file_context = _build_file_context()

        # Build IFC model context if a file is specified
        model_context = ""
        if request.filename:
            model_context = _build_model_context(request.filename)

        # System prompt for Gemini
        system_prompt = f"""당신은 건축 BIM(Building Information Modeling) 전문 AI 어시스턴트입니다.
사용자가 IFC 파일의 분석, 수정, CAD→IFC 변환을 요청하면 적절히 도움을 줍니다.

현재 서버에 있는 파일:
{file_context}

{f"현재 작업 중인 IFC 모델 정보:{chr(10)}{model_context}" if model_context else ""}

{"사용자가 뷰어에서 가리키고 있는 특정 객체(Context Express ID): " + str(request.context_id) if request.context_id else "선택된 특정한 객체 없음"}

사용 가능한 도구와 형식:
1. CAD→IFC 변환: {{"tool": "convert_cad_to_ifc", "params": {{"filename": "xxx.dxf", "wall_height": 3.0, "wall_thickness": 0.2, "slab_thickness": 0.3}}}}
2. IFC 데이터 추출: {{"tool": "extract_ifc_data", "params": {{"filename": "xxx.ifc"}}}}
3. IFC 요소 수정: {{"tool": "modify_ifc_elements", "params": {{"filename": "xxx.ifc", "action": "change_thickness|change_height|move|delete|set_property|insert_door|insert_window", "target_filter": {{"express_id": 123}}, "parameters": {{"value": 0.2}}}}}}
   - target_filter에 "express_id" (정수) 값을 넣으면 개별 객체만 타겟팅 수정됩니다. 사용자의 명령이 맥락(Context)을 지칭한다면(예: "이거 옮겨줘") 반드시 제공된 Context Express ID를 사용하세요.
4. 건물 물량 산출 (BOQ): {{"tool": "calculate_boq", "params": {{"filename": "xxx.ifc"}}}}

응답 형식:
- 도구를 호출해야 하는 경우: 반드시 JSON 블록을 ```json ... ``` 형태로 포함하세요.
- 정보 제공만 필요한 경우: 마크다운으로 설명하세요.
- 항상 한국어로 응답하세요.
"""

        # Build messages
        messages = []
        for msg in request.history[-10:]:  # Last 10 messages for context
            role = "user" if msg.get("role") == "user" else "model"
            messages.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        messages.append({"role": "user", "parts": [{"text": request.message}]})

        # Call Gemini API
        from google import genai

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=messages,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
        )

        assistant_text = response.text if response.text else ""

        if not assistant_text:
            print("[chat] Gemini returned empty response, falling back")
            return await _rule_based_chat(request)

        print(f"[chat] Gemini OK. response[:80]={repr(assistant_text[:80])}")

        # Parse tool calls from response
        tool_result = None
        try:
            tool_result = _extract_and_execute_tool(assistant_text)
        except Exception as te:
            print(f"[chat] tool extract error: {te}")

        return {
            "success": True,
            "response": assistant_text,
            "tool_result": tool_result,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Gemini API error: {e}")
        # Return rule based chat but with a note if possible or just log it
        return await _rule_based_chat(request)


async def _rule_based_chat(request: ChatRequest) -> dict:
    """
    Gemini API 없이 규칙 기반으로 사용자 요청을 처리합니다.
    """
    message = request.message.lower().strip()

    # IFC 질의 처리 (개수, 정보 조회) — 수정 키워드보다 먼저 처리
    if request.filename and request.filename.endswith(".ifc"):
        is_query = any(kw in message for kw in [
            "몇개", "몇 개", "얼마나", "몇가지", "개수", "알려줘", "보여줘",
            "how many", "count", "list", "show"
        ])

        if any(kw in message for kw in ["창문", "window", "윈도우"]):
            count_answer = _handle_ifc_count_query(request.filename, message, "IfcWindow")
            if count_answer:
                return {"success": True, "response": count_answer, "tool_result": None}

        if any(kw in message for kw in ["문", "door"]) and is_query:
            count_answer = _handle_ifc_count_query(request.filename, message, "IfcDoor")
            if count_answer:
                return {"success": True, "response": count_answer, "tool_result": None}

        if any(kw in message for kw in ["벽", "wall"]) and is_query:
            count_answer = _handle_ifc_count_query(request.filename, message, "IfcWall")
            if count_answer:
                return {"success": True, "response": count_answer, "tool_result": None}

        if any(kw in message for kw in ["기둥", "column"]) and is_query:
            count_answer = _handle_ifc_count_query(request.filename, message, "IfcColumn")
            if count_answer:
                return {"success": True, "response": count_answer, "tool_result": None}

        if any(kw in message for kw in ["슬래브", "slab", "바닥"]) and is_query:
            count_answer = _handle_ifc_count_query(request.filename, message, "IfcSlab")
            if count_answer:
                return {"success": True, "response": count_answer, "tool_result": None}

        # 두께/높이 정보 조회 (수정이 아닌 질의인 경우)
        if is_query and any(kw in message for kw in ["두께", "높이", "크기", "치수", "size"]):
            from services.ifc_utils import open_ifc, get_model_summary, get_spatial_structure
            filepath = None
            for directory in [OUTPUT_DIR, UPLOAD_DIR]:
                candidate = directory / request.filename
                if candidate.exists():
                    filepath = candidate
                    break
            if filepath:
                model = open_ifc(str(filepath))
                summary = get_model_summary(model)
                total = sum(summary.values())
                lines = [f"📊 **{request.filename}** 구성 요소:"]
                for ifc_type, count in sorted(summary.items()):
                    lines.append(f"  - {ifc_type}: {count}개")
                lines.append(f"\n총 {total}개 요소가 있습니다.")
                lines.append("\n개별 요소의 치수 정보는 3D 뷰어에서 객체를 클릭하면 확인할 수 있습니다.")
                return {"success": True, "response": "\n".join(lines), "tool_result": None}

    # File info
    if any(kw in message for kw in ["파일", "목록", "리스트", "file"]):
        files_response = await list_files()
        return {
            "success": True,
            "response": f"현재 서버에 {len(files_response['files'])}개의 파일이 있습니다.",
            "tool_result": files_response,
        }

    # Convert
    if any(kw in message for kw in ["변환", "convert", "dxf", "cad"]):
        if request.filename and request.filename.endswith(".dxf"):
            from services.dxf_parser import parse_dxf
            from services.ifc_builder import build_ifc_from_dxf

            input_path = UPLOAD_DIR / request.filename
            if input_path.exists():
                output_filename = Path(request.filename).stem + ".ifc"
                output_path = OUTPUT_DIR / output_filename

                parse_result = parse_dxf(str(input_path))
                stats = build_ifc_from_dxf(
                    parse_result=parse_result,
                    output_path=str(output_path),
                )
                return {
                    "success": True,
                    "response": f"✅ {request.filename}을 IFC로 변환했습니다.\n생성된 객체: 벽 {stats['walls']}개, 슬래브 {stats['slabs']}개",
                    "tool_result": {"output_file": output_filename, "stats": stats},
                }

        return {
            "success": True,
            "response": "변환할 DXF 파일을 선택해주세요.",
            "tool_result": None,
        }

    # Extract / Analyze
    if any(kw in message for kw in ["분석", "추출", "정보", "구조", "요약", "extract", "analyze"]):
        if request.filename and request.filename.endswith(".ifc"):
            from services.ifc_utils import open_ifc, get_spatial_structure, get_model_summary

            filepath = None
            for directory in [OUTPUT_DIR, UPLOAD_DIR]:
                candidate = directory / request.filename
                if candidate.exists():
                    filepath = candidate
                    break

            if filepath:
                model = open_ifc(str(filepath))
                spatial = get_spatial_structure(model)
                summary = get_model_summary(model)
                total = sum(summary.values())

                response_text = f"📊 **{request.filename}** 분석 결과:\n"
                response_text += f"- 총 요소 수: {total}개\n"
                for ifc_type, count in sorted(summary.items()):
                    response_text += f"  - {ifc_type}: {count}개\n"

                return {
                    "success": True,
                    "response": response_text,
                    "tool_result": {"spatial_structure": spatial, "summary": summary},
                }

        return {
            "success": True,
            "response": "분석할 IFC 파일을 선택해주세요.",
            "tool_result": None,
        }

    # Modify
    if any(kw in message for kw in ["수정", "변경", "이동", "삭제", "두께", "높이", "modify"]):
        return {
            "success": True,
            "response": (
                "IFC 수정 기능을 사용하려면 구체적인 지시를 해주세요.\n"
                "예시:\n"
                '- "1층 벽의 두께를 200mm로 변경해"\n'
                '- "선택한 요소를 X축으로 1m 이동시켜"\n'
                '- "1층의 모든 IfcWall 삭제해"'
            ),
            "tool_result": None,
        }

    # Default
    return {
        "success": True,
        "response": (
            "안녕하세요! IFC 처리 도우미입니다. 다음 작업을 도와드릴 수 있습니다:\n"
            "1. 📐 **CAD→IFC 변환**: DXF 파일을 IFC로 변환\n"
            "2. 📊 **IFC 분석**: 모델 구조/속성 분석\n"
            "3. ✏️ **IFC 수정**: 요소 이동, 속성 변경, 삭제\n\n"
            "현재 LLM 키가 설정되어 있지 않거나 LLM 서비스가 연결되지 않아 기본 응답 모드로 동작하고 있습니다.\n"
            "GEMINI_API_KEY를 설정하면 더 자연스러운 LLM 기반 답변을 받을 수 있습니다."
        ),
        "tool_result": None,
    }


def _handle_ifc_count_query(filename: str, message: str, element_type: str) -> Optional[str]:
    try:
        from services.ifc_utils import open_ifc, filter_elements

        filepath = None
        for directory in [OUTPUT_DIR, UPLOAD_DIR]:
            candidate = directory / filename
            if candidate.exists():
                filepath = candidate
                break

        if not filepath:
            return None

        storey = _parse_storey_name(message)
        target_filter = {"type": element_type}
        if storey:
            target_filter["storey"] = storey

        model = open_ifc(str(filepath))
        elements = filter_elements(model, target_filter)
        if elements is None:
            return None

        kind = element_type[3:]
        if storey:
            return f"'{filename}' 파일의 {storey}에 있는 {kind} 개수는 {len(elements)}개입니다."
        return f"'{filename}' 파일에 있는 {kind} 개수는 {len(elements)}개입니다."
    except Exception as e:
        print(f"[_handle_ifc_count_query] error: {e}")
        return None


def _parse_storey_name(message: str) -> Optional[str]:
    match = re.search(r"(\d+)\s*(?:층|[fF](?:loor)?\b)", message)
    if match:
        return match.group(1) + "층"
    return None


def _build_file_context() -> str:
    """현재 서버의 파일 목록을 텍스트로 구성합니다."""
    files = []
    for directory, source in [(UPLOAD_DIR, "uploads"), (OUTPUT_DIR, "outputs")]:
        if directory.exists():
            for fp in directory.iterdir():
                if fp.is_file() and fp.suffix.lower() in (".dxf", ".ifc"):
                    files.append(f"- [{source}] {fp.name} ({fp.stat().st_size} bytes)")

    return "\n".join(files) if files else "파일 없음"


def _build_model_context(filename: str) -> str:
    """IFC 모델의 요약 정보를 텍스트로 구성합니다."""
    try:
        from services.ifc_utils import open_ifc, get_model_summary

        filepath = None
        for directory in [OUTPUT_DIR, UPLOAD_DIR]:
            candidate = directory / filename
            if candidate.exists():
                filepath = candidate
                break

        if not filepath or not filename.endswith(".ifc"):
            return ""

        model = open_ifc(str(filepath))
        summary = get_model_summary(model)
        lines = [f"- {ifc_type}: {count}개" for ifc_type, count in summary.items()]
        return "\n".join(lines)
    except Exception:
        return ""


def _extract_and_execute_tool(response_text: str) -> Optional[dict]:
    """
    LLM 응답에서 JSON 도구 호출을 추출하고 실행합니다.
    """
    import re

    # Find JSON blocks in the response
    json_pattern = r"```json\s*\n?(.*?)\n?\s*```"
    matches = re.findall(json_pattern, response_text, re.DOTALL)

    if not matches:
        return None

    for match in matches:
        try:
            tool_call = json.loads(match)
            tool_name = tool_call.get("tool")
            params = tool_call.get("params", {})

            if tool_name == "convert_cad_to_ifc":
                from services.dxf_parser import parse_dxf
                from services.ifc_builder import build_ifc_from_dxf

                filename = params.get("filename", "")
                input_path = UPLOAD_DIR / filename
                if not input_path.exists():
                    return {"error": f"파일을 못 찾음: {filename}"}

                output_filename = Path(filename).stem + ".ifc"
                output_path = OUTPUT_DIR / output_filename

                parse_result = parse_dxf(str(input_path))
                stats = build_ifc_from_dxf(
                    parse_result=parse_result,
                    output_path=str(output_path),
                    wall_height=params.get("wall_height", 3.0),
                    wall_thickness=params.get("wall_thickness", 0.2),
                    slab_thickness=params.get("slab_thickness", 0.3),
                )
                return {"tool": tool_name, "output_file": output_filename, "stats": stats}

            elif tool_name == "extract_ifc_data":
                from services.ifc_utils import open_ifc, get_spatial_structure, get_model_summary

                filename = params.get("filename", "")
                filepath = None
                for directory in [OUTPUT_DIR, UPLOAD_DIR]:
                    candidate = directory / filename
                    if candidate.exists():
                        filepath = candidate
                        break

                if not filepath:
                    return {"error": f"파일을 못 찾음: {filename}"}

                model = open_ifc(str(filepath))
                return {
                    "tool": tool_name,
                    "spatial_structure": get_spatial_structure(model),
                    "summary": get_model_summary(model),
                }

            elif tool_name == "modify_ifc_elements":
                from services.ifc_utils import (
                    open_ifc,
                    filter_elements,
                    move_element,
                    change_wall_thickness,
                    change_wall_height,
                    delete_element,
                )

                filename = params.get("filename", "")
                filepath = None
                for directory in [OUTPUT_DIR, UPLOAD_DIR]:
                    candidate = directory / filename
                    if candidate.exists():
                        filepath = candidate
                        break

                if not filepath:
                    return {"error": f"파일을 못 찾음: {filename}"}

                model = open_ifc(str(filepath))
                action = params.get("action", "")
                target_filter = params.get("target_filter", {})
                action_params = params.get("parameters", {})

                elements = filter_elements(model, target_filter)
                modified = 0

                for element in elements:
                    if action == "change_thickness":
                        if change_wall_thickness(model, element, action_params.get("value", 0.2)):
                            modified += 1
                    elif action == "change_height":
                        if change_wall_height(model, element, action_params.get("value", 3.0)):
                            modified += 1
                    elif action == "move":
                        move_element(
                            model, element,
                            action_params.get("dx", 0),
                            action_params.get("dy", 0),
                            action_params.get("dz", 0),
                        )
                        modified += 1
                    elif action == "delete":
                        delete_element(model, element)
                        modified += 1

                model.write(str(filepath))

                return {
                    "tool": tool_name,
                    "action": action,
                    "modified_count": modified,
                    "total_matched": len(elements),
                }

            elif tool_name == "calculate_boq":
                from services.ifc_utils import open_ifc
                from services.boq_calculator import calculate_boq as calc_boq

                filename = params.get("filename", "")
                filepath = None
                for directory in [OUTPUT_DIR, UPLOAD_DIR]:
                    candidate = directory / filename
                    if candidate.exists():
                        filepath = candidate
                        break

                if not filepath:
                    return {"error": f"파일을 못 찾음: {filename}"}

                model = open_ifc(str(filepath))
                boq_result = calc_boq(model)
                
                return {
                    "tool": tool_name,
                    "filename": filename,
                    "boq": boq_result
                }

        except json.JSONDecodeError:
            continue
        except Exception as e:
            return {"error": str(e)}

    return None


@app.post("/api/model/create")
async def create_element(request: CreateElementRequest):
    """BIM 객체 수동 생성 (Revit-like)"""
    from services.ifc_utils import open_ifc
    from services.ifc_builder import create_wall_from_line, create_column, Point3D
    from services.ifc_utils import insert_door_in_wall, insert_window_in_wall

    filepath = None
    for directory in [OUTPUT_DIR, UPLOAD_DIR]:
        candidate = directory / request.filename
        if candidate.exists():
            filepath = candidate
            break

    if not filepath:
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {request.filename}")

    try:
        model = open_ifc(str(filepath))
        
        # Get context and storey
        project = model.by_type("IfcProject")[0]
        site = model.by_type("IfcSite")[0]
        building = model.by_type("IfcBuilding")[0]
        storeys = model.by_type("IfcBuildingStorey")
        storey = storeys[0] if storeys else None
        
        contexts = model.by_type("IfcGeometricRepresentationContext")
        body_context = next((c for c in contexts if getattr(c, "ContextIdentifier", None) == "Body"), contexts[0])

        params = request.parameters
        success = False
        message = ""

        if request.type == "Wall":
            start = Point3D(params.get("x1", 0), params.get("y1", 0), params.get("z1", 0))
            end = Point3D(params.get("x2", 1), params.get("y2", 0), params.get("z2", 0))
            wall = create_wall_from_line(
                model, storey, body_context,
                start=start, end=end,
                height=params.get("height", 3.0),
                thickness=params.get("thickness", 0.2),
                name=params.get("name", "New Wall")
            )
            success = wall is not None
            message = "벽체 생성 완료"

        elif request.type == "Column":
            pos = Point3D(params.get("x", 0), params.get("y", 0), params.get("z", 0))
            col = create_column(
                model, storey, body_context,
                position=pos,
                radius=params.get("radius", 0.2),
                height=params.get("height", 3.0),
                name=params.get("name", "New Column")
            )
            success = col is not None
            message = "기둥 생성 완료"

        elif request.type in ["Door", "Window"]:
            # Needs a wall to host
            host_id = params.get("host_id")
            if not host_id:
                raise HTTPException(400, "문/창문을 삽입할 벽(host_id)이 필요합니다.")
            
            wall = model.by_id(int(host_id))
            if not wall or not wall.is_a("IfcWall"):
                raise HTTPException(400, f"ID {host_id}는 유효한 벽체가 아닙니다.")

            if request.type == "Door":
                success = insert_door_in_wall(model, wall, width=params.get("width", 0.9), height=params.get("height", 2.1))
                message = "문 삽입 완료"
            else:
                success = insert_window_in_wall(model, wall, width=params.get("width", 1.0), height=params.get("height", 1.0))
                message = "창문 삽입 완료"

        if success:
            model.write(str(filepath))
            return {"success": True, "message": message}
        else:
            return {"success": False, "message": "생성 실패"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"생성 오류: {str(e)}")


@app.post("/api/model/modify")
async def modify_element(request: ModifyElementRequest):
    """기존 BIM 객체 수정 (Revit-like)"""
    from services.ifc_utils import open_ifc, move_element, change_wall_thickness, change_wall_height, delete_element

    filepath = None
    for directory in [OUTPUT_DIR, UPLOAD_DIR]:
        candidate = directory / request.filename
        if candidate.exists():
            filepath = candidate
            break

    if not filepath:
        raise HTTPException(404, f"파일을 찾을 수 없습니다: {request.filename}")

    try:
        model = open_ifc(str(filepath))
        element = model.by_id(request.express_id)
        if not element:
            raise HTTPException(404, f"요소를 찾을 수 없습니다: Express ID {request.express_id}")

        params = request.parameters
        success = False
        message = ""

        if request.action == "move":
            move_element(model, element, dx=params.get("dx", 0), dy=params.get("dy", 0), dz=params.get("dz", 0))
            success = True
            message = "이동 완료"
        
        elif request.action == "resize":
            if element.is_a("IfcWall"):
                if "thickness" in params:
                    change_wall_thickness(model, element, params["thickness"])
                if "height" in params:
                    change_wall_height(model, element, params["height"])
                success = True
                message = "크기 조정 완료"
        
        elif request.action == "delete":
            delete_element(model, element)
            success = True
            message = "삭제 완료"

        if success:
            model.write(str(filepath))
            return {"success": True, "message": message}
        else:
            return {"success": False, "message": "수정 실패"}

    except Exception as e:
        raise HTTPException(500, f"수정 오류: {str(e)}")


# ── Run with uvicorn ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
