export default function UserMessage({ text }) {
  return (
    <div
      style={{
        alignSelf: 'flex-end', maxWidth: '72%', background: 'var(--color-accent)',
        color: 'var(--color-bg)', padding: '10px 14px', fontSize: 14, lineHeight: 1.5,
        whiteSpace: 'pre-wrap',
      }}
    >
      {text}
    </div>
  )
}
