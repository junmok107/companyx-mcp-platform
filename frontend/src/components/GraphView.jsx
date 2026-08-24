import { NODE_TYPE_KO } from '../data/scenarios'

function nodeAttrs(n) {
  if (n.attrs) return n.attrs
  if (n.position) return `position=${n.position} · dept=${n.dept}`
  return `category=${n.category} · price=${n.price}`
}

export default function GraphView({ graph, nodes }) {
  const positioned = nodes.slice(0, 12).map((n, i, arr) => {
    const a = -Math.PI / 2 + (i / arr.length) * Math.PI * 2
    return { name: n.name, x: (50 + Math.cos(a) * 34).toFixed(2) + '%', y: (50 + Math.sin(a) * 36).toFixed(2) + '%' }
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ border: '1px solid var(--color-divider)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-accent-700)' }}>{graph?.relation}</span>
          <span style={{ font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>{graph?.direction}</span>
          <span style={{ marginLeft: 'auto', font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
            {nodes.length > 12 ? `노드 ${nodes.length}건 중 12건 표시` : `노드 ${nodes.length}건`}
          </span>
        </div>
        <div style={{ position: 'relative', height: 340, background: 'var(--color-surface)' }}>
          <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
            {positioned.map((e, i) => (
              <line key={i} x1="50%" y1="50%" x2={e.x} y2={e.y} stroke="#b7b7ba" strokeWidth="1" />
            ))}
          </svg>
          <div
            style={{
              position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)',
              border: '1px solid var(--color-accent)', background: 'var(--color-accent)', color: 'var(--color-bg)',
              padding: '8px 12px', fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 14,
              whiteSpace: 'nowrap', zIndex: 2,
            }}
          >
            {graph?.entity}
          </div>
          {positioned.map((g, i) => (
            <div
              key={i}
              style={{
                position: 'absolute', left: g.x, top: g.y, transform: 'translate(-50%,-50%)',
                border: '1px solid var(--color-accent-600)', background: 'var(--color-bg)', padding: '5px 9px',
                fontSize: 12, whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6, zIndex: 2,
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-accent-600)', flex: 'none' }} />
              {g.name}
            </div>
          ))}
        </div>
        <div style={{ font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
          기준 개체(가운데)에서 {graph?.relation} 관계로 도달한 노드입니다.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {nodes.map((n) => (
          <div key={n.id} style={{ border: '1px solid var(--color-divider)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 5 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 15 }}>{n.name}</span>
              <span style={{ font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>{n.id}</span>
              <span style={{ marginLeft: 'auto', fontSize: 10, padding: '2px 7px', background: 'var(--color-neutral-100)', color: 'var(--color-neutral-800)' }}>
                {NODE_TYPE_KO[n.type] || n.type}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-neutral-700)' }}>{nodeAttrs(n)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
