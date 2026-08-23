# MCP 기반 통합 지능형 데이터 검색 플랫폼

2026 오픈소스 개발자대회 · 리원에이스 지정과제("MCP 기반 지능형 데이터 플랫폼 클러스터") 출품작.

PostgreSQL(정형 데이터 + pgvector), 온프레미스 오픈웨이트 LLM(Ollama), 지식 그래프를 MCP(Model Context Protocol) 표준으로 연결해, 사용자가 자연어로 질문하면 NL2SQL·지식 그래프·벡터 검색 세 도구 중 알맞은 것을 규칙 기반 라우터가 자동으로 골라 답하는 시스템입니다.

원본 데이터셋 설명은 [DATASET.md](DATASET.md) 참고.

## 아키텍처

![Company-X MCP 시스템 아키텍처](docs/architecture.svg)

질문 1건이 처리되는 순서: **질문 → 라우터가 키워드 점수로 도구 선택 → 선택된 도구 실행(SQL 생성/그래프 순회/문서 검색) → 필요 시 Ollama·PostgreSQL 호출 → 근거(source)와 함께 자연어 답변 반환**.

## 디렉터리 구조

```
nl2sql/           NL2SQL 도구 — 자연어→SQL 변환, 읽기 전용 실행, 답변 생성
knowledge_graph/  지식 그래프 도구 — 질문→탐색 스펙 추출, networkx 순회, 답변 생성
vector_search/    벡터 검색 도구 — 문서 임베딩 파이프라인, pgvector 유사도 검색, 리랭킹, 답변 생성
mcp_server/       MCP 서버 — 위 3개 도구를 MCP 프로토콜로 노출, 규칙 기반 라우터
sql/, documents/, graph/, questions.json   원본 데이터셋 (DATASET.md 참고)
핵심로직_작업계획_및_검증기준.md   각 도구 설계 근거, 디버깅 기록, 통과 기준
```

## 설치 및 실행

### 1. 의존성

- Python 3.11+
- PostgreSQL 15+ (pgvector 확장 필수 — Windows 네이티브 PostgreSQL은 pgvector 미지원이라 **WSL 위에 별도 구축**함)
- [Ollama](https://ollama.com) — `gemma2:9b`(생성), `nomic-embed-text`(임베딩, 768차원)

```bash
pip install psycopg mcp networkx
ollama pull gemma2:9b
ollama pull nomic-embed-text
```

### 2. 데이터베이스 준비

```bash
# WSL 등 pgvector를 지원하는 PostgreSQL에서
createdb companyx
psql companyx -c "CREATE EXTENSION vector;"
psql companyx -f sql/01-schema.sql
psql companyx -f sql/02-data.sql
# 조회 전용 role 생성 (아래 '보안' 참고, 생략 불가).
# 비밀번호는 저장소에 남기지 않도록 실행 시 인자로 전달한다.
psql companyx -v reader_password="$MCP_READER_PASSWORD" -f sql/03-roles.sql
```

### 3. 환경 변수

```bash
export COMPANYX_DB_DSN="dbname=companyx host=localhost port=5434 user=mcp_reader"
export PGPASSWORD="<mcp_reader 비밀번호>"   # 자격증명은 코드에 하드코딩하지 않음
export OLLAMA_HOST="http://localhost:11434"

# 임베딩 적재(4단계)에만 필요한 쓰기 권한 계정 — 질의 경로에서는 쓰지 않는다
export COMPANYX_ADMIN_DSN="dbname=companyx host=localhost port=5434 user=postgres"
```

### 4. 문서 임베딩 적재 (최초 1회)

```bash
python vector_search/embed.py
```

### 5. MCP 서버 실행

```bash
python mcp_server/server.py
```

## 테스트

각 도구 및 통합(라우터) 테스트는 `questions.json`의 예시 질문 30개(도구별 10개)를 기준으로 한다.

```bash
python nl2sql/test_nl2sql.py
python knowledge_graph/test_kg.py
python vector_search/test_vector.py
python mcp_server/test_router.py        # 라우터 단독 정확도
python mcp_server/test_integration.py   # 라우터+도구 통합
```

### 도구별 정확도

DB·그래프에서 정답을 직접 계산해 대조한 결과 기준. 답변 텍스트가 조회 결과를 빠짐없이
담고 있는지까지 확인했다(눈으로 훑어 "그럴듯하면 통과"로 처리하지 않음).

| 항목 | 결과 | 비고 |
|---|---|---|
| NL2SQL | 10/10 | SQL 생성·실행·답변 모두 정답 일치 |
| 지식 그래프 | 9/10 | 실패 1건은 데이터셋 결함(아래) — 구현으로 해결 불가 |
| 벡터 검색 | 10/10 | 근거 문서(source) 포함 |

`questions.json` Q24 "서울물산 담당 엔지니어는 누구야?"의 "서울물산"은 `graph/`, `documents/`,
`sql/` 어디에도 존재하지 않는다. hint는 Client-B를 가리키지만 질문 텍스트와 데이터가 어긋난
데이터셋 자체의 오류다.

### 라우터 정확도 — 세트를 구분해서 볼 것

키워드 규칙은 튜닝에 쓴 질문으로 재면 항상 100%가 나온다. 그 숫자는 일반화 성능이 아니다.

| 세트 | 결과 | 성격 |
|---|---|---|
| questions.json 30문항 | 30/30 | 이 세트를 보며 튜닝함 — 참고용 |
| 1차 held-out 18문항 | 18/18 | 초기 15/18(83%), 실패를 근거로 설계 수정 — 이제 튜닝된 세트 |
| 2차 held-out 15문항 | 15/15 | 설계 수정 후 작성, 튜닝에 미사용 — **일반화 지표** |

2차 세트 15문항 중 7건은 규칙 점수가 0이라 LLM 폴백이 처리했다. 규칙만으로는 12/15였다.
튜닝 세트 48문항에서는 폴백이 한 번도 발동하지 않아 빠른 경로(0.002ms)가 유지된다.

### 성능 (실측)

| 구간 | 지연 |
|---|---|
| 라우터 규칙 판정 | 0.002ms |
| NL2SQL — 목록형 결과 | 4.9s |
| NL2SQL — 단일값 결과 | 8.8s |
| 지식 그래프 — 목록형 결과 | 4.6s |
| 벡터 검색 | 6.0s |

지연의 대부분은 Ollama 추론이고 DB 조회는 60ms 수준이다. 목록형 결과는 LLM 요약을 거치지
않으므로(정확도 문제 때문, 아래 참고) 단일값 질의보다 오히려 빠르다.

## 보안

NL2SQL 도구는 LLM이 생성한 SQL을 실행하므로 애플리케이션 검증만으로는 부족하다.
실측으로 확인한 사항:

- superuser로 접속하면 문자열 검증을 **정상적으로 통과하는 SELECT 한 줄**로
  `pg_read_file()`(서버 파일 읽기)과 `pg_shadow`(비밀번호 해시)를 읽을 수 있다.
  읽기 전용 트랜잭션은 쓰기만 막을 뿐 이를 막지 못한다.
- 따라서 조회 전용 role(`sql/03-roles.sql`)로 접속하는 것이 1차 방어선이다.
  이 role은 SELECT만 가능하고, 관리 함수·시스템 뷰·스키마 생성이 모두 거부된다.
- 애플리케이션 검증(`nl2sql/executor.py`)은 그 위의 2차 방어선이다: SELECT 단일 문장만 허용,
  주석·다중문장·쓰기 키워드·`pg_*` 접근 거부. 문자열 리터럴 내부는 마스킹 후 검사하므로
  `WHERE name = 'A;B'` 같은 정상 쿼리를 오탐으로 거부하지 않는다.
- 회귀 테스트: `python nl2sql/executor.py` (16개 케이스, DB 연결 불필요)

## 알려진 한계

- **벡터 검색 관련성 판정은 어휘 겹침 기반**이다. 코퍼스 내 질문 10개는 모두 통과하고 코퍼스
  밖 질문 6개는 모두 차단되지만, 의미는 같은데 어휘가 전혀 겹치지 않는 순수 패러프레이즈
  (예: "서버가 멈춘 적 있어?" ↔ "장애")는 놓친다. 코사인 유사도로는 이 구분이 불가능했다
  (코퍼스 내 최저 0.660 < 코퍼스 밖 최고 0.790).
- **목록형 답변은 LLM 요약을 쓰지 않는다.** gemma2:9b는 여러 행을 요약할 때 일부를 조용히
  누락한다(실측: 5행 중 1행만 언급, 11명 중 9명만 언급 — 5회 반복 모두 동일하게 재현).
  조회 결과를 빠짐없이 전달하는 것이 우선이라 결정론적 렌더링으로 대체했다.
- 라우터 키워드 사전은 표현이 달라지면 점수가 0이 된다. LLM 폴백이 이를 보완하지만
  그만큼 해당 질문은 응답이 느려진다.

## 준수 사항

- 로컬 오픈웨이트 LLM(Ollama)만 사용, 외부 상용 API 미사용
- 직접 작성한 소스코드는 MIT 라이선스([LICENSE](LICENSE)) 적용
- 비밀번호 등 자격 증명은 코드에 포함하지 않고 환경 변수로만 전달

## 라이선스

MIT License. [LICENSE](LICENSE) 참고.
