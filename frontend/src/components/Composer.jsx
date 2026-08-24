import { TOOLS } from '../data/scenarios'

export default function Composer({ tool, onToolChange, draft, onDraftChange, busy, onSubmit }) {
  const len = draft.length
  const toolHint = tool === 'ask'
    ? '규칙 기반 라우터가 도구를 고릅니다. 규칙 점수가 0이면 LLM 폴백(+약 2.8초).'
    : `${TOOLS[tool].label} 엔드포인트를 직접 호출합니다.`

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div
      style={{
        borderTop: '1px solid var(--color-divider)', padding: '14px 26px 16px',
        display: 'flex', flexDirection: 'column', gap: 10, background: 'var(--color-surface)', flex: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div className="seg">
          <label className="seg-opt">
            <input type="radio" name="tool" checked={tool === 'ask'} onChange={() => onToolChange('ask')} />자동 (ask)
          </label>
          <label className="seg-opt">
            <input type="radio" name="tool" checked={tool === 'nl2sql'} onChange={() => onToolChange('nl2sql')} />NL2SQL
          </label>
          <label className="seg-opt">
            <input type="radio" name="tool" checked={tool === 'knowledge_graph'} onChange={() => onToolChange('knowledge_graph')} />지식 그래프
          </label>
          <label className="seg-opt">
            <input type="radio" name="tool" checked={tool === 'vector_search'} onChange={() => onToolChange('vector_search')} />벡터 검색
          </label>
        </div>
        <span style={{ fontSize: 11.5, color: 'var(--color-neutral-600)' }}>{toolHint}</span>
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        <div className="field" style={{ flex: 1 }}>
          <textarea
            className="input"
            style={{ minHeight: 64 }}
            placeholder="예: Critical 우선순위 티켓 중 아직 해결되지 않은 건은?"
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6, flex: 'none' }}>
          <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: len > 2000 ? 'var(--color-accent-900)' : 'var(--color-neutral-600)' }}>
            {len} / 2,000자
          </span>
          <button
            className="btn btn-primary"
            style={{ marginTop: 0, minWidth: 104, height: 38, opacity: busy ? 0.45 : 1 }}
            onClick={onSubmit}
          >
            {busy ? '조회 중…' : '질문하기'}
          </button>
        </div>
      </div>
    </div>
  )
}
