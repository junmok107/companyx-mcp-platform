import { SCENARIOS, FALLBACK } from '../data/scenarios'

const SQL_WORDS = ['매출', '계약', '연봉', '직원 목록', '티켓', '개수', '몇 개', '평균', '합계', '금액', '등록']
const KG_WORDS = ['담당', '소속', '사용', '관련', '팀장', '이끄', '누구', '고객사는']

// Picks a canned scenario for a question, optionally constrained to a
// specific tool (used when the user bypasses `ask` and calls a tool
// directly). Falls through to a generic "no result" / "not found" shape
// per tool when nothing matches, mirroring how the real router always
// resolves to *some* tool.
export function pick(question, forcedTool) {
  const low = question.toLowerCase()
  for (const s of SCENARIOS) {
    if (s.match.some((k) => low.indexOf(k) !== -1) && (!forcedTool || s.tool === forcedTool)) return s
  }

  let tool = forcedTool
  if (!tool) {
    if (SQL_WORDS.some((k) => low.indexOf(k) !== -1)) tool = 'nl2sql'
    else if (KG_WORDS.some((k) => low.indexOf(k) !== -1)) tool = 'knowledge_graph'
    else tool = 'vector_search'
  }

  if (tool === 'nl2sql') {
    return {
      tool: 'nl2sql', latency: 2400, fallbackRoute: !forcedTool, noInfo: true,
      answer: '조회된 결과가 없습니다.',
      sql: '-- 질문을 SQL로 변환해 실행했지만 조건에 맞는 행이 없습니다\nSELECT *\nFROM sales\nWHERE 1 = 0;',
      table: { columns: ['(결과 없음)'], rows: [], total_count: 0, truncated: false },
    }
  }
  if (tool === 'knowledge_graph') {
    const ent = question.replace(/[?!.]/g, '').split(/\s+/)[0]
    return {
      tool: 'knowledge_graph', latency: 2000, fallbackRoute: !forcedTool,
      answer: `'${ent}'를 그래프에서 찾을 수 없습니다.`,
      spec: { mode: 'traverse', entity: ent, hops: [] },
      nodeError: `'${ent}'에 해당하는 개체가 그래프에 없습니다. 지원하는 개체는 고객사(Client-X), 제품(Product-X), 직원, 부서, 프로젝트입니다.`,
    }
  }
  return Object.assign({}, FALLBACK, { fallbackRoute: !forcedTool })
}
