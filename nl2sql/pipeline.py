"""NL2SQL 엔드투엔드 파이프라인: 질문 → SQL 생성 → 실행 → 자연어 답변.

라우터 연동 규격에 맞춰 { answer, raw_data, source } 형식으로 반환한다.
"""

from answer import generate_answer
from executor import UnsafeQueryError, run_select
from llm_client import call_ollama
from prompt import build_nl2sql_prompt


def _clean_sql(text: str) -> str:
    """LLM이 규칙을 어기고 마크다운 코드펜스를 붙이는 경우를 방어적으로 제거한다."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # 첫 줄의 ```sql 제거
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_sql(question: str) -> str:
    p = build_nl2sql_prompt(question)
    full_prompt = f"{p['system']}\n\n{p['user']}"
    raw = call_ollama(full_prompt)
    return _clean_sql(raw)


def answer_question(question: str) -> dict:
    sql = generate_sql(question)
    try:
        result = run_select(sql)
    except UnsafeQueryError as e:
        return {"answer": f"안전하지 않은 쿼리라 실행을 거부했습니다: {e}", "raw_data": None, "source": "nl2sql", "sql": sql}
    except Exception as e:
        return {"answer": f"쿼리 실행 중 오류가 발생했습니다: {e}", "raw_data": None, "source": "nl2sql", "sql": sql}

    answer_text = generate_answer(question, result)
    return {"answer": answer_text, "raw_data": result, "source": "nl2sql", "sql": sql}


if __name__ == "__main__":
    out = answer_question("현재 활성 상태인 계약 수는 몇 개야?")
    print("SQL:", out["sql"])
    print("ANSWER:", out["answer"])
