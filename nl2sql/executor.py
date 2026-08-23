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

# 시스템 카탈로그/관리 함수 접근 차단.
# pg_ 접두사만 막으면 information_schema와 접두사 없는 서버 정보 함수로 우회된다
# (실측: information_schema.tables로 스키마 열거, version()으로 서버 빌드 노출,
#  current_user로 계정 노출. 보안 레드팀에서 user/current_catalog/has_*_privilege
#  같은 별칭·정보 함수로 재우회되는 것도 확인 — 조회 전용 role에도 기본 허용이라
#  DB 권한만으로는 막히지 않는다).
# 주의: user/current_role 등은 컬럼명으로도 흔히 쓰이므로, 함수/특수 키워드로
# 해석되는 문맥(단어 경계 + 뒤에 컬럼 참조가 아닌 형태)만 잡도록 신중히 구성한다.
SYSTEM_OBJECT_PATTERN = re.compile(
    r"\bpg_[a-z_]+"
    r"|\binformation_schema\b"
    r"|\bcurrent_(?:user|role|schema|schemas|database|setting|catalog|query)\b"
    r"|\bsession_user\b"
    r"|\bhas_[a-z_]+_privilege\b"
    r"|\b(?:row_security_active|to_regclass|to_regrole|to_regnamespace)\b"
    r"|\bversion\s*\("
    r"|\btxid_[a-z_]+\s*\("
    r"|\binet_(?:server|client)_(?:addr|port)\b"
    r"|\blo_(?:import|export)\b",
    re.IGNORECASE,
)

# SQL 표준 니라리(niladic) 함수 — 괄호 없이 쓰이는 특수 키워드. 컬럼명 user와 구별하기 위해
# SELECT 목록이나 연산 위치에 단독으로 온 경우만 차단한다 (FROM/WHERE의 컬럼 참조는 제외).
BARE_IDENT_FUNCS = re.compile(
    r"(?:^|[\s,(])(?:user|current_catalog)(?=\s*(?:,|$|\)|\bAS\b|::|\bUNION\b))",
    re.IGNORECASE,
)

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

    found_bare = BARE_IDENT_FUNCS.search(masked)
    if found_bare:
        raise UnsafeQueryError(f"시스템 정보 함수 접근은 허용되지 않습니다: {found_bare.group(0).strip(', ()')}")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", masked, re.IGNORECASE):
            raise UnsafeQueryError(f"금지된 키워드가 포함되어 있습니다: {kw}")

    return stripped


def run_select(sql: str, row_limit: int = ROW_LIMIT_DEFAULT) -> dict:
    """검증을 통과한 SELECT 쿼리를 읽기 전용 트랜잭션으로 실행한다.

    반환값의 total_count는 상한과 무관한 실제 행 수다. 상한에 걸렸는데 가져온 행 수만
    보고하면 "총 200건"처럼 사실과 다른 총계를 단언하게 된다
    (실측: sales 500행 질의가 200건이라고 답했다). truncated가 True면 표시가 잘렸다는 뜻이다.
    """
    query = validate_select_only(sql)

    with psycopg.connect(DB_DSN) as conn:
        conn.read_only = True
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
            cur.execute(query)
            columns = [d.name for d in cur.description]
            rows = cur.fetchmany(row_limit)

            total = len(rows)
            truncated = len(rows) == row_limit
            if truncated:
                # 상한에 걸렸을 때만 실제 총계를 따로 센다 (평소에는 추가 비용 없음)
                try:
                    cur.execute(f"SELECT count(*) FROM ({query}) AS __total")
                    total = cur.fetchone()[0]
                except Exception:
                    total = None  # 총계를 못 구하면 '알 수 없음'으로 두고 답변에서 그렇게 밝힌다
        conn.rollback()

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "total_count": total,
        "truncated": truncated,
    }


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
        # pg_ 접두사를 피해가는 정보 노출 경로 (감사에서 실제로 뚫렸던 케이스 — 회귀 방지)
        ("SELECT table_name FROM information_schema.tables", False),
        ("SELECT column_name FROM information_schema.columns", False),
        ("SELECT current_user", False),
        ("SELECT session_user", False),
        ("SELECT version()", False),
        ("SELECT current_setting('data_directory')", False),
        ("SELECT inet_server_addr()", False),
        ("SELECT lo_import('/etc/hostname')", False),
        # 보안 레드팀에서 검증기를 우회했던 정보 함수들 (회귀 방지)
        ("SELECT user", False),
        ("SELECT user, name FROM clients", False),
        ("SELECT current_catalog", False),
        ("SELECT current_role", False),
        ("SELECT txid_current()", False),
        ("SELECT has_table_privilege('postgres','clients','SELECT')", False),
        ("SELECT to_regclass('pg_authid')", False),
        # user/current 가 컬럼명·문자열로 쓰인 정상 쿼리는 통과해야 함 (오탐 방지)
        ("SELECT count(*) FROM users_table WHERE active = true", True),
        ("SELECT name FROM clients WHERE name = 'super_user'", True),
        # 위 차단이 정상 쿼리를 막지 않는지 (오탐 방지)
        ("SELECT name, CASE WHEN region = '서울' THEN 1 ELSE 0 END FROM clients", True),
        ("SELECT CAST(id AS TEXT) FROM clients", True),
        ("SELECT name FROM clients ORDER BY id OFFSET 5 LIMIT 3", True),
        ("SELECT name FROM clients WHERE id IN (SELECT client_id FROM contracts)", True),
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
