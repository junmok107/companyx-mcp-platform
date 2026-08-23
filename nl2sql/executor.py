"""LLM이 생성한 SQL을 안전하게 실행하는 실행기.

방어 계층 (하나가 뚫려도 다음 계층이 막도록 구성):
1. 문자열 검증: SELECT 단일 문장인지, 금지 키워드/주석이 없는지 확인
2. DB 세션 자체를 읽기 전용(read-only) 트랜잭션으로 열어서, 검증을 통과한
   악성 쿼리가 있더라도 DB 레벨에서 쓰기가 물리적으로 차단되도록 함
3. statement_timeout으로 폭주 쿼리 방지
"""

import os
import re

import psycopg

# 비밀번호는 DSN 문자열에 넣지 않는다 — PGPASSWORD 환경변수 또는 .pgpass로 관리
# (로컬 개발 DB 접속 정보이며, 이 저장소는 대회 규정상 공개되므로 자격정보를 코드에 넣지 않는다)
# 기본값은 WSL(Ubuntu-22.04)에 pgvector 포함해 띄운 PostgreSQL 14, 포트 5434 기준.
# (Windows 네이티브 PostgreSQL 17/18에는 pgvector가 없어 document_chunks 테이블을 못 만듦 — DEV_DB_SETUP.md 참고)
DB_DSN = os.environ.get("COMPANYX_DB_DSN", "dbname=companyx host=localhost port=5434 user=postgres")
STATEMENT_TIMEOUT_MS = 5000
ROW_LIMIT_DEFAULT = 200

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "EXECUTE", "CALL", "COPY", "MERGE", "VACUUM",
    "REINDEX", "SET", "RESET",
]


class UnsafeQueryError(ValueError):
    """검증을 통과하지 못한 쿼리에 대해 발생시키는 예외."""


def validate_select_only(sql: str) -> str:
    """SELECT 단일 문장인지 검증하고, 통과하면 정제된 쿼리 문자열을 반환한다."""
    cleaned = (sql or "").strip()
    if not cleaned:
        raise UnsafeQueryError("빈 쿼리는 실행할 수 없습니다")

    # 끝의 세미콜론 하나는 허용하고 제거, 남은 부분에 세미콜론이 있으면 다중 문장으로 간주
    stripped = cleaned[:-1].strip() if cleaned.endswith(";") else cleaned
    if ";" in stripped:
        raise UnsafeQueryError("다중 SQL 문장은 허용되지 않습니다")

    if "--" in stripped or "/*" in stripped:
        raise UnsafeQueryError("SQL 주석은 허용되지 않습니다 (검증 우회 시도로 간주)")

    if not re.match(r"^\s*SELECT\b", stripped, re.IGNORECASE):
        raise UnsafeQueryError("SELECT 문만 허용됩니다")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", stripped, re.IGNORECASE):
            raise UnsafeQueryError(f"금지된 키워드가 포함되어 있습니다: {kw}")

    return stripped


def run_select(sql: str, row_limit: int = ROW_LIMIT_DEFAULT) -> dict:
    """검증을 통과한 SELECT 쿼리를 읽기 전용 트랜잭션으로 실행한다."""
    query = validate_select_only(sql)

    with psycopg.connect(DB_DSN) as conn:
        conn.read_only = True
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
            cur.execute(query)
            columns = [d.name for d in cur.description]
            rows = cur.fetchmany(row_limit)
        conn.rollback()

    return {"columns": columns, "rows": rows, "row_count": len(rows)}


if __name__ == "__main__":
    # DB 연결 없이 검증 로직만 오프라인으로 점검
    test_cases = [
        ("SELECT * FROM clients WHERE region = '서울';", True),
        ("SELECT COUNT(*) FROM contracts WHERE status = 'active'", True),
        ("DROP TABLE clients;", False),
        ("SELECT * FROM clients; DROP TABLE clients;", False),
        ("SELECT * FROM clients WHERE name = 'x' -- ' OR 1=1", False),
        ("UPDATE clients SET name = 'x'", False),
        ("SELECT * FROM clients /* comment */", False),
        ("", False),
        ("SELECT * FROM settings_table", True),  # SET 부분 단어 오탐 방지 확인
        ("SELECT * FROM tickets WHERE resolved_at IS NULL", True),  # DELETE 부분 단어(resolved) 오탐 방지
    ]
    passed = 0
    for sql, should_pass in test_cases:
        try:
            validate_select_only(sql)
            ok = should_pass is True
        except UnsafeQueryError as e:
            ok = should_pass is False
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status}] expected_pass={should_pass} sql={sql!r}")
    print(f"\n{passed}/{len(test_cases)} 검증 테스트 통과")
