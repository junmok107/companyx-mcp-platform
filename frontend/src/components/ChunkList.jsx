import { TYPE_KO } from '../data/scenarios'

export default function ChunkList({ chunks }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 11.5, color: 'var(--color-neutral-700)', lineHeight: 1.5 }}>
        검색·재순위를 마친 후보 {chunks.length}건 전부입니다. 실선 카드가 답변에 반영된 근거(source), 점선 카드는 검색만 된 후보입니다.
      </div>

      <div style={{ border: '1px solid var(--color-divider)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 9, background: 'var(--color-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)' }}>유사도 → 재순위 점수 이동</span>
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 12, font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
            <span>○ similarity</span><span>● rerank</span>
          </span>
        </div>
        {chunks.map((c) => {
          const lo = Math.min(c.similarity, c.rerank_score) * 100
          const hi = Math.max(c.similarity, c.rerank_score) * 100
          const fg = c.evidence ? 'var(--color-accent-800)' : 'var(--color-neutral-600)'
          const trackColor = c.evidence ? 'var(--color-accent)' : 'var(--color-neutral-400)'
          return (
            <div key={c.doc_id + c.chunk_index} style={{ display: 'grid', gridTemplateColumns: '112px 1fr 46px', gap: 10, alignItems: 'center' }}>
              <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: fg, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.doc_id} {c.evidence ? '· 근거' : '· 후보'}
              </span>
              <span style={{ position: 'relative', height: 18, borderBottom: '1px solid var(--color-neutral-300)', display: 'block' }}>
                <span style={{ position: 'absolute', top: 8, height: 2, background: trackColor, left: `${lo}%`, width: `${hi - lo}%` }} />
                <span style={{ position: 'absolute', top: 4, left: `${c.similarity * 100}%`, width: 9, height: 9, borderRadius: '50%', border: `1.5px solid ${trackColor}`, background: 'var(--color-bg)', transform: 'translateX(-50%)' }} />
                <span style={{ position: 'absolute', top: 4, left: `${c.rerank_score * 100}%`, width: 9, height: 9, borderRadius: '50%', background: trackColor, transform: 'translateX(-50%)' }} />
              </span>
              <span style={{ font: '10.5px ui-monospace,Menlo,monospace', color: fg, textAlign: 'right' }}>{c.rerank_score.toFixed(2)}</span>
            </div>
          )
        })}
        <div style={{ display: 'grid', gridTemplateColumns: '112px 1fr 46px', gap: 10 }}>
          <span />
          <span style={{ display: 'flex', justifyContent: 'space-between', font: '9.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
            <span>0.0</span><span>0.5</span><span>1.0</span>
          </span>
          <span />
        </div>
      </div>

      {chunks.map((c) => (
        <div
          key={c.doc_id + ':' + c.chunk_index}
          style={{
            border: `1px solid ${c.evidence ? 'var(--color-accent)' : 'var(--color-neutral-300)'}`,
            padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8,
            background: c.evidence ? 'var(--color-bg)' : 'transparent',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, flexWrap: 'wrap' }}>
            <span style={{ font: '11px ui-monospace,Menlo,monospace', color: 'var(--color-accent-700)' }}>{c.doc_id} · #{c.chunk_index}</span>
            <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 14.5 }}>{c.title}</span>
            <span style={{ fontSize: 10, padding: '2px 7px', background: 'var(--color-neutral-100)', color: 'var(--color-neutral-800)' }}>{TYPE_KO[c.type]}</span>
            <span
              style={{
                marginLeft: 'auto', fontSize: 10.5, padding: '2px 8px',
                border: `1px solid ${c.evidence ? 'var(--color-accent)' : 'var(--color-neutral-400)'}`,
                color: c.evidence ? 'var(--color-accent-800)' : 'var(--color-neutral-700)',
              }}
            >
              {c.evidence ? '근거' : '후보'}
            </span>
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--color-neutral-800)' }}>{c.content}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '70px 1fr 58px', gap: 8, alignItems: 'center', font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)' }}>
            <span>similarity</span>
            <span style={{ height: 5, background: 'var(--color-neutral-300)' }}>
              <span style={{ display: 'block', height: 5, background: 'var(--color-accent-400)', width: `${Math.round(c.similarity * 100)}%` }} />
            </span>
            <span>{c.similarity.toFixed(2)}</span>
            <span>rerank</span>
            <span style={{ height: 5, background: 'var(--color-neutral-300)' }}>
              <span style={{ display: 'block', height: 5, background: 'var(--color-accent-700)', width: `${Math.round(c.rerank_score * 100)}%` }} />
            </span>
            <span>{c.rerank_score.toFixed(2)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
