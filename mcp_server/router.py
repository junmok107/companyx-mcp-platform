"""규칙 기반 라우터: 질문을 nl2sql / knowledge_graph / vector_search 중 하나로 분류한다.

MCP Parallel 패턴 — LLM 호출 없이 키워드 점수로 즉시 라우팅해서 지연시간과 장애 지점을 줄인다.
(실측: 라우팅 판정 0.002ms. 도구 실행 자체는 6~9초로 대부분 LLM 호출 시간이다.)

설계 원칙 — 어휘를 나열하기 전에 "무엇이 세 도구를 구분하는가"부터 정한다:
  · 지식 그래프  = 두 개체 사이의 '관계'를 묻는다      → 관계 동사/역할어가 결정적 신호
  · NL2SQL       = 수치 집계나 속성 필터를 묻는다       → 측정·집계어가 결정적 신호
  · 벡터 검색    = 문서에 적힌 '내용'을 묻는다          → 문서 성격어가 결정적 신호
개체 명사(고객사·제품·직원·프로젝트·부서)는 세 도구에 모두 등장하므로 그 자체로는
변별력이 없다. 이전 버전은 "프로젝트"를 NL2SQL 신호로 넣었다가 "프로젝트를 이끈 직원"
같은 관계 질문을 NL2SQL로 잘못 보내는 회귀를 냈다. 따라서 개체 명사는 단독 가중치를 주지 않고,
'개체 이름 + 다른 개체 유형'이 함께 나올 때만 관계 신호로 취급한다.
"""

import re

# --- 지식 그래프: 관계 동사 / 역할어 (활용형을 함께 등록) ---
KG_RELATION = [
    "담당", "소속", "속한", "맡", "이끄", "이끌", "이끈", "리드", "책임",
    "팀장", "부서장", "책임자", "수장", "우두머리", "총괄",
    "사용", "쓰는", "쓰고", "쓴", "채택", "들여", "운용", "굴리",
    "관련", "엮인", "연관", "이슈", "불만", "클레임",
    "누구", "누가 있", "누가 속", "누구누구", "명단", "인원",
]
KG_WEIGHT = 3

# 그래프 노드 이름 패턴 (Client-A, Product-C1 …)
ENTITY_NAME_PATTERN = re.compile(r"(Client|Product)-[A-Za-z0-9]+")
# 개체 '유형' 명사 — 단독으로는 변별력이 없다
ENTITY_TYPE_NOUNS = ["고객사", "고객", "거래처", "업체", "제품", "솔루션", "상품",
                     "직원", "인력", "프로젝트", "부서", "엔지니어", "담당자"]
# 개체 이름과 다른 개체 유형이 함께 나오면 두 개체 사이의 관계를 묻는 것으로 본다
ENTITY_PAIR_WEIGHT = 3

# --- NL2SQL: 측정값 / 집계 표현 ---
SQL_MEASURE = [
    "매출", "연봉", "급여", "금액", "가격", "단가", "예산", "건수", "개수",
    "총", "합계", "평균", "몇", "상위", "순으로", "순서", "순위", "비싼", "저렴",
    "세어", "세면", "집계", "몇 곳", "몇 건", "몇 명", "얼마나 많",
]
# 부분 문자열 매칭이 위험한 어휘는 정규식으로 다룬다.
# "얼마"는 금액을 묻는 신호지만, 정도부사 "얼마나"(얼마나 자주/얼마나 걸려)에도 그대로 걸려
# 문서 질문을 NL2SQL로 잘못 보낸다 (감사 실측: 오분류 5건 중 3건이 이 원인).
SQL_MEASURE_PATTERNS = [re.compile(r"얼마(?!나)")]
SQL_MEASURE_WEIGHT = 3
# 정형 테이블에만 존재하는 개념 (문서·그래프에는 없음)
SQL_TABLE_ONLY = ["티켓", "계약", "분기", "카테고리", "우선순위", "활성", "등록된", "미해결", "규모"]
SQL_TABLE_WEIGHT = 2
# 1위를 묻는 표현 — 집계 성격이지만 관계 질문에도 자주 붙으므로 약한 신호
SQL_WEAK = ["가장", "많은", "높은"]
SQL_WEAK_WEIGHT = 1

SQL_REGION_PATTERN = re.compile(r"서울|경기|인천|대전|대구|부산|광주|제주")
SQL_PERIOD_PATTERN = re.compile(r"\d{4}년|\d분기")
SQL_PATTERN_WEIGHT = 1

# --- 벡터 검색: 문서 성격 / 내용어 ---
DOC_CONTENT = [
    "장애", "사고", "먹통", "멎", "멈춘", "사례", "원인", "복구", "절차", "대응", "조치",
    "설치", "구축", "가이드", "매뉴얼", "레퍼런스", "튜닝", "최적화", "방법", "아키텍처", "설계",
    "회의", "미팅", "논의", "일정 지연", "마일스톤", "킥오프",
    "제안서", "정책", "방침", "취약점", "점검", "백업", "보관", "로그", "모니터링", "지표",
    "인증", "API", "엔드포인트", "전략", "문서", "요약", "업데이트", "업그레이드", "배포",
]
DOC_WEIGHT = 3
DOC_WEAK = ["도입"]  # '도입 제안서'일 수도, '제품을 도입한 고객사'일 수도 있어 약하게
DOC_WEAK_WEIGHT = 2

TOOL_NAMES = ("nl2sql", "knowledge_graph", "vector_search")
# 동점일 때는 실패가 가장 온건한 도구를 고른다. 벡터 검색은 관련 문서가 없으면
# "관련 문서를 찾지 못했습니다"라고 정직하게 답하지만, 관계 질문이 아닌 것을
# 지식 그래프로 보내면 "그래프에서 찾을 수 없습니다" 같은 혼란스러운 답이 나온다.
TIE_PREFERENCE = ("vector_search", "nl2sql", "knowledge_graph")
DEFAULT_TOOL = "vector_search"

# 규칙 점수가 전부 0일 때만 쓰는 LLM 폴백 분류기.
# 키워드 사전은 표현이 조금만 달라져도 0점이 되는 한계가 있다(실측: 미튜닝 세트
# 오분류 4건 중 3건이 전부 0점이었다). 어휘를 계속 늘리는 대신, 신호가 전혀 없는
# 소수 질문에만 LLM을 한 번 부른다. 대부분의 질문은 규칙에서 걸러져 0.002ms 경로를 유지한다.
LLM_ROUTER_PROMPT = """\
다음 질문을 처리할 도구를 하나만 고른다.

nl2sql: 매출·계약·연봉·가격·건수 등 수치를 집계하거나 조건으로 거르는 질문
knowledge_graph: 고객사-제품-직원-부서-프로젝트 사이의 관계(사용, 담당, 소속, 리드)를 묻는 질문
vector_search: 장애보고서·기술문서·회의록·제안서에 적힌 내용을 묻는 질문

도구 이름 하나만 출력한다. 다른 말은 쓰지 않는다.

질문: {question}
도구:"""


def _score(text: str, keywords: list, weight: int) -> int:
    return sum(weight for kw in keywords if kw in text)


def score_tools(question: str) -> dict:
    """도구별 점수를 반환한다 (디버깅·회귀 분석용)."""
    kg = _score(question, KG_RELATION, KG_WEIGHT)
    if ENTITY_NAME_PATTERN.search(question) and any(n in question for n in ENTITY_TYPE_NOUNS):
        kg += ENTITY_PAIR_WEIGHT

    sql = (
        _score(question, SQL_MEASURE, SQL_MEASURE_WEIGHT)
        + sum(SQL_MEASURE_WEIGHT for p in SQL_MEASURE_PATTERNS if p.search(question))
        + _score(question, SQL_TABLE_ONLY, SQL_TABLE_WEIGHT)
        + _score(question, SQL_WEAK, SQL_WEAK_WEIGHT)
    )
    if SQL_REGION_PATTERN.search(question) or SQL_PERIOD_PATTERN.search(question):
        sql += SQL_PATTERN_WEIGHT

    doc = _score(question, DOC_CONTENT, DOC_WEIGHT) + _score(question, DOC_WEAK, DOC_WEAK_WEIGHT)

    return {"nl2sql": sql, "knowledge_graph": kg, "vector_search": doc}


def route_by_rules(question: str) -> str | None:
    """규칙만으로 판정한다. 신호가 전혀 없으면 None을 반환한다."""
    scores = score_tools(question)
    top = max(scores.values())
    if top == 0:
        return None
    # 동점이면 TIE_PREFERENCE 순서로 결정한다 (dict 순서에 의존하지 않도록)
    for tool in TIE_PREFERENCE:
        if scores[tool] == top:
            return tool
    return None


def _route_by_llm(question: str) -> str | None:
    try:
        from llm_client import call_ollama

        answer = call_ollama(LLM_ROUTER_PROMPT.format(question=question), timeout=30).strip().lower()
    except Exception:
        return None
    for tool in TOOL_NAMES:
        if tool in answer:
            return tool
    return None


def route(question: str, allow_llm_fallback: bool = True) -> str:
    """question -> 'nl2sql' | 'knowledge_graph' | 'vector_search'

    규칙 점수가 하나라도 있으면 LLM을 부르지 않고 즉시 반환한다(빠른 경로).
    """
    ruled = route_by_rules(question)
    if ruled is not None:
        return ruled
    if allow_llm_fallback:
        guessed = _route_by_llm(question)
        if guessed is not None:
            return guessed
    return DEFAULT_TOOL


if __name__ == "__main__":
    for q in ["서울 지역 매출 상위 5개 고객사를 알려줘",
              "Client-A가 사용 중인 제품 목록은?",
              "최근 서버 장애 사례와 원인을 알려줘"]:
        print(f"{route(q):>15}  {score_tools(q)}  {q}")
