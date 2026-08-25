"""HTTP 브릿지 서버 — 브라우저 프론트엔드가 MCP 백엔드를 호출할 수 있게 감싼다.

백엔드(mcp_server/)는 MCP stdio 프로토콜로만 노출되어 브라우저에서 직접 못 부른다.
이 서버는 세 도구 파이프라인을 직접 import해서 HTTP POST로 노출한다.
응답은 docs/frontend_requirements.md의 계약({answer, raw_data, tool, source})을 그대로 따른다.

실행:
  export PGPASSWORD=...           # mcp_reader 비밀번호
  uvicorn bridge.server:app --port 8000      (프로젝트 루트에서)
또는:
  python bridge/server.py
"""

import importlib
import sys
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 세 도구는 pipeline.py 등 동일 파일명을 쓰므로, mcp_server/server.py와 같은 방식으로
# 한 번에 한 디렉터리씩 sys.path에 올려 각각 로드한다.
_SHARED = ["pipeline", "answer", "llm_client", "executor", "prompt",
           "search", "rerank", "extract", "traverse", "loader", "embed", "korean"]


def _load(tool_dir: str):
    for name in _SHARED:
        sys.modules.pop(name, None)
    d = str(PROJECT_ROOT / tool_dir)
    sys.path.insert(0, d)
    try:
        mod = importlib.import_module("pipeline")
    finally:
        sys.path.remove(d)
    for name in _SHARED:
        sys.modules.pop(name, None)
    return mod


nl2sql_pipeline = _load("nl2sql")
kg_pipeline = _load("knowledge_graph")
vector_pipeline = _load("vector_search")
sys.path.insert(0, str(PROJECT_ROOT / "mcp_server"))
from router import route, route_by_rules  # noqa: E402

HANDLERS = {
    "nl2sql": nl2sql_pipeline.answer_question,
    "knowledge_graph": kg_pipeline.answer_question,
    "vector_search": vector_pipeline.answer_question,
}

MAX_QUESTION_CHARS = 2000

app = FastAPI(title="Company-X MCP 브릿지")
# 개발 편의를 위해 로컬 프론트(Vite 기본 5173 등)에서의 호출을 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 데모 전용. 배포 시 프론트 오리진으로 좁힐 것.
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── IP별 요청 제한 (finance-mcp의 토큰버킷 패턴 이식) ──
# 도구 호출은 LLM 때문에 건당 5~10초라 사람은 이 한도에 닿기 어렵다. 폭주/오용 방어용.
RATE_LIMIT = 60          # 창(window)당 허용 요청 수
RATE_WINDOW = 60.0       # 초
_rate_state: dict[str, tuple[int, float]] = {}


def _allow(ip: str) -> bool:
    now = time.monotonic()
    count, reset_at = _rate_state.get(ip, (0, 0.0))
    if now > reset_at:
        _rate_state[ip] = (1, now + RATE_WINDOW)
        # 만료된 항목 정리(메모리 누수 방지)
        for k in [k for k, (_, r) in _rate_state.items() if now > r]:
            if k != ip:
                _rate_state.pop(k, None)
        return True
    if count >= RATE_LIMIT:
        return False
    _rate_state[ip] = (count + 1, reset_at)
    return True


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "POST":
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        if not _allow(ip.split(",")[0].strip()):
            return JSONResponse(
                {"answer": "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.",
                 "raw_data": None, "tool": "ask", "source": []},
                status_code=429, headers={"Retry-After": "60"})
    return await call_next(request)


class Query(BaseModel):
    question: str


def _reject(reason: str, tool: str) -> dict:
    return {"answer": reason, "raw_data": None, "tool": tool, "source": []}


def _guard(question):
    if not isinstance(question, str) or not question.strip():
        return _reject("질문이 비어 있습니다. 찾으려는 내용을 입력해 주세요.", "ask")
    if len(question) > MAX_QUESTION_CHARS:
        return _reject(f"질문이 너무 깁니다 ({len(question)}자). {MAX_QUESTION_CHARS}자 이내로 줄여 주세요.", "ask")
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(q: Query):
    guard = _guard(q.question)
    if guard:
        return guard
    question = q.question.strip()
    # 어느 단계가 라우팅을 결정했는지 알려 UI가 정확한 경로 라벨을 그린다.
    ruled = route_by_rules(question)
    tool = ruled if ruled is not None else route(question)
    result = HANDLERS[tool](question)
    result["routed_to"] = tool
    result["route_tier"] = "rules" if ruled is not None else "llm_fallback"
    return result


@app.post("/tool/{tool_name}")
def tool_direct(tool_name: str, q: Query):
    if tool_name not in HANDLERS:
        return _reject(f"알 수 없는 도구입니다: {tool_name}", "ask")
    guard = _guard(q.question)
    if guard:
        guard["tool"] = tool_name
        return guard
    try:
        return HANDLERS[tool_name](q.question.strip())
    except Exception as e:
        return _reject(f"처리 중 오류가 발생했습니다: {type(e).__name__}: {e}", tool_name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
