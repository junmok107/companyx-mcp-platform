"""LLM이 생성한 SQL을 안전하게 실행하는 실행기.

방어 계층 (하나가 뚫려도 다음 계층이 막도록 구성):
1. DB 권한: 조회 전용 role(mcp_reader)로 접속 — sql/03-roles.sql 참고.
   이것이 가장 중요한 계층이다. superuser로 접속하면 아래 문자열 검증을 정상적으로
   통과하는 SELECT 한 줄로 pg_read_file()(서버 파일 읽기), pg_shadow(비밀번호 해시)
   까지 읽을 수 있다(실측 확인됨). 애플리케이션 검증만으로는 막을 수 없다.
2. 문자열 검증: SELECT 단일 문장인지, 금지 키워드/주석/시스템 카탈로그 접근이 없는지 확인
3. 읽기 전용 트랜잭션 + statement_timeout으로 쓰기와 폭주 쿼리 차단
"""

import os
import re

import psycopg

# 비밀번호는 DSN 문자열에 넣지 않는다 — PGPASSWORD 환경변수 또는 .pgpass로 관리
# (로컬 개발 DB 접속 정보이며, 이 저장소는 대회 규정상 공개되므로 자격정보를 코드에 넣지 않는다)
# 기본값은 WSL(Ubuntu-22.04)에 pgvector 포함해 띄운 PostgreSQL 14, 포트 5434 기준.
DB_DSN = os.environ.get("COMPANYX_DB_DSN", "dbname=companyx host=localhost port=5434 user=mcp_reader")
STATEMENT_TIMEOUT_MS = 5000
ROW_LIMIT_DEFAULT = 200

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "EXECUTE", "CALL", "COPY", "MERGE", "VACUUM",
    "REINDEX", "SET", "RESET",
]

# 시스템 카탈로그/관리 함수 접근 차단 (pg_read_file, pg_shadow, pg_stat_* 등).
# DB 권한으로도 막히지만, 스키마 열거 자체를 애플리케이션 레벨에서도 거부한다.
SYSTEM_OBJECT_PATTERN = re.compile(r"\bpg_[a-z_]+", re.IGNORECASE)

# SQL 문자열 리터럴 ('...', 내부의 '' 이스케이프 포함)
STRING_LITERAL_PATTERN = re.compile(r"'(?:[^']|'')*'")


class UnsafeQueryError(ValueError):
    """검증을 통과하지 못한 쿼리에 대해 발생시키는 예외."""


def _mask_string_literals(sql: str) -> str:
    """문자열 리터럴 내용을 비운다.

    검증은 이 마스킹된 문자열을 대상으로 수행한다. 리터럴 안의 세미콜론이나 하이픈은
    실행되는 SQL이 아니라 데이터이므로(예: WHERE name = 'A;B'), 그대로 검사하면
    정상 쿼리를 오탐으로 거부하게 된다. 반대로 공격자가 리터럴 안에 키워드를 숨겨도
    그것 역시 실행되지 않는 데이터이므로 마스킹해도 안전하다.
    """
    return STRING_LITERAL_PATTERN.sub("''", sql)


def validate_select_only(sql: str) -> str:
    """SELECT 단일 문장인지 검증하고, 통과하면 정제된 쿼리 문자열을 반환한다."""
    cleaned = (sql or "").strip()
    if not cleaned:
        raise UnsafeQueryError("빈 쿼리는 실행할 수 없습니다")

    # 끝의 세미콜론 하나는 허용하고 제거
    stripped = cleaned[:-1].strip() if cleaned.endswith(";") else cleaned
    masked = _mask_string_literals(stripped)

    if ";" in masked:
        raise UnsafeQueryError("다중 SQL 문장은 허용되지 않습니다")

    if "--" in masked or "/*" in masked:
        raise UnsafeQueryError("SQL 주석은 허용되지 않습니다 (검증 우회 시도로 간주)")

    if not re.match(r"^\s*SELECT\b", masked, re.IGNORECASE):
        raise UnsafeQueryError("SELECT 문만 허용됩니다")

    found_system = SYSTEM_OBJECT_PATTERN.search(masked)
    if found_system:
        raise UnsafeQueryError(f"시스템 카탈로그/관리 함수 접근은 허용되지 않습니다: {found_system.group(0)}")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", masked, re.IGNORECASE):
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
        # 시스템 카탈로그/관리 함수 (superuser 접속 시 실제로 유출됐던 케이스 — 회귀 방지)
        ("SELECT pg_read_file('/etc/hostname')", False),
        ("SELECT usename, passwd FROM pg_shadow", False),
        ("SELECT datname FROM pg_database", False),
        # 문자열 리터럴 안의 특수문자는 데이터이므로 거부하면 안 됨 (오탐 회귀 방지)
        ("SELECT * FROM clients WHERE name = 'A;B'", True),
        ("SELECT * FROM clients WHERE name = 'A--B'", True),
        # 리터럴 마스킹이 실제 공격까지 통과시키지는 않는지 확인
        ("SELECT * FROM clients WHERE name = 'x'; DROP TABLE clients", False),
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
