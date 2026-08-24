import { useState } from 'react'
import { TOOLS, TYPE_KO } from '../data/scenarios'
import RawDataTable from './RawDataTable'
import GraphView from './GraphView'
import ChunkList from './ChunkList'

function buildJson(m, tool) {
  if (m.error) {
    return { answer: m.answer, raw_data: null, tool: null, source: [] }
  }
  const source = m.table
    ? [m.sql]
    : m.nodes
      ? m.nodes.map((n) => n.id)
      : (m.chunks || []).filter((c) => c.evidence).map((c) => c.doc_id)
  const raw_data = m.table
    ? { columns: m.table.columns, rows: m.table.rows.slice(0, 3).concat([['…']]), row_count: m.table.rows.length, total_count: m.table.total_count, truncated: m.table.truncated }
    : m.nodeError
      ? { error: m.nodeError, nodes: [] }
      : (m.nodes || m.chunks)
  return {
    answer: m.answer,
    tool,
    routed_to: m.forced ? undefined : tool,
    sql: m.sql,
    spec: m.spec,
    source,
    raw_data,
  }
}

export default function AnswerMessage({ m }) {
  const [showSource, setShowSource] = useState(false)
  const [showRaw, setShowRaw] = useState(false)
  const [showJson, setShowJson] = useState(false)

  const tool = m.tool
  const label = m.error ? '요청 거부' : TOOLS[tool].label
  const evidenceChunks = m.chunks ? m.chunks.filter((c) => c.evidence) : []
  const srcCount = m.error ? 0 : (m.table ? 1 : m.nodes ? m.nodes.length : m.chunks ? evidenceChunks.length : 0)
  const rawCount = m.error ? 0 : (m.table ? m.table.rows.length : m.nodes ? m.nodes.length : m.chunks ? m.chunks.length : 0)
  const noInfo = !!m.noInfo || !!m.nodeError

  const routeLabel = m.error
    ? '도구 실행 전 거부'
    : m.forced
      ? '도구 직접 지정'
      : m.fallbackRoute
        ? `ask → LLM 폴백 → ${tool}`
        : `ask → routed_to: ${tool}`

  const statusLabel = m.error ? '거부 — 부가 필드 없음' : noInfo ? '정보 없음 (정상 응답)' : `근거 ${srcCount}건 확인 가능`
  const statusBg = m.error ? 'var(--color-neutral-200)' : noInfo ? 'var(--color-neutral-100)' : 'var(--color-accent-100)'
  const statusFg = m.error ? 'var(--color-neutral-900)' : noInfo ? 'var(--color-neutral-800)' : 'var(--color-accent-800)'

  const rawShapeLabel = m.error
    ? 'raw_data: null'
    : m.table
      ? '{ columns, rows, row_count, total_count, truncated }'
      : m.nodeError
        ? '{ error, nodes: [] }'
        : m.nodes
          ? '{ nodes: [] }'
          : 'chunk[]'

  const sourceItems = [
    ...(m.nodes || []).map((n) => ({ id: n.id, name: n.name, meta: n.meta || (n.position ? `${n.position} · ${n.dept}` : n.category ? `${n.category} · ${n.price}` : '') })),
    ...evidenceChunks.map((c) => ({ id: c.doc_id, name: c.title, meta: `${TYPE_KO[c.type]} · rerank ${c.rerank_score.toFixed(2)}` })),
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 940 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 7, border: '1px solid var(--color-accent)',
            background: 'var(--color-accent)', color: 'var(--color-bg)', padding: '4px 9px',
            fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 12, letterSpacing: '.02em',
          }}
        >
          {label}
        </span>
        <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)' }}>{routeLabel}</span>
        <span style={{ marginLeft: 'auto', font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
          {m.error ? '0.0초' : `${m.elapsed}초`}
        </span>
      </div>

      <div style={{ borderLeft: '2px solid var(--color-accent)', padding: '2px 0 2px 14px', fontSize: 14.5, lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>
        {m.answer}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 9px', fontSize: 11, background: statusBg, color: statusFg }}>
          {statusLabel}
        </span>
        {!!(m.table && m.table.truncated) && (
          <span style={{ fontSize: 11, color: 'var(--color-neutral-700)', border: '1px dashed var(--color-neutral-400)', padding: '3px 9px' }}>
            answer는 최대 50건까지만 나열 · 표는 raw_data {rawCount}행 기준
          </span>
        )}
        {!!m.routerWould && (
          <span style={{ fontSize: 11, color: 'var(--color-accent-800)', border: '1px dashed var(--color-accent-400)', padding: '3px 9px' }}>
            자동 라우팅(ask)이라면 {m.routerWould}로 처리되는 질문입니다
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, borderTop: '1px solid var(--color-divider)', paddingTop: 10 }}>
        <button className="btn btn-secondary" onClick={() => setShowSource((v) => !v)}>
          근거 {m.error ? '—' : srcCount === 0 ? '없음' : `${srcCount}건`}
        </button>
        <button className="btn btn-secondary" onClick={() => setShowRaw((v) => !v)}>
          원자료 {m.error ? '—' : `${rawCount}건`}
        </button>
        <button className="btn btn-ghost" onClick={() => setShowJson((v) => !v)}>JSON</button>
      </div>

      {showSource && (
        <div style={{ border: '1px solid var(--color-divider)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-neutral-600)' }}>근거 (source)</div>
          {(m.error || noInfo) && (
            <div style={{ fontSize: 13, color: 'var(--color-neutral-700)', lineHeight: 1.55 }}>
              {m.error
                ? m.refusal
                : m.nodeError
                  ? '근거 노드 없음 — 개체를 찾지 못해 탐색이 시작되지 않았습니다.'
                  : 'source는 빈 배열입니다. 검색·재순위는 정상적으로 끝났지만 답변에 반영할 만한 문서가 없었습니다. 오류가 아니라 정상 응답입니다.'}
            </div>
          )}
          {!!m.sql && (
            <pre style={{ margin: 0, background: 'var(--color-accent-900)', color: '#e9eef4', padding: '12px 14px', font: '12px/1.6 ui-monospace,Menlo,monospace', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
              {m.sql}
            </pre>
          )}
          {sourceItems.map((s) => (
            <div key={s.id} style={{ display: 'flex', alignItems: 'baseline', gap: 10, borderBottom: '1px solid color-mix(in srgb, var(--color-text) 8%, transparent)', paddingBottom: 7 }}>
              <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-accent-700)', flex: 'none', minWidth: 96 }}>{s.id}</span>
              <span style={{ fontSize: 13 }}>{s.name}</span>
              <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-neutral-600)' }}>{s.meta}</span>
            </div>
          ))}
        </div>
      )}

      {showRaw && (
        <div style={{ border: '1px solid var(--color-divider)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-neutral-600)' }}>원자료 (raw_data)</span>
            <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)' }}>{rawShapeLabel}</span>
          </div>

          {m.table && <RawDataTable table={m.table} />}
          {m.nodeError && (
            <div style={{ border: '1px solid var(--color-neutral-400)', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 14 }}>개체를 찾지 못함</div>
              <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--color-neutral-800)' }}>{m.nodeError}</div>
              <div style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
                raw_data.error 존재 · nodes: [] — 빈 결과와는 다른 상태로 표시합니다.
              </div>
            </div>
          )}
          {!!(m.nodes && m.nodes.length) && <GraphView graph={m.graph} nodes={m.nodes} />}
          {!!(m.chunks && m.chunks.length) && <ChunkList chunks={m.chunks} />}
        </div>
      )}

      {showJson && (
        <pre className="scr" style={{ margin: 0, border: '1px solid var(--color-divider)', background: 'var(--color-surface)', padding: '12px 14px', font: '11.5px/1.6 ui-monospace,Menlo,monospace', maxHeight: 280, overflow: 'auto' }}>
          {JSON.stringify(buildJson(m, tool), null, 2)}
        </pre>
      )}
    </div>
  )
}
