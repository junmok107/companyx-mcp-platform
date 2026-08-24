// Mock response data for the console demo.
//
// The real backend is an MCP server exposed over stdio only (see
// mcp_server/server.py) — it cannot be called directly from a browser.
// This mirrors the shapes documented in docs/frontend_requirements.md
// (answer / raw_data / tool / source, per-tool extras, null-vs-filled
// raw_data rules) using canned scenarios instead of live calls.

export const TOOLS = {
  nl2sql: { label: 'NL2SQL', ko: '정형 데이터' },
  knowledge_graph: { label: '지식 그래프', ko: '관계' },
  vector_search: { label: '벡터 검색', ko: '문서' },
}

export const EXAMPLES = {
  nl2sql: [
    '서울 지역 매출 상위 5개 고객사를 알려줘',
    '2025년 3분기 총 매출액은 얼마야?',
    '보안 솔루션 카테고리 제품들의 월 평균 매출은?',
    '현재 활성 상태인 계약 수는 몇 개야?',
    '기술지원팀 직원 목록과 연봉을 알려줘',
    '가장 많은 프로젝트를 진행 중인 고객사는?',
    'Critical 우선순위 티켓 중 아직 해결되지 않은 건은?',
    '제품별 총 계약 금액을 큰 순서로 보여줘',
    '2024년에 등록된 고객사는 몇 개야?',
    '평균 연봉이 가장 높은 부서는 어디야?',
  ],
  vector_search: [
    '최근 서버 장애 사례와 원인을 알려줘',
    'Product-C1 설치 방법이 궁금해',
    'Kubernetes 관련 장애 대응 방법은?',
    '성능 최적화를 위한 DB 튜닝 방법 알려줘',
    '보안 취약점 점검 관련 내용이 있어?',
    '백업 정책은 어떻게 되어 있어?',
    'API 인증 방식은 뭐야?',
    '고객사 미팅에서 논의된 일정 지연 이슈는?',
    '클라우드 마이그레이션 제안서 내용 보여줘',
    'SSL 인증서 관련 장애가 있었어?',
  ],
  knowledge_graph: [
    'Client-A가 사용 중인 제품 목록은?',
    'Product-C1을 사용하는 고객사는 어디야?',
    '클라우드사업부 소속 직원들은 누구야?',
    '서울물산 담당 엔지니어는 누구야?',
    'Product-D1 제품과 관련된 프로젝트는?',
    '기술 지원 이슈가 가장 많은 제품은?',
    '경영지원팀 팀장은 누구야?',
    '진행 중인 프로젝트를 이끄는 직원 목록',
    'Product-S1 관련 고객 이슈 현황은?',
    '가장 많은 고객을 담당하는 직원은?',
  ],
}

export const TYPE_KO = {
  incident_report: '장애보고서',
  technical_doc: '기술문서',
  meeting_note: '회의록',
  proposal: '제안서',
}

export const NODE_TYPE_KO = {
  employee: '직원',
  client: '고객사',
  product: '제품',
  project: '프로젝트',
  dept: '부서',
}

const CLIENTS = ['Client-Q', 'Client-Y', 'Client-I', 'Client-A', 'Client-E', 'Client-B', 'Client-T', 'Client-V', 'Client-D', 'Client-H', 'Client-AA', 'Client-O']
const QUARTERS = ['2024-Q1', '2024-Q3', '2025-Q1', '2025-Q2', '2025-Q3', '2026-Q1', '2026-Q2']

function bigRows() {
  const out = []
  for (let i = 0; i < 200; i++) {
    const id = 812 - i
    out.push([id, CLIENTS[(i * 7) % CLIENTS.length], 'Product-' + ['C1', 'C3', 'S1', 'S2', 'D1', 'D3', 'T2'][(i * 5) % 7], 380 + ((i * 137) % 4200), QUARTERS[(i * 3) % QUARTERS.length]])
  }
  return out
}

function tbl(columns, rows, opts) {
  return Object.assign({ columns, rows, total_count: rows.length, truncated: false }, opts || {})
}

function kgNodes(type, list) {
  return list.map((n) => ({ id: n[0], type, name: n[1], attrs: n[2], meta: n[2] }))
}

const KG_EMPLOYEES = [
  ['employee_3', '김도윤', '사원'], ['employee_7', '안진우', '이사'], ['employee_11', '조동현', '차장'], ['employee_14', '이지훈', '차장'], ['employee_19', '황다은', '사원'],
  ['employee_22', '한은지', '사원'], ['employee_28', '황재원', '사원'], ['employee_31', '김준혁', '차장'], ['employee_36', '강현우', '사원'], ['employee_41', '서재원', '과장'],
]

export const SCENARIOS = [
  {
    match: ['critical', '티켓'],
    tool: 'nl2sql', latency: 2100,
    answer: '총 5건:\n- id=37, title=프로덕션 핫픽스 요청, status=in_progress, created_at=2026-03-20 16:08:23\n- id=62, title=SSL 인증서 만료 알림, status=in_progress, created_at=2025-05-06 17:23:07\n- id=64, title=디스크 용량 부족 경고, status=open, created_at=2025-04-15 11:32:44\n- id=66, title=ETL 작업 실패, status=in_progress, created_at=2026-05-31 08:06:13\n- id=80, title=로그 수집 중단, status=in_progress, created_at=2025-06-11 09:39:12',
    sql: "SELECT id, title, status, created_at\nFROM support_tickets\nWHERE priority = 'critical'\n  AND status IN ('open', 'in_progress')\nORDER BY created_at DESC;",
    table: {
      columns: ['id', 'title', 'status', 'created_at'],
      rows: [[37, '프로덕션 핫픽스 요청', 'in_progress', '2026-03-20 16:08:23'], [62, 'SSL 인증서 만료 알림', 'in_progress', '2025-05-06 17:23:07'], [64, '디스크 용량 부족 경고', 'open', '2025-04-15 11:32:44'], [66, 'ETL 작업 실패', 'in_progress', '2026-05-31 08:06:13'], [80, '로그 수집 중단', 'in_progress', '2025-06-11 09:39:12']],
      total_count: 5, truncated: false,
    },
  },
  {
    match: ['평균 연봉'],
    tool: 'nl2sql', latency: 2900,
    answer: '평균 연봉이 가장 높은 부서는 기술지원팀입니다.',
    note: '단일값이라 답변 문장 생성에 LLM 호출 1회가 추가됩니다 (실측 약 9초).',
    sql: 'SELECT d.name, AVG(e.salary) AS avg_salary\nFROM employees e JOIN departments d ON d.id = e.dept_id\nGROUP BY d.name\nORDER BY avg_salary DESC\nLIMIT 1;',
    table: { columns: ['name', 'avg_salary'], rows: [['기술지원팀', 6752.25]], total_count: 1, truncated: false },
  },
  {
    match: ['전체 매출', '매출 내역'],
    tool: 'nl2sql', latency: 2400,
    answer: '총 200건:\n- id=812, client=Client-Q, amount=380\n- id=811, client=Client-I, amount=517\n- id=810, client=Client-E, amount=654\n… 외 150건 (답변은 최대 50건까지만 나열합니다)',
    sql: 'SELECT s.id, c.name AS client, s.product_id, s.amount, s.quarter\nFROM sales s JOIN clients c ON c.id = s.client_id\nORDER BY s.id DESC\nLIMIT 200;',
    table: { columns: ['id', 'client', 'product_id', 'amount', 'quarter'], rows: bigRows(), total_count: null, truncated: true },
  },
  {
    match: ['클라우드사업부'],
    tool: 'knowledge_graph', latency: 2000,
    answer: '총 10건:\n- 김도윤 (position=사원, dept=클라우드사업부)\n- 안진우 (position=이사, dept=클라우드사업부)\n- 조동현 (position=차장, dept=클라우드사업부)\n- 이지훈 (position=차장, dept=클라우드사업부)\n- 황다은 (position=사원, dept=클라우드사업부)\n- 한은지 (position=사원, dept=클라우드사업부)\n- 황재원 (position=사원, dept=클라우드사업부)\n- 김준혁 (position=차장, dept=클라우드사업부)\n- 강현우 (position=사원, dept=클라우드사업부)\n- 서재원 (position=과장, dept=클라우드사업부)',
    spec: { mode: 'traverse', entity: '클라우드사업부', hops: [{ relation: 'BELONGS_TO', direction: 'incoming' }] },
    graph: { entity: '클라우드사업부', relation: 'BELONGS_TO', direction: 'incoming (직원 → 부서)' },
    nodes: KG_EMPLOYEES.map((e) => ({ id: e[0], type: 'employee', name: e[1], position: e[2], dept: '클라우드사업부' })),
  },
  {
    match: ['서울물산'],
    tool: 'knowledge_graph', latency: 1500,
    answer: "'서울물산'를 그래프에서 찾을 수 없습니다.",
    spec: { mode: 'traverse', entity: '서울물산', hops: [{ relation: 'MANAGES_ACCOUNT', direction: 'outgoing' }, { relation: 'BELONGS_TO', direction: 'incoming' }] },
    nodeError: "'서울물산'에 해당하는 개체가 그래프에 없습니다. 고객사명은 모두 Client-X 형식으로 저장되어 있습니다.",
  },
  {
    match: ['db 튜닝', '성능 최적화'],
    tool: 'vector_search', latency: 2600,
    answer: '- Connection Pool: 최소 14, 최대 52\n- 인덱스 점검: 슬로우 쿼리 로그 기반으로 월 1회 점검\n- 쿼리 캐싱: Redis에 TTL 200초 설정',
    chunks: [
      { doc_id: 'DOC-014', chunk_index: 0, title: '성능 튜닝 가이드', type: 'technical_doc', content: 'Connection Pool은 최소 14, 최대 52로 설정한다. 슬로우 쿼리 로그를 기반으로 월 1회 인덱스를 점검한다.', similarity: 0.82, rerank_score: 0.91, evidence: true },
      { doc_id: 'DOC-019', chunk_index: 1, title: 'DB 운영 매뉴얼', type: 'technical_doc', content: '쿼리 캐싱은 Redis에 TTL 200초로 설정한다. 캐시 적중률은 주간 리포트로 확인한다.', similarity: 0.79, rerank_score: 0.88, evidence: true },
      { doc_id: 'DOC-030', chunk_index: 0, title: '인프라 점검 회의록', type: 'meeting_note', content: 'DB 응답 지연 개선안으로 인덱스 재구성과 커넥션 풀 상향이 논의되었다.', similarity: 0.74, rerank_score: 0.8, evidence: true },
      { doc_id: 'DOC-022', chunk_index: 2, title: '월간 운영 회의록', type: 'meeting_note', content: '월간 지표 검토와 함께 스토리지 증설 계획을 공유했다.', similarity: 0.71, rerank_score: 0.52, evidence: false },
      { doc_id: 'DOC-007', chunk_index: 0, title: '장애 보고서 — 배치 지연', type: 'incident_report', content: '야간 배치가 지연되어 리포트 생성이 늦어졌다. 원인은 잠금 경합이었다.', similarity: 0.69, rerank_score: 0.41, evidence: false },
    ],
  },
  {
    match: ['kubernetes', 'k8s', '쿠버네티스'],
    tool: 'vector_search', latency: 2500,
    answer: '관련 문서를 찾지 못했습니다.',
    noInfo: true,
    chunks: [
      { doc_id: 'DOC-003', chunk_index: 0, title: '장애 보고서 — 컨테이너 재시작', type: 'incident_report', content: '컨테이너가 반복 재시작되어 서비스가 간헐적으로 중단되었다. 리소스 제한을 상향했다.', similarity: 0.72, rerank_score: 0.44, evidence: false },
      { doc_id: 'DOC-005', chunk_index: 1, title: '장애 보고서 — 리소스 부족', type: 'incident_report', content: '트래픽 증가로 리소스가 부족했고 모니터링 임계값이 낮게 설정되어 있었다.', similarity: 0.7, rerank_score: 0.39, evidence: false },
      { doc_id: 'DOC-011', chunk_index: 0, title: 'Product-C1 설치 가이드', type: 'technical_doc', content: '의존성 설치 → 설정 파일 준비 → 서비스 시작 → 헬스체크 순으로 진행한다.', similarity: 0.66, rerank_score: 0.28, evidence: false },
    ],
  },
  {
    match: ['보안 취약점'],
    tool: 'vector_search', latency: 2600,
    answer: '- [DOC-021] 회의록에서 보안 취약점 점검 결과 7건의 개선 사항이 도출되었다고 나와 있습니다.\n- [DOC-028] 회의록에서 보안 취약점 점검 결과 6건의 개선 사항이 도출되었다고 나와 있습니다.\n- [DOC-024] 회의록에서 보안 취약점 점검 결과 4건의 개선 사항이 도출되었다고 나와 있습니다.',
    chunks: [
      { doc_id: 'DOC-021', chunk_index: 0, title: '주간 운영 회의록', type: 'meeting_note', content: '보안 취약점 점검 결과 7건의 개선 사항이 도출되었다. 담당자는 다음 주까지 우선순위를 정리한다.', similarity: 0.84, rerank_score: 0.88, evidence: true },
      { doc_id: 'DOC-028', chunk_index: 1, title: '보안 점검 회의록', type: 'meeting_note', content: '보안 취약점 점검 결과 6건의 개선 사항이 도출되었다. 조치 완료 기한은 이달 말이다.', similarity: 0.81, rerank_score: 0.81, evidence: true },
      { doc_id: 'DOC-024', chunk_index: 0, title: '분기 보안 회의록', type: 'meeting_note', content: '보안 취약점 점검 결과 4건의 개선 사항이 도출되었다.', similarity: 0.78, rerank_score: 0.76, evidence: true },
      { doc_id: 'DOC-013', chunk_index: 2, title: '접근 제어 기술 문서', type: 'technical_doc', content: '권한은 역할 기반으로 부여하며 분기마다 재검토한다.', similarity: 0.69, rerank_score: 0.33, evidence: false },
    ],
  },
  {
    match: ['client-a'],
    tool: 'knowledge_graph', latency: 1900,
    answer: '총 2건:\n- Product-S1 (category=security, price=280)\n- Product-C3 (category=cloud, price=120)',
    spec: { mode: 'traverse', entity: 'Client-A', hops: [{ relation: 'USES', direction: 'outgoing' }] },
    graph: { entity: 'Client-A', relation: 'USES', direction: 'outgoing (고객사 → 제품)' },
    nodes: [
      { id: 'product_3', type: 'product', name: 'Product-S1', category: 'security', price: 280 },
      { id: 'product_8', type: 'product', name: 'Product-C3', category: 'cloud', price: 120 },
    ],
  },
  { match: ['서울 지역', '매출 상위'], tool: 'nl2sql', latency: 2100,
    answer: '총 4건:\n- name=Client-Q, total_sales=23244\n- name=Client-Y, total_sales=22865\n- name=Client-I, total_sales=10898\n- name=Client-A, total_sales=10707',
    sql: "SELECT c.name, SUM(s.amount) AS total_sales\nFROM sales s JOIN clients c ON c.id = s.client_id\nWHERE c.region = '서울'\nGROUP BY c.name\nORDER BY total_sales DESC\nLIMIT 5;",
    table: tbl(['name', 'total_sales'], [['Client-Q', 23244], ['Client-Y', 22865], ['Client-I', 10898], ['Client-A', 10707]]) },
  { match: ['3분기 총 매출'], tool: 'nl2sql', latency: 2900,
    answer: '2025년 3분기 총 매출액은 23,859 입니다.',
    sql: "SELECT SUM(amount) AS total\nFROM sales\nWHERE quarter = '2025-Q3';",
    table: tbl(['total'], [[23859]]) },
  { match: ['월 평균 매출'], tool: 'nl2sql', latency: 2900,
    answer: '보안 솔루션 카테고리 제품들의 월 평균 매출은 589.97원입니다.',
    sql: "SELECT AVG(s.amount) AS avg_amount\nFROM sales s JOIN products p ON p.id = s.product_id\nWHERE p.category = 'security';",
    table: tbl(['avg_amount'], [[589.97]]) },
  { match: ['활성 상태', '계약 수'], tool: 'nl2sql', latency: 2800,
    answer: '현재 활성 상태인 계약은 46개입니다.',
    sql: "SELECT COUNT(*) AS active_contracts\nFROM contracts\nWHERE status = 'active';",
    table: tbl(['active_contracts'], [[46]]) },
  { match: ['기술지원팀'], tool: 'nl2sql', latency: 2000,
    answer: '총 4건:\n- name=박소연, salary=9520\n- name=권승호, salary=5378\n- name=조예진, salary=5019\n- name=임우진, salary=7092',
    sql: "SELECT e.name, e.salary\nFROM employees e JOIN departments d ON d.id = e.dept_id\nWHERE d.name = '기술지원팀';",
    table: tbl(['name', 'salary'], [['박소연', 9520], ['권승호', 5378], ['조예진', 5019], ['임우진', 7092]]) },
  { match: ['많은 프로젝트'], tool: 'nl2sql', latency: 2100,
    answer: '총 2건:\n- Client-AC\n- Client-E',
    sql: 'SELECT c.name, COUNT(*) AS project_count\nFROM projects p JOIN clients c ON c.id = p.client_id\nGROUP BY c.name\nORDER BY project_count DESC\nLIMIT 2;',
    table: tbl(['name', 'project_count'], [['Client-AC', 5], ['Client-E', 5]]) },
  { match: ['제품별', '계약 금액'], tool: 'nl2sql', latency: 2200,
    answer: '총 12건:\n- name=Product-D3, total_contract_amount=36500\n- name=Product-C1, total_contract_amount=34300\n- name=Product-S1, total_contract_amount=30800\n- name=Product-D1, total_contract_amount=25200\n- name=Product-S2, total_contract_amount=24000\n- name=Product-S3, total_contract_amount=15360\n- name=Product-C4, total_contract_amount=15000\n- name=Product-C2, total_contract_amount=11700\n- name=Product-D2, total_contract_amount=10800\n- name=Product-C3, total_contract_amount=8400\n- name=Product-T2, total_contract_amount=3800\n- name=Product-T1, total_contract_amount=2720',
    sql: 'SELECT p.name, SUM(ct.amount) AS total_contract_amount\nFROM contracts ct JOIN products p ON p.id = ct.product_id\nGROUP BY p.name\nORDER BY total_contract_amount DESC;',
    table: tbl(['name', 'total_contract_amount'], [['Product-D3', 36500], ['Product-C1', 34300], ['Product-S1', 30800], ['Product-D1', 25200], ['Product-S2', 24000], ['Product-S3', 15360], ['Product-C4', 15000], ['Product-C2', 11700], ['Product-D2', 10800], ['Product-C3', 8400], ['Product-T2', 3800], ['Product-T1', 2720]]) },
  { match: ['2024년에 등록'], tool: 'nl2sql', latency: 2800,
    answer: '2024년에 등록된 고객사는 8개입니다.',
    sql: "SELECT COUNT(*) AS client_count\nFROM clients\nWHERE registered_at BETWEEN '2024-01-01' AND '2024-12-31';",
    table: tbl(['client_count'], [[8]]) },

  { match: ['사용하는 고객사'], tool: 'knowledge_graph', latency: 2000,
    answer: '총 6건:\n- Client-Q (industry=미디어, region=서울, size=mid)\n- Client-T (industry=공공기관, region=대전, size=mid)\n- Client-V (industry=금융, region=인천, size=startup)\n- Client-Y (industry=의료/바이오, region=서울, size=startup)\n- Client-D (industry=유통/물류, region=대전, size=startup)\n- Client-H (industry=에너지, region=제주, size=mid)',
    spec: { mode: 'traverse', entity: 'Product-C1', hops: [{ relation: 'USES', direction: 'incoming' }] },
    graph: { entity: 'Product-C1', relation: 'USES', direction: 'incoming (고객사 → 제품)' },
    nodes: kgNodes('client', [['client_17', 'Client-Q', 'industry=미디어 · region=서울 · size=mid'], ['client_20', 'Client-T', 'industry=공공기관 · region=대전 · size=mid'], ['client_22', 'Client-V', 'industry=금융 · region=인천 · size=startup'], ['client_25', 'Client-Y', 'industry=의료/바이오 · region=서울 · size=startup'], ['client_4', 'Client-D', 'industry=유통/물류 · region=대전 · size=startup'], ['client_8', 'Client-H', 'industry=에너지 · region=제주 · size=mid']]) },
  { match: ['product-d1'], tool: 'knowledge_graph', latency: 2200,
    answer: '총 6건:\n- Client-B CI/CD 파이프라인 구축 (status=planning, budget=11832)\n- Client-B CI/CD 파이프라인 구축 (status=planning, budget=9267)\n- Client-Y 데이터 거버넌스 (status=on_hold, budget=3128)\n- Client-B 하이브리드 클라우드 (status=planning, budget=8616)\n- Client-Q AI 예측 모델 구축 (status=on_hold, budget=4922)\n- Client-AB DevOps 전환 (status=completed, budget=6512)',
    spec: { mode: 'traverse', entity: 'Product-D1', hops: [{ relation: 'USES', direction: 'incoming' }, { relation: 'HAS_PROJECT', direction: 'outgoing' }] },
    graph: { entity: 'Product-D1', relation: 'USES ∘ HAS_PROJECT', direction: '2홉 (제품 ← 고객사 → 프로젝트)' },
    nodes: kgNodes('project', [['project_12', 'Client-B CI/CD 파이프라인 구축', 'status=planning · budget=11832'], ['project_31', 'Client-B CI/CD 파이프라인 구축', 'status=planning · budget=9267'], ['project_44', 'Client-Y 데이터 거버넌스', 'status=on_hold · budget=3128'], ['project_19', 'Client-B 하이브리드 클라우드', 'status=planning · budget=8616'], ['project_27', 'Client-Q AI 예측 모델 구축', 'status=on_hold · budget=4922'], ['project_38', 'Client-AB DevOps 전환', 'status=completed · budget=6512']]) },
  { match: ['이슈가 가장 많은'], tool: 'knowledge_graph', latency: 2900,
    answer: '기술 지원 이슈가 가장 많은 제품은 Product-T2입니다.',
    spec: { mode: 'aggregate', relation: 'REPORTED_ISSUE', group_by: 'target', order: 'desc', limit: 1 },
    graph: { entity: 'REPORTED_ISSUE', relation: '집계 (group_by=target)', direction: '상위 1건' },
    nodes: kgNodes('product', [['product_12', 'Product-T2', 'count=9 · category=tool']]) },
  { match: ['경영지원팀'], tool: 'knowledge_graph', latency: 2900,
    answer: '경영지원팀 팀장은 윤소연입니다.',
    spec: { mode: 'traverse', entity: '경영지원팀', hops: [{ relation: 'HEAD_IS', direction: 'outgoing' }] },
    graph: { entity: '경영지원팀', relation: 'HEAD_IS', direction: 'outgoing (부서 → 직원)' },
    nodes: kgNodes('employee', [['employee_2', '윤소연', 'position=부장 · dept=경영지원팀']]) },
  { match: ['이끄는'], tool: 'knowledge_graph', latency: 2300,
    answer: '총 11건:\n- 권소연 (position=과장, dept=보안솔루션팀)\n- 한태호 (position=차장, dept=보안솔루션팀)\n- 류서연 (position=차장, dept=데이터플랫폼팀)\n- 안진우 (position=이사, dept=클라우드사업부)\n- 조동현 (position=차장, dept=클라우드사업부)\n- 조재원 (position=이사, dept=보안솔루션팀)\n- 박성민 (position=차장, dept=보안솔루션팀)\n- 장미라 (position=과장, dept=보안솔루션팀)\n- 김준혁 (position=차장, dept=클라우드사업부)\n- 강현우 (position=사원, dept=클라우드사업부)\n- 서재원 (position=과장, dept=클라우드사업부)',
    spec: { mode: 'filtered_traverse', node_type: 'project', filter: { status: 'in_progress' }, hops: [{ relation: 'LEADS', direction: 'incoming' }] },
    graph: { entity: 'project(status=in_progress)', relation: 'LEADS', direction: 'incoming (직원 → 프로젝트)' },
    nodes: kgNodes('employee', [['employee_5', '권소연', 'position=과장 · dept=보안솔루션팀'], ['employee_9', '한태호', 'position=차장 · dept=보안솔루션팀'], ['employee_13', '류서연', 'position=차장 · dept=데이터플랫폼팀'], ['employee_7', '안진우', 'position=이사 · dept=클라우드사업부'], ['employee_11', '조동현', 'position=차장 · dept=클라우드사업부'], ['employee_16', '조재원', 'position=이사 · dept=보안솔루션팀'], ['employee_21', '박성민', 'position=차장 · dept=보안솔루션팀'], ['employee_26', '장미라', 'position=과장 · dept=보안솔루션팀'], ['employee_31', '김준혁', 'position=차장 · dept=클라우드사업부'], ['employee_36', '강현우', 'position=사원 · dept=클라우드사업부'], ['employee_41', '서재원', 'position=과장 · dept=클라우드사업부']]) },
  { match: ['product-s1'], tool: 'knowledge_graph', latency: 2200,
    answer: '총 8건:\n- Client-J (industry=공공기관, region=경기, size=startup)\n- Client-O (industry=의료/바이오, region=광주, size=enterprise)\n- Client-S (industry=건설, region=부산, size=startup)\n- Client-V (industry=금융, region=인천, size=startup)\n- Client-X (industry=유통/물류, region=제주, size=enterprise)\n- Client-AA (industry=미디어, region=부산, size=enterprise)\n- Client-D (industry=유통/물류, region=대전, size=startup)\n- Client-E (industry=의료/바이오, region=대구, size=mid)',
    spec: { mode: 'traverse', entity: 'Product-S1', hops: [{ relation: 'REPORTED_ISSUE', direction: 'incoming' }] },
    graph: { entity: 'Product-S1', relation: 'REPORTED_ISSUE', direction: 'incoming (고객사 → 제품)' },
    nodes: kgNodes('client', [['client_10', 'Client-J', 'industry=공공기관 · region=경기'], ['client_15', 'Client-O', 'industry=의료/바이오 · region=광주'], ['client_19', 'Client-S', 'industry=건설 · region=부산'], ['client_22', 'Client-V', 'industry=금융 · region=인천'], ['client_24', 'Client-X', 'industry=유통/물류 · region=제주'], ['client_27', 'Client-AA', 'industry=미디어 · region=부산'], ['client_4', 'Client-D', 'industry=유통/물류 · region=대전'], ['client_5', 'Client-E', 'industry=의료/바이오 · region=대구']]) },
  { match: ['많은 고객을 담당'], tool: 'knowledge_graph', latency: 2300,
    answer: '총 3건:\n- 안소연 (position=차장, dept=데이터플랫폼팀, count=4)\n- 조현우 (position=차장, dept=데이터플랫폼팀, count=4)\n- 김준혁 (position=차장, dept=클라우드사업부, count=4)',
    spec: { mode: 'aggregate', relation: 'MANAGES_ACCOUNT', group_by: 'source', order: 'desc', limit: 3 },
    graph: { entity: 'MANAGES_ACCOUNT', relation: '집계 (group_by=source)', direction: '상위 3건' },
    nodes: kgNodes('employee', [['employee_18', '안소연', 'position=차장 · dept=데이터플랫폼팀 · count=4'], ['employee_23', '조현우', 'position=차장 · dept=데이터플랫폼팀 · count=4'], ['employee_31', '김준혁', 'position=차장 · dept=클라우드사업부 · count=4']]) },

  { match: ['서버 장애', '장애 사례'], tool: 'vector_search', latency: 2600,
    answer: '최근 서버 장애는 트래픽 증가에 따른 리소스 부족이 근본 원인으로, 모니터링 임계값이 적절히 설정되지 않아 사전 감지가 되지 않았습니다.',
    chunks: [
      { doc_id: 'DOC-002', chunk_index: 0, title: '장애 보고서 — 로드밸런서 헬스체크 실패', type: 'incident_report', content: 'Client-B에서 운영 중인 Product-C2 서비스에서 로드밸런서 헬스체크 실패로 트래픽 분산 장애가 발생했다.', similarity: 0.85, rerank_score: 0.92, evidence: true },
      { doc_id: 'DOC-003', chunk_index: 1, title: '장애 보고서 — 리소스 부족', type: 'incident_report', content: '최근 트래픽 증가에 따른 리소스 부족이 근본 원인이며, 모니터링 임계값이 적절히 설정되지 않아 사전 감지가 되지 않았다.', similarity: 0.82, rerank_score: 0.89, evidence: true },
      { doc_id: 'DOC-009', chunk_index: 0, title: '장애 보고서 — 야간 배치 지연', type: 'incident_report', content: '야간 배치 작업이 지연되어 리포트 생성이 늦어졌다. 조치 후 재발 방지 스크립트를 추가했다.', similarity: 0.76, rerank_score: 0.78, evidence: true },
      { doc_id: 'DOC-030', chunk_index: 2, title: '인프라 점검 회의록', type: 'meeting_note', content: '장애 대응 절차와 모니터링 알림 기준을 재정비하기로 했다.', similarity: 0.7, rerank_score: 0.38, evidence: false },
    ] },
  { match: ['설치'], tool: 'vector_search', latency: 2600,
    answer: 'Product-C1 설치 가이드 문서에 따라 설치 절차는 1단계 의존성 설치, 2단계 설정 파일 준비, 3단계 서비스 시작, 4단계 헬스체크 순으로 진행됩니다.',
    chunks: [
      { doc_id: 'DOC-011', chunk_index: 0, title: 'Product-C1 설치 가이드', type: 'technical_doc', content: '1단계 의존성 설치, 2단계 설정 파일 준비, 3단계 서비스 시작, 4단계 헬스체크 순으로 진행한다.', similarity: 0.87, rerank_score: 0.94, evidence: true },
      { doc_id: 'DOC-001', chunk_index: 1, title: 'Product-C1 운영 매뉴얼', type: 'technical_doc', content: '설치 후 헬스체크 엔드포인트로 상태를 확인하고, 실패 시 로그 경로를 점검한다.', similarity: 0.8, rerank_score: 0.85, evidence: true },
      { doc_id: 'DOC-031', chunk_index: 0, title: '제안서 — 클라우드 마이그레이션', type: 'proposal', content: 'Product-C1을 통해 대규모 클라우드 마이그레이션 플랫폼을 구축할 수 있다.', similarity: 0.72, rerank_score: 0.44, evidence: false },
    ] },
  { match: ['백업'], tool: 'vector_search', latency: 2500,
    answer: 'Product-C4는 매일 1:00 AM에 90일간 S3 호환 스토리지에 자동 백업됩니다. Product-S1은 매일 2:00 AM에 26일간 S3 호환 스토리지에 자동 백업됩니다.',
    chunks: [
      { doc_id: 'DOC-009', chunk_index: 1, title: 'Product-C4 운영 매뉴얼', type: 'technical_doc', content: '매일 1:00 AM에 자동 백업이 실행되며, 보관 기간은 90일, S3 호환 스토리지에 저장된다.', similarity: 0.84, rerank_score: 0.9, evidence: true },
      { doc_id: 'DOC-018', chunk_index: 0, title: 'Product-S1 운영 매뉴얼', type: 'technical_doc', content: '매일 2:00 AM에 자동 백업이 실행되며, 보관 기간은 26일이다.', similarity: 0.81, rerank_score: 0.87, evidence: true },
      { doc_id: 'DOC-011', chunk_index: 2, title: 'Product-C1 설치 가이드', type: 'technical_doc', content: '설정 파일에서 백업 대상 경로를 지정할 수 있다.', similarity: 0.71, rerank_score: 0.4, evidence: false },
    ] },
  { match: ['인증 방식', 'api 인증'], tool: 'vector_search', latency: 2400,
    answer: 'Bearer 토큰 방식을 사용하며, /auth/token 엔드포인트에서 발급받습니다.',
    chunks: [
      { doc_id: 'DOC-012', chunk_index: 0, title: 'API 레퍼런스 — 인증', type: 'technical_doc', content: 'Bearer 토큰 방식을 사용한다. /auth/token 엔드포인트에서 토큰을 발급받는다.', similarity: 0.88, rerank_score: 0.95, evidence: true },
      { doc_id: 'DOC-015', chunk_index: 1, title: 'API 레퍼런스 — 엔드포인트', type: 'technical_doc', content: '모든 요청 헤더에 Authorization: Bearer <token>을 포함한다.', similarity: 0.82, rerank_score: 0.86, evidence: true },
      { doc_id: 'DOC-020', chunk_index: 0, title: '접근 제어 기술 문서', type: 'technical_doc', content: '토큰 만료 시간은 기본 1시간이며 갱신 엔드포인트를 제공한다.', similarity: 0.75, rerank_score: 0.72, evidence: true },
    ] },
  { match: ['일정 지연'], tool: 'vector_search', latency: 2500,
    answer: '마일스톤 2가 13일 지연되고 있습니다. 크리티컬 패스에 영향이 있으므로 일정 재조정이 필요합니다.',
    chunks: [
      { doc_id: 'DOC-027', chunk_index: 0, title: '고객사 미팅 회의록', type: 'meeting_note', content: '마일스톤 2가 13일 지연되고 있다. 크리티컬 패스에 영향이 있어 일정 재조정이 필요하다.', similarity: 0.86, rerank_score: 0.93, evidence: true },
      { doc_id: 'DOC-029', chunk_index: 1, title: '프로젝트 주간 회의록', type: 'meeting_note', content: '지연 원인은 인력 배치 조정이며, 다음 주까지 만회 계획을 공유한다.', similarity: 0.79, rerank_score: 0.84, evidence: true },
      { doc_id: 'DOC-022', chunk_index: 0, title: '월간 운영 회의록', type: 'meeting_note', content: '월간 지표 검토와 스토리지 증설 계획을 공유했다.', similarity: 0.68, rerank_score: 0.31, evidence: false },
    ] },
  { match: ['제안서'], tool: 'vector_search', latency: 2600,
    answer: 'Product-C1을 통해 대규모 클라우드 마이그레이션 플랫폼을 구축할 수 있습니다. 멀티클라우드 지원을 제공하며, 도입 후 운영 비용 31% 절감, 장애 대응 시간 37% 단축 효과를 기대할 수 있습니다.',
    chunks: [
      { doc_id: 'DOC-031', chunk_index: 0, title: '제안서 — 클라우드 마이그레이션', type: 'proposal', content: 'Product-C1으로 대규모 클라우드 마이그레이션 플랫폼을 구축하며 멀티클라우드를 지원한다.', similarity: 0.87, rerank_score: 0.93, evidence: true },
      { doc_id: 'DOC-032', chunk_index: 1, title: '제안서 — 도입 효과', type: 'proposal', content: '도입 후 운영 비용 31% 절감, 장애 대응 시간 37% 단축 효과를 기대할 수 있다.', similarity: 0.83, rerank_score: 0.89, evidence: true },
      { doc_id: 'DOC-038', chunk_index: 0, title: '제안서 — 단계별 이행 계획', type: 'proposal', content: '3단계 이행 계획으로 평가·이행·안정화 순으로 진행한다.', similarity: 0.77, rerank_score: 0.75, evidence: true },
    ] },
  { match: ['ssl'], tool: 'vector_search', latency: 2500,
    answer: '네, SSL 인증서 만료로 인한 HTTPS 통신 실패 현상이 Client-E와 Client-F에서 발생했습니다.',
    chunks: [
      { doc_id: 'DOC-002', chunk_index: 2, title: '장애 보고서 — SSL 인증서 만료', type: 'incident_report', content: 'SSL 인증서 만료로 HTTPS 통신 실패가 발생했다. 인증서 갱신 후 정상화되었다.', similarity: 0.86, rerank_score: 0.92, evidence: true },
      { doc_id: 'DOC-005', chunk_index: 0, title: '장애 보고서 — Client-F HTTPS 실패', type: 'incident_report', content: 'Client-F 환경에서 동일한 인증서 만료 문제가 재발했다. 갱신 자동화를 등록했다.', similarity: 0.82, rerank_score: 0.88, evidence: true },
      { doc_id: 'DOC-006', chunk_index: 1, title: '장애 대응 회고', type: 'incident_report', content: '만료 30일 전 알림을 추가해 사전 감지 체계를 보완했다.', similarity: 0.74, rerank_score: 0.71, evidence: true },
    ] },
]

export const FALLBACK = {
  tool: 'vector_search', latency: 3200, fallbackRoute: true, noInfo: true,
  answer: '관련 문서를 찾지 못했습니다.',
  chunks: [
    { doc_id: 'DOC-016', chunk_index: 0, title: '운영 매뉴얼', type: 'technical_doc', content: '정기 점검 절차와 담당자 연락 체계를 정리한 문서다.', similarity: 0.64, rerank_score: 0.21, evidence: false },
    { doc_id: 'DOC-034', chunk_index: 1, title: '제안서 — 데이터 플랫폼', type: 'proposal', content: '데이터 수집·적재·분석 단계를 단일 플랫폼으로 통합하는 방안이다.', similarity: 0.61, rerank_score: 0.18, evidence: false },
  ],
}
