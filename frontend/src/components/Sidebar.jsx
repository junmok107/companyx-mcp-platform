import { TOOLS } from '../data/scenarios'

export default function Sidebar({ chats, activeId, onNew, onOpenExamples, onOpenChat, onDeleteChat }) {
  return (
    <aside
      style={{
        width: 268, flex: 'none', borderRight: '1px solid var(--color-divider)',
        display: 'flex', flexDirection: 'column', background: 'var(--color-surface)',
      }}
    >
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8, borderBottom: '1px solid var(--color-divider)' }}>
        <button className="btn btn-primary btn-block" style={{ marginTop: 0 }} onClick={onNew}>새 채팅</button>
        <button className="btn btn-secondary btn-block" style={{ marginTop: 0 }} onClick={onOpenExamples}>예시 질문 30개</button>
      </div>

      <div style={{ padding: '14px 16px 6px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--color-neutral-600)' }}>
        이 세션 채팅
      </div>

      <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '0 12px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {chats.length === 0 && (
          <div style={{ fontSize: 12, color: 'var(--color-neutral-600)', padding: '6px 4px', lineHeight: 1.5 }}>
            아직 채팅이 없습니다. 질문을 하면 채팅이 하나 만들어지고, 세션 안에서만 유지됩니다.
          </div>
        )}
        {chats.map((c) => {
          const on = c.id === activeId
          const answers = c.messages.filter((m) => m.role === 'answer')
          const lastTool = answers.length ? answers[answers.length - 1].tool : null
          const userCount = c.messages.filter((m) => m.role === 'user').length
          return (
            <div
              key={c.id}
              style={{
                display: 'flex', alignItems: 'stretch',
                border: `1px solid ${on ? 'var(--color-accent)' : 'var(--color-divider)'}`,
                background: on ? 'var(--color-accent-100)' : 'transparent',
              }}
            >
              <button
                className="chat-row-btn"
                style={{
                  flex: 1, minWidth: 0, textAlign: 'left', border: 0, background: 'transparent',
                  padding: '8px 10px', cursor: 'pointer', display: 'flex', flexDirection: 'column',
                  gap: 4, font: 'inherit',
                }}
                onClick={() => onOpenChat(c.id)}
              >
                <span
                  style={{
                    fontSize: 12.5, lineHeight: 1.35, color: 'var(--color-text)', overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 190,
                  }}
                >
                  {c.title}
                </span>
                <span style={{ display: 'flex', gap: 6, alignItems: 'center', font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
                  <span style={{ width: 7, height: 7, background: 'var(--color-accent-700)', flex: 'none' }} />
                  질문 {userCount}건{lastTool ? ` · ${TOOLS[lastTool].label}` : ''}
                </span>
              </button>
              <button
                title="채팅 삭제"
                className="chat-del-btn"
                style={{
                  flex: 'none', width: 28, border: 0, borderLeft: '1px solid var(--color-divider)',
                  background: 'transparent', cursor: 'pointer', font: 'inherit', fontSize: 13,
                  color: 'var(--color-neutral-600)',
                }}
                onClick={(e) => { e.stopPropagation(); onDeleteChat(c.id) }}
              >
                ×
              </button>
            </div>
          )
        })}
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--color-divider)', font: '9.5px/1.5 ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
        로컬 전용 · Ollama gemma2:9b · pgvector
      </div>
    </aside>
  )
}
