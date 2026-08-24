import { TOOLS } from '../data/scenarios'

export default function PendingMessage({ tool, forced, elapsedRef }) {
  const t = tool || 'nl2sql'
  const stageLabel = forced ? `${TOOLS[t].label} 호출 중` : '라우터가 도구를 고르는 중'

  return (
    <div style={{ border: '1px solid var(--color-divider)', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 620 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ width: 9, height: 9, background: 'var(--color-accent)', animation: 'pulse 1.1s ease-in-out infinite' }} />
        <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 14 }}>{stageLabel}</span>
        <span ref={elapsedRef} style={{ marginLeft: 'auto', font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
          0.0초 경과
        </span>
      </div>
      <div style={{ height: 3, background: 'var(--color-neutral-300)', overflow: 'hidden', position: 'relative' }}>
        <span style={{ position: 'absolute', inset: 0, width: '33%', background: 'var(--color-accent)', animation: 'sweep 1.4s linear infinite' }} />
      </div>
      <div style={{ fontSize: 12, color: 'var(--color-neutral-700)', lineHeight: 1.5 }}>
        응답은 완료 후 한 번에 옵니다. 목록형은 약 5초, 단일값·문장 생성이 붙으면 약 9초까지 걸립니다.
      </div>
    </div>
  )
}
