# Company-X DB 스키마 컨텍스트 (NL2SQL 프롬프트용)

> 출처: `sql/01-schema.sql`(DDL), `sql/02-data.sql`(실 데이터 값 확인), `sql/erd.md`(관계도)
> 이 문서는 NL2SQL 프롬프트의 시스템 메시지에 그대로 포함시켜 LLM이 정확한 컬럼명·값을 참조하도록 한다.

## 테이블 관계 요약

```
departments 1─N employees (employees.dept_id → departments.id)
departments 1─1 employees (departments.head_id → employees.id, 부서장)
clients 1─N contracts, clients 1─N projects, clients 1─N sales, clients 1─N support_tickets
products 1─N contracts, products 1─N sales, products 1─N support_tickets
employees 1─N contracts(manager_id), employees 1─N projects(manager_id), employees 1─N support_tickets(assignee_id)
contracts 1─N sales (sales.contract_id → contracts.id)
contracts 1─1 projects (projects.contract_id → contracts.id, nullable)
```

---

## 1. departments (부서) — 6행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 부서 ID | 1~6 |
| name | VARCHAR(50) | 부서명 | 경영지원팀, 클라우드사업부, 보안솔루션팀, 데이터플랫폼팀, 기술지원팀, 영업팀 |
| head_id | INTEGER FK→employees.id | 부서장 직원 ID | |

## 2. employees (직원) — 45행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 직원 ID | |
| name | VARCHAR(50) | 이름 | 윤소연, 안진우 등 (한글 이름) |
| email | VARCHAR(100) | 이메일 | `*@companyx.co.kr` |
| position | VARCHAR(50) | 직급 | 사원, 대리, 과장, 차장, 부장, 이사 |
| dept_id | INTEGER FK→departments.id | 소속 부서 | 1~6 |
| hire_date | DATE | 입사일 | |
| salary | INTEGER | 연봉(단위: 만원 추정) | 3736~9520 범위 |
| is_active | BOOLEAN | 재직 여부 | 기본 TRUE |

**주의**: "~팀장", "~부서장" 질문은 `departments.head_id`를 조인해야 함. "직급"과 "부서"는 서로 다른 컬럼(position vs dept_id)이므로 혼동하지 않을 것.

## 3. clients (고객사) — 30행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 고객사 ID | |
| name | VARCHAR(100) | 고객사명 | Client-A ~ Client-O 등 |
| industry | VARCHAR(50) | 업종 | 제조업, 금융, IT/SW, 유통/물류, 건설, 의료/바이오, 교육, 에너지, 공공기관, 미디어 |
| region | VARCHAR(30) | 지역 | 서울, 경기, 인천, 대전, 대구, 부산, 광주, 제주 |
| company_size | VARCHAR(20) | 규모 | startup, mid, enterprise |
| contact_name | VARCHAR(50) | 담당자명 | |
| contact_email | VARCHAR(100) | 담당자 이메일 | |
| registered_at | DATE | 등록일 | |
| is_active | BOOLEAN | 활성 여부 | 기본 TRUE |

## 4. products (제품/솔루션) — 12행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 제품 ID | |
| name | VARCHAR(100) | 제품명 | Product-C1~C4(cloud), Product-S1~S3(security), Product-D1~D3(data), Product-T1~T2(consulting) |
| category | VARCHAR(50) | 카테고리 | cloud, security, data, consulting |
| description | TEXT | 설명 | |
| price_monthly | INTEGER | 월 가격 | |
| version | VARCHAR(20) | 버전 | 예: 2.3.7 |
| release_date | DATE | 출시일 | |
| status | VARCHAR(20) | 상태 | active, beta |

**주의**: "보안 솔루션"이라는 표현은 `category = 'security'`로 매핑. "카테고리"와 "제품명 접두어(C/S/D/T)"가 대응됨.

## 5. contracts (계약) — 65행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 계약 ID | |
| client_id | INTEGER FK→clients.id | 고객사 | |
| product_id | INTEGER FK→products.id | 제품 | |
| manager_id | INTEGER FK→employees.id | 담당 영업/매니저 | |
| contract_type | VARCHAR(20) | 계약 유형 | subscription, project, maintenance |
| amount | INTEGER | 계약 금액 | |
| start_date | DATE | 시작일 | |
| end_date | DATE | 종료일 | nullable |
| status | VARCHAR(20) | 상태 | active, completed, cancelled |

## 6. projects (프로젝트) — 40행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 프로젝트 ID | |
| name | VARCHAR(200) | 프로젝트명 | |
| client_id | INTEGER FK→clients.id | 고객사 | |
| manager_id | INTEGER FK→employees.id | 담당자 | |
| contract_id | INTEGER FK→contracts.id | 연결 계약 | nullable |
| status | VARCHAR(20) | 상태 | planning, in_progress, on_hold, completed |
| start_date | DATE | 시작일 | |
| end_date | DATE | 종료일 | nullable |
| budget | INTEGER | 예산 | |
| description | TEXT | 설명 | |

## 7. sales (매출) — 500행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 매출 ID | |
| contract_id | INTEGER FK→contracts.id | 연결 계약 | |
| client_id | INTEGER FK→clients.id | 고객사 | |
| product_id | INTEGER FK→products.id | 제품 | |
| amount | INTEGER | 매출액 | |
| sale_date | DATE | 매출일 | |
| quarter | VARCHAR(10) | 분기 | '2024-Q1' ~ '2026-Q2' 형식 |
| category | VARCHAR(50) | 카테고리(제품과 동일 체계) | cloud, security, data, consulting |
| region | VARCHAR(30) | 지역 | clients.region과 동일 값 체계 |

**주의**: "2025년 3분기"는 `quarter = '2025-Q3'`로 매핑. 분기 컬럼이 이미 있으므로 `EXTRACT`로 재계산할 필요 없음.

## 8. support_tickets (기술 지원 티켓) — 120행

| 컬럼 | 타입 | 의미 | 예시 값 |
|---|---|---|---|
| id | SERIAL PK | 티켓 ID | |
| client_id | INTEGER FK→clients.id | 고객사 | |
| product_id | INTEGER FK→products.id | 제품 | |
| assignee_id | INTEGER FK→employees.id | 담당자 | nullable |
| title | VARCHAR(200) | 제목 | |
| description | TEXT | 설명 | |
| priority | VARCHAR(10) | 우선순위 | low, medium, high, critical |
| status | VARCHAR(20) | 상태 | open, in_progress, resolved, closed |
| created_at | TIMESTAMP | 생성일시 | |
| resolved_at | TIMESTAMP | 해결일시 | nullable |

**주의**: "아직 해결되지 않은"은 `status IN ('open', 'in_progress')`로 매핑 (resolved/closed 제외).

## 9. document_chunks (벡터 검색용, NL2SQL 대상 아님)

문서 임베딩 저장 테이블. NL2SQL 질의 대상에서 제외 — 비정형 문서 검색은 벡터 검색 도구가 담당.

---

## 자주 틀리는 포인트 체크리스트

- [ ] "보안", "클라우드" 등 한글 카테고리 표현 → `category` 컬럼의 영문 값(security/cloud/data/consulting)으로 정확히 매핑했는가
- [ ] "지역"(서울/경기 등) 질문 시 `clients.region`인지 `sales.region`인지 질문 맥락에 맞게 선택했는가
- [ ] 매출 집계는 `sales` 테이블, 계약 금액 집계는 `contracts` 테이블 — 혼동하지 않았는가
- [ ] 날짜 범위는 `BETWEEN` 또는 `>=`/`<`로, 분기는 `quarter` 컬럼 값으로 직접 필터링했는가
- [ ] 정렬/상위 N개 질문에 `ORDER BY ... DESC LIMIT N`이 빠지지 않았는가
