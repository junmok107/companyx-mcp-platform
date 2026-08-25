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
bridge/           HTTP 브릿지 — 세 도구를 웹에서 부를 수 있게 FastAPI로 감쌈
frontend/         React + Vite 콘솔 UI (브릿지를 통해 실데이터 연동)
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
pip install fastapi uvicorn        # 웹 프론트엔드용 HTTP 브릿지에만 필요
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

### 6. 웹 프론트엔드 (선택)

MCP 서버는 stdio 프로토콜이라 브라우저에서 직접 못 부른다. `bridge/server.py`가 세 도구
파이프라인을 그대로 import해 HTTP(`/ask`, `/tool/{name}`, `/health`)로 노출하고,
`frontend/`(React + Vite)가 이를 호출한다.

```bash
# (1) 브릿지 — 환경변수는 위 3번과 동일
python -m uvicorn bridge.server:app --host 127.0.0.1 --port 8000

# (2) 프론트엔드 — 별도 터미널
cd frontend && npm install && npm run dev   # http://localhost:5173
```

브릿지 응답 계약은 [`docs/frontend_requirements.md`](docs/frontend_requirements.md)에,
프론트엔드의 어댑터는 [`frontend/src/lib/api.js`](frontend/src/lib/api.js)에 있다.

## 테스트

각 도구 및 통합(라우터) 테스트는 `questions.json`의 예시 질문 30개(도구별 10개)를 기준으로 한다.

```bash
python nl2sql/test_nl2sql.py
python knowledge_graph/test_kg.py
python vector_search/test_vector.py
python mcp_server/test_router.py        # 라우터 정확도 (TUNED/HOLDOUT/FRESH 구분)
python nl2sql/executor.py               # SQL 검증·공격 차단 회귀 (DB 불필요)
python mcp_server/test_integration.py   # 라우터+도구 통합
```

### 도구별 정확도

`questions.json`의 30문항과, 그것과 별개로 작성한 감사용 문항을 함께 사용한다.
정답은 hint를 믿지 않고 독립적으로 계산했다 — NL2SQL은 손으로 쓴 기준 SQL, 지식 그래프는
raw JSON 직접 순회, 벡터 검색은 문서 원문 검색으로 정답 문서를 확정했다.
답변 텍스트가 조회 결과를 빠짐없이 담고 있는지도 프로그램으로 대조한다.

| 항목 | 결과 | 측정 방법 |
|---|---|---|
| NL2SQL | 16/16 | 기준 SQL 독립 작성 대조. NULL·MAX·LIKE·미존재 데이터 등 신규 6문항 포함 |
| 지식 그래프 | 14/14 completeness, 환각 0/3 | raw `nodes.json`/`edges.json` 직접 순회. 미존재 엔티티 3건은 모두 거부 |
| 벡터 검색 | Recall@1·3·5 각 8/8, 근거 정확도 8/8 | 정답 문서를 원문 검색으로 확정 |
| 벡터 검색 — 코퍼스 밖 질문 | 거부 5/5 | 데이터셋에 없는 주제를 물었을 때 답을 지어내지 않음 |
| 벡터 검색 — 패러프레이즈 | 3/4 | 원문과 어휘가 겹치지 않게 바꿔 쓴 질문 |
| SQL 검증 | 28/28 | 공격 차단 + 정상 쿼리 오탐 방지 양쪽, DB 연결 불필요 |

`questions.json` Q24 "서울물산 담당 엔지니어는 누구야?"의 "서울물산"은 데이터셋 어디에도
없다(`sql/`, `graph/`의 properties 포함 전체 문자열, `documents/`, `index.json` 전수 확인).
모든 고객사명이 `Client-X` 형식이라 애초에 매칭될 수 없다. 질문 텍스트와 데이터가 어긋난
데이터셋 자체의 오류이며 구현으로 해결할 수 없다.

### 라우터 정확도 — 세트를 구분해서 볼 것

키워드 규칙은 튜닝에 쓴 질문으로 재면 항상 100%가 나온다. 그 숫자는 일반화 성능이 아니다.

| 세트 | 결과 | 성격 |
|---|---|---|
| questions.json 30문항 | 30/30 | 이 세트를 보며 튜닝함 — 참고용 |
| 1차 held-out 18문항 | 18/18 | 초기 15/18(83%), 실패를 근거로 설계 수정 — 이제 튜닝된 세트 |
| 2차 held-out 15문항 | 15/15 | 이후 작성했으나 이 역시 수정에 반영됨 |
| 감사용 신규 50문항 | 정답 단일 35문항 중 **34/35 (97%)** | 애매/다중의도/구어체 포함. 최초 측정 30/35(86%) |

감사용 세트에서 규칙 점수가 0이라 LLM 폴백이 처리한 문항은 19/50이었다.
반면 위 세 세트(63문항)에서는 폴백이 한 번도 발동하지 않아 빠른 경로가 유지된다.

### 성능 (실측, 10회 이상 반복)

| 구간 | 중앙값 | 비고 |
|---|---|---|
| 라우터 — 규칙 경로 | 0.00ms | n=200, max 0.03ms |
| 라우터 — LLM 폴백 경로 | **2,771ms** | 규칙 점수가 0일 때만 발동 |
| 질의 임베딩 생성 | **2,097ms** | 벡터 검색 지연의 대부분 |
| pgvector 유사도 검색 | 약 105ms | 임베딩 시간 제외 |
| 리랭킹 (순수 계산) | 2.1ms | n=100 |
| DB SELECT | 60ms | |
| NL2SQL — 목록형 (LLM 요약 없음) | 4,989ms | cold 7,411ms |
| NL2SQL — 단일값 (LLM 문장화) | 9,035ms | cold 9,510ms |
| 지식 그래프 — 목록형 | 4,708ms | cold 5,852ms |
| 벡터 검색 | 6,054ms | cold 6,706ms |

## 도구 반환 규격

세 도구와 `ask` 모두 동일한 형태로 반환한다.

| 필드 | 내용 |
|---|---|
| `answer` | 사용자에게 보여줄 자연어 답변 |
| `raw_data` | 도구가 실제로 조회한 원자료 (행 목록 / 그래프 노드 / 청크) |
| `tool` | 응답을 만든 도구 이름 |
| `source` | **근거 목록**. NL2SQL은 실행된 SQL, 지식 그래프는 노드 id, 벡터 검색은 문서 id |

`ask`는 여기에 라우팅 결과 `routed_to`를 덧붙이고, NL2SQL은 `sql`, 지식 그래프는 `spec`을
도구별 부가 정보로 함께 반환한다. 빈 질문과 2,000자 초과 입력은 도구 실행 전에 거부되며,
내부 오류도 예외를 던지지 않고 같은 형태의 응답으로 돌려준다.

## 보안

NL2SQL 도구는 LLM이 생성한 SQL을 실행하므로 애플리케이션 검증만으로는 부족하다.
실제로 공격을 시도해 확인한 사항:

- superuser로 접속하면 문자열 검증을 **정상적으로 통과하는 SELECT 한 줄**로
  `pg_read_file()`(서버 파일 읽기)과 `pg_shadow`(비밀번호 해시)를 읽을 수 있다.
  읽기 전용 트랜잭션은 쓰기만 막을 뿐 이를 막지 못한다.
- 따라서 조회 전용 role(`sql/03-roles.sql`)로 접속하는 것이 1차 방어선이다.
  이 role은 SELECT만 가능하고, 관리 함수·시스템 뷰·스키마 생성·임시 객체가 모두 거부된다.
- 애플리케이션 검증(`nl2sql/executor.py`)은 그 위의 2차 방어선이다: SELECT 단일 문장만 허용,
  주석·다중문장·쓰기 키워드 거부. 시스템 객체는 `pg_*`뿐 아니라 `information_schema`와
  접두사가 없는 서버 정보 함수(`version()`, `current_user`, `inet_server_addr()` 등)까지 막는다.
  이들은 조회 전용 role에도 기본 허용이라 DB 권한만으로는 차단되지 않는다.
  문자열 리터럴 내부는 마스킹 후 검사하므로 `WHERE name = 'A;B'` 같은 정상 쿼리는 통과한다.
- 회귀 테스트: `python nl2sql/executor.py` (28개 케이스, DB 연결 불필요)

## 알려진 한계

- **패러프레이즈 일부를 놓친다.** 원문과 어휘가 겹치지 않게 바꿔 쓴 질문 4개 중 3개는
  하이브리드 검색(벡터 + 어휘)으로 회수되지만, 남은 1개는 어휘 검색으로 후보에는 들어와도
  재순위에서 밀려 답변에 반영되지 않는다. 코사인 유사도만으로 관련성을 가르는 것은
  이 코퍼스에서 불가능했다 (코퍼스 내 최저 0.660 < 코퍼스 밖 최고 0.790).
- **목록형 답변은 LLM 요약을 쓰지 않는다.** gemma2:9b는 여러 행을 요약할 때 일부를 조용히
  누락한다(실측: 5행 중 1행만 언급, 11명 중 9명만 언급 — 5회 반복 모두 동일하게 재현).
  조회 결과를 빠짐없이 전달하는 것이 우선이라 결정론적 렌더링으로 대체했다.
- **라우터 키워드 사전은 표현이 달라지면 점수가 0이 된다.** LLM 폴백이 이를 보완하지만
  해당 질문은 약 2.8초가 추가된다. 감사용 신규 50문항에서는 19건이 폴백을 탔다.
- **지식 그래프 답변의 근거는 노드 id**라 사람이 바로 읽기 어렵다. 이름은 `raw_data`에 있다.
- 문서 데이터에 이름이 같은 서로 다른 프로젝트가 있어(예: "Client-B CI/CD 파이프라인 구축"),
  관련 프로젝트 조회 시 같은 이름이 중복 표시될 수 있다. 데이터 그대로의 결과다.

## 준수 사항

- 로컬 오픈웨이트 LLM(Ollama)만 사용, 외부 상용 API 미사용
- 직접 작성한 소스코드는 MIT 라이선스([LICENSE](LICENSE)) 적용
- 비밀번호 등 자격 증명은 코드에 포함하지 않고 환경 변수로만 전달

## 라이선스

MIT License. [LICENSE](LICENSE) 참고.
