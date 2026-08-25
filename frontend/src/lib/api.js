// 실제 백엔드(HTTP 브릿지) 호출 + 응답 어댑터.
//
// 브릿지 서버(bridge/server.py)는 docs/frontend_requirements.md의 계약
// { answer, raw_data, tool, source } 를 반환한다. 이 파일은 그 응답을
// 화면 컴포넌트(AnswerMessage 등)가 기대하는 렌더링 형태로 변환한다.
//
// 브릿지 주소는 VITE_BRIDGE_URL 환경변수로 바꿀 수 있고, 기본값은 로컬 8000.

const BRIDGE_URL = import.meta.env.VITE_BRIDGE_URL || 'http://127.0.0.1:8000'

const TYPE_LABEL = {
  incident_report: 'incident_report',
  technical_doc: 'technical_doc',
  meeting_note: 'meeting_note',
  proposal: 'proposal',
}

// 백엔드 응답(res) -> AnswerMessage가 읽는 형태로 변환.
function adapt(res, forced) {
  const tool = res.tool || res.routed_to || 'nl2sql'
  const base = {
    tool,
    answer: res.answer,
    forced,
    // 자동 라우팅이고 규칙이 기권해 LLM 폴백이 결정한 경우에만 폴백 라벨을 표시한다.
    fallbackRoute: !forced && res.route_tier === 'llm_fallback',
  }

  // 사전 거부 / 최상위 예외 — raw_data null, 부가 필드 없음
  if (res.raw_data == null && !res.sql && !res.spec) {
    return { ...base, error: true, tool: null,
      refusal: '사전 거부 또는 내부 오류 — 도구 실행 결과가 없습니다. 부가 필드가 응답에 없습니다.' }
  }

  if (tool === 'nl2sql') {
    const rd = res.raw_data || {}
    const table = {
      columns: rd.columns || [],
      rows: rd.rows || [],
      total_count: rd.total_count,
      truncated: !!rd.truncated,
    }
    const noInfo = (rd.rows || []).length === 0 && (res.source || []).length === 0
    return { ...base, sql: res.sql, table, noInfo }
  }

  if (tool === 'knowledge_graph') {
    const rd = res.raw_data || {}
    if (rd.error) {
      return { ...base, spec: res.spec, nodeError: rd.error }
    }
    const nodes = (rd.nodes || []).map((n) => ({
      id: n.id,
      type: n.type,
      name: n.name,
      position: n.position,
      dept: n.dept,
      category: n.category,
      price: n.price,
      count: n.count,
      // GraphView가 그 밖의 속성을 attrs로 뭉쳐 보여주므로 원본도 넘긴다.
      attrs: n,
    }))
    return { ...base, spec: res.spec, nodes }
  }

  // vector_search: raw_data는 청크 배열. source(doc_id 배열)에 있으면 evidence.
  const srcSet = new Set(res.source || [])
  const chunks = (res.raw_data || []).map((c) => ({
    doc_id: c.doc_id,
    chunk_index: c.chunk_index,
    content: c.content,
    title: (c.metadata && c.metadata.title) || c.doc_id,
    type: (c.metadata && c.metadata.type) || 'technical_doc',
    similarity: c.similarity,
    rerank_score: c.rerank_score != null ? c.rerank_score : c.similarity,
    evidence: srcSet.has(c.doc_id),
  }))
  const noInfo = (res.source || []).length === 0
  return { ...base, chunks, noInfo }
}

// 질문을 백엔드로 보내고 어댑터를 거친 렌더링 객체를 반환한다.
// forcedTool: null이면 /ask(자동 라우팅), 아니면 해당 도구 직접 호출.
export async function askBackend(question, forcedTool) {
  const t0 = performance.now()
  const url = forcedTool ? `${BRIDGE_URL}/tool/${forcedTool}` : `${BRIDGE_URL}/ask`
  let res
  try {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
    res = await r.json()
  } catch (e) {
    // 브릿지 미기동 등 네트워크 오류
    return {
      tool: null, error: true, forced: !!forcedTool,
      answer: '백엔드 브릿지 서버에 연결하지 못했습니다. bridge/server.py가 실행 중인지 확인해 주세요.',
      refusal: `연결 오류: ${e.message}`,
      elapsed: ((performance.now() - t0) / 1000).toFixed(1),
    }
  }
  const adapted = adapt(res, !!forcedTool)
  adapted.elapsed = ((performance.now() - t0) / 1000).toFixed(1)
  return adapted
}

export { TYPE_LABEL }
