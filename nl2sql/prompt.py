"""NL2SQL 프롬프트 템플릿.

schema_context.md(테이블 설명)와 few-shot 예시를 결합해, 자연어 질문을
PostgreSQL SELECT 쿼리로 변환시키는 프롬프트를 만든다.

출력 규칙: LLM은 SQL 쿼리 문자열만 반환해야 한다 (설명, 마크다운 코드펜스 금지).
Step 3의 실행기가 응답을 그대로 세미콜론 기준으로 파싱하기 때문.
"""

from pathlib import Path

SCHEMA_CONTEXT_PATH = Path(__file__).resolve().parent.parent / "schema_context.md"

RULES = """\
당신은 PostgreSQL 전용 NL2SQL 변환기다. 아래 스키마 컨텍스트에 정의된 테이블과 컬럼만 사용해서,
사용자의 자연어 질문에 답하는 SELECT 쿼리를 한 개만 생성한다.

규칙:
1. SELECT 문만 작성한다. INSERT/UPDATE/DELETE/DROP/ALTER 등 쓰기 쿼리는 절대 생성하지 않는다.
2. 세미콜론으로 여러 문장을 이어 붙이지 않는다. 쿼리는 반드시 한 문장이다.
3. 스키마 컨텍스트에 없는 테이블/컬럼명을 지어내지 않는다.
4. "상위 N개", "가장 많은/적은" 같은 표현은 ORDER BY ... LIMIT N으로 처리한다.
5. 한글 카테고리 표현(보안/클라우드 등)은 스키마 컨텍스트의 영문 값(security/cloud 등)으로 매핑한다.
6. 출력은 SQL 쿼리 문자열 하나만 반환한다. 설명, 마크다운 코드펜스(```), 주석을 포함하지 않는다.
7. 부서명/고객사명/제품명 등으로 필터링할 때는 반드시 해당 테이블과 JOIN해서 name 컬럼으로 조건을 건다.
   id를 임의로 추측해서 하드코딩하지 않는다 (예: dept_id = 6 처럼 숫자를 직접 넣지 말 것).
"""

FEW_SHOT_EXAMPLES = [
    # 주의: 여기 질문 문장은 실제 테스트셋(questions.json)과 절대 겹치지 않게 유지한다.
    # 겹치면 모델이 "이미 답한 질문"으로 착각해 엉뚱한 값을 생성하는 현상이 실측됨.
    {
        "question": "부산 지역에서 매출이 가장 높은 고객사 3곳은?",
        "sql": (
            "SELECT c.name, SUM(s.amount) AS total_sales "
            "FROM sales s JOIN clients c ON s.client_id = c.id "
            "WHERE c.region = '부산' "
            "GROUP BY c.name "
            "ORDER BY total_sales DESC "
            "LIMIT 3;"
        ),
    },
    {
        "question": "2024년 1분기 총 매출액은?",
        "sql": "SELECT SUM(amount) AS total_amount FROM sales WHERE quarter = '2024-Q1';",
    },
    {
        "question": "완료된 계약은 몇 건이야?",
        "sql": "SELECT COUNT(*) AS completed_contract_count FROM contracts WHERE status = 'completed';",
    },
    {
        "question": "High 우선순위 티켓 중 아직 처리되지 않은 건은?",
        "sql": (
            "SELECT id, title, status, created_at FROM support_tickets "
            "WHERE priority = 'high' AND status IN ('open', 'in_progress');"
        ),
    },
    {
        "question": "영업팀 직원 목록과 연봉을 알려줘",
        "sql": (
            "SELECT e.name, e.salary FROM employees e "
            "JOIN departments d ON e.dept_id = d.id "
            "WHERE d.name = '영업팀';"
        ),
    },
]


def _load_schema_context() -> str:
    return SCHEMA_CONTEXT_PATH.read_text(encoding="utf-8")


def _format_few_shot() -> str:
    blocks = []
    for ex in FEW_SHOT_EXAMPLES:
        blocks.append(f"질문: {ex['question']}\nSQL: {ex['sql']}")
    return "\n\n".join(blocks)


def build_system_prompt() -> str:
    return f"{RULES}\n\n[스키마 컨텍스트]\n{_load_schema_context()}\n\n[예시]\n{_format_few_shot()}"


def build_nl2sql_prompt(question: str) -> dict:
    """LLM 호출용 messages 리스트를 반환한다 (system + user 역할 분리)."""
    return {
        "system": build_system_prompt(),
        "user": f"질문: {question}\nSQL:",
    }


if __name__ == "__main__":
    sample = build_nl2sql_prompt("보안 솔루션 카테고리 제품들의 월 평균 매출은?")
    print("--- system prompt 길이 ---")
    print(len(sample["system"]), "자")
    print("\n--- user turn ---")
    print(sample["user"])
