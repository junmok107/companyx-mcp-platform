-- ============================================================
-- 최소 권한 접속 role 생성
--
-- NL2SQL 도구는 LLM이 생성한 SQL을 실행하므로, 애플리케이션 레벨 검증만
-- 믿어서는 안 된다. superuser로 접속하면 검증을 통과한 SELECT 한 줄로
-- pg_read_file()(서버 파일 읽기), pg_shadow(비밀번호 해시 조회)까지 가능하다
-- (실측 확인됨). 따라서 조회 전용 role로 접속해 DB 레벨에서 권한을 제한한다.
--
-- 적용 (superuser로 실행). 비밀번호는 저장소에 남기지 않도록 실행 시 인자로 전달한다:
--   psql companyx -v reader_password="$(read -s -p 'password: ' p; echo $p)" -f sql/03-roles.sql
-- 또는 셸 변수에서:
--   psql companyx -v reader_password="$MCP_READER_PASSWORD" -f sql/03-roles.sql
-- ============================================================

DROP ROLE IF EXISTS mcp_reader;

CREATE ROLE mcp_reader
    LOGIN PASSWORD :'reader_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;

-- 접속 권한은 이 role에만 부여 (PUBLIC의 기본 접속 권한 회수)
REVOKE ALL ON DATABASE companyx FROM PUBLIC;
GRANT CONNECT ON DATABASE companyx TO mcp_reader;

-- 스키마는 읽기만: PostgreSQL 14 이하는 public 스키마에 CREATE 권한을
-- PUBLIC에 기본 부여하므로, 회수하지 않으면 조회 전용 계정도 테이블을 만들 수 있다.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO mcp_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_reader;

-- 확인용: 아래 쿼리가 모두 실패해야 정상
--   SELECT pg_read_file('/etc/hostname');      -- permission denied for function
--   SELECT usename, passwd FROM pg_shadow;     -- permission denied for view
--   DELETE FROM clients WHERE id = 1;          -- permission denied for table
--   CREATE TABLE evil(x int);                  -- permission denied for schema
