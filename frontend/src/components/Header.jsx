const PAGES = [
  ['console', '콘솔'],
  ['examples', '예시 질문'],
  ['info', '시스템 안내'],
]

export default function Header({ page, onNavigate }) {
  return (
    <header
      className="nav"
      style={{ borderBottom: '1px solid var(--color-divider)', padding: '12px 22px', gap: 22, flex: 'none' }}
    >
      <div className="nav-brand" style={{ marginRight: 0 }}>
        MCP<span style={{ color: 'var(--color-accent)' }}>·</span>QUERY
      </div>
      <div
        style={{
          fontSize: 10.5, letterSpacing: '.1em', textTransform: 'uppercase',
          color: 'var(--color-neutral-600)', marginRight: 'auto',
        }}
      >
        Company-X 통합 지능형 데이터 검색
      </div>
      <nav style={{ display: 'flex', gap: 2 }}>
        {PAGES.map(([id, label]) => {
          const on = page === id
          return (
            <button
              key={id}
              style={{
                font: 'inherit', fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 13.5,
                padding: '7px 14px', cursor: 'pointer',
                background: on ? 'var(--color-accent)' : 'transparent',
                color: on ? 'var(--color-bg)' : 'var(--color-text)',
                border: `1px solid ${on ? 'var(--color-accent)' : 'var(--color-divider)'}`,
              }}
              onClick={() => onNavigate(id)}
            >
              {label}
            </button>
          )
        })}
      </nav>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 7,
          font: '10px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)',
        }}
      >
        <span style={{ width: 7, height: 7, background: 'var(--color-accent)' }} />
        실데이터 연동 · 브릿지(:8000) · Ollama gemma2:9b · pgvector
      </div>
    </header>
  )
}
