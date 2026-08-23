"""Company-X MCP 서버 — NL2SQL / 지식그래프 / 벡터검색 3개 도구를 MCP 프로토콜로 노출한다.

실행 전 준비물 (환경변수):
  - COMPANYX_DB_DSN (기본값: dbname=companyx host=localhost port=5434 user=postgres)
  - PGPASSWORD       (DB 비밀번호 — 코드에 절대 하드코딩하지 않음)
  - OLLAMA_HOST       (기본값: http://localhost:11434)

실행: python mcp_server/server.py   (stdio transport로 구동)
"""

import importlib
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 세 도구 디렉터리 모두 "pipeline.py", "answer.py", "llm_client.py" 등 같은 파일명을 쓰기 때문에
# (각 도구를 독립 모듈로 유지하려는 설계 — 작업계획 문서 참고), 이름 충돌 없이 각각 로드하기 위해
# 한 번에 한 디렉터리씩만 sys.path에 올리고, 로드 직후 관련 모듈 캐시를 비운다.
_SHARED_MODULE_NAMES = [
    "pipeline", "answer", "llm_client", "executor", "prompt",
    "search", "rerank", "extract", "traverse", "loader", "embed",
]


def _load_pipeline(tool_dir_name: str):
    for name in _SHARED_MODULE_NAMES:
        sys.modules.pop(name, None)

    tool_dir = str(PROJECT_ROOT / tool_dir_name)
    sys.path.insert(0, tool_dir)
    try:
        module = importlib.import_module("pipeline")
    finally:
        sys.path.remove(tool_dir)

    for name in _SHARED_MODULE_NAMES:
        sys.modules.pop(name, None)
    return module


nl2sql_pipeline = _load_pipeline("nl2sql")
kg_pipeline = _load_pipeline("knowledge_graph")
vector_pipeline = _load_pipeline("vector_search")

from router import route  # mcp_server 디렉터리 자체는 스크립트 실행 시 sys.path[0]으로 자동 포함됨

mcp = MCPServer(
    name="companyx-mcp",
    description="Company-X 지능형 데이터 검색 MCP 서버 — NL2SQL, 지식 그래프, 벡터 검색 3개 도구 제공",
)


@mcp.tool()
def nl2sql_query(question: str) -> dict:
    """정형 데이터(매출, 계약, 직원, 제품, 티켓 등)에 대한 자연어 질문을 SQL로 변환해 조회한다."""
    return nl2sql_pipeline.answer_question(question)


@mcp.tool()
def knowledge_graph_query(question: str) -> dict:
    """고객사-제품-직원-프로젝트-부서 간 관계(사용, 담당, 소속, 리드 등)를 탐색해 답한다."""
    return kg_pipeline.answer_question(question)


@mcp.tool()
def vector_search_query(question: str) -> dict:
    """장애보고서, 기술문서, 회의록, 제안서 등 비정형 문서를 의미 검색해 답한다."""
    return vector_pipeline.answer_question(question)


@mcp.tool()
def ask(question: str) -> dict:
    """어떤 도구를 써야 할지 모를 때 사용하는 진입점. 규칙 기반 라우터가 질문 유형에 맞는
    도구(NL2SQL/지식그래프/벡터검색)를 자동으로 선택해서 호출한다."""
    tool_name = route(question)
    handlers = {
        "nl2sql": nl2sql_pipeline.answer_question,
        "knowledge_graph": kg_pipeline.answer_question,
        "vector_search": vector_pipeline.answer_question,
    }
    result = handlers[tool_name](question)
    result["routed_to"] = tool_name
    return result


if __name__ == "__main__":
    mcp.run()
