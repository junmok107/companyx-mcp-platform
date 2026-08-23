"""규칙 기반 라우터: 질문을 nl2sql / knowledge_graph / vector_search 중 하나로 분류한다.

MCP Parallel 패턴 — LLM 호출 없이 키워드 점수로 즉시 라우팅해서 지연시간과 장애 지점을 줄인다.
각 도구별 점수를 매겨 최고점 도구를 선택한다 (동점이면 우선순위: knowledge_graph > nl2sql > vector_search,
관계 질문이 집계 질문 표현과 자주 겹쳐서 더 구체적인 신호를 우선시).
"""

import re

# 그래프 관계를 직접 가리키는 동사/명사 — 정형 데이터에는 없는, 관계 탐색 특유의 표현.
# 관계를 명시하는 동사(이끄는/담당/소속 등)는 "직원 목록"처럼 SQL과 겹치는 명사보다 신호가 강해서 가중치 2를 준다.
KG_KEYWORDS_STRONG = ["담당", "소속", "이끄는", "이끌", "팀장", "부서장", "관리하는", "관리 담당"]
KG_KEYWORDS_WEAK = ["사용 중인", "사용하는", "사용 중", "관련된", "관련 있는", "이슈 현황", "이슈"]
# 엔티티 이름 패턴: Client-A, Product-C1 같은 식별자 (그래프 노드 이름과 일치)
KG_ENTITY_PATTERN = re.compile(r"(Client|Product)-[A-Za-z0-9]+")

# 정형 데이터 집계/조회 특유의 표현 — 테이블 컬럼과 직접 대응
SQL_KEYWORDS = [
    "매출", "계약", "티켓", "연봉", "등록된", "분기", "카테고리", "활성 상태",
    "우선순위", "직원 목록", "총", "평균", "얼마", "몇 개", "몇 명", "상위", "프로젝트",
]
SQL_REGION_PATTERN = re.compile(r"서울|경기|인천|대전|대구|부산|광주|제주")
SQL_QUARTER_PATTERN = re.compile(r"\d{4}년|\d분기")

# 비정형 문서 검색 특유의 표현 — 문서 타입/내용을 가리킴
DOC_KEYWORDS = [
    "장애", "사례", "설치", "가이드", "매뉴얼", "튜닝", "방법", "레퍼런스",
    "회의", "미팅", "논의", "제안서", "도입", "정책", "취약점", "API", "인증",
]


def _score(text: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def route(question: str) -> str:
    """question -> 'nl2sql' | 'knowledge_graph' | 'vector_search'"""
    kg_score = _score(question, KG_KEYWORDS_STRONG) * 2 + _score(question, KG_KEYWORDS_WEAK)
    if KG_ENTITY_PATTERN.search(question):
        kg_score += 1  # Client-A/Product-C1 언급은 신호이지만, 문서 키워드와 겹치면 문서 검색이 우선될 수 있음

    sql_score = _score(question, SQL_KEYWORDS)
    if SQL_REGION_PATTERN.search(question) or SQL_QUARTER_PATTERN.search(question):
        sql_score += 1

    doc_score = _score(question, DOC_KEYWORDS)

    scores = {"knowledge_graph": kg_score, "nl2sql": sql_score, "vector_search": doc_score}
    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "vector_search"  # 아무 신호도 없으면 문서 검색으로 폴백 (가장 넓은 커버리지)
    return best


if __name__ == "__main__":
    tests = [
        ("서울 지역 매출 상위 5개 고객사를 알려줘", "nl2sql"),
        ("Client-A가 사용 중인 제품 목록은?", "knowledge_graph"),
        ("최근 서버 장애 사례와 원인을 알려줘", "vector_search"),
    ]
    for q, expected in tests:
        got = route(q)
        print(f"{'OK ' if got == expected else 'FAIL'} {q!r} -> {got} (expected {expected})")
