import { useMemo, useState } from 'react'

const PER_PAGE = 8

export default function RawDataTable({ table }) {
  const [sort, setSort] = useState({ col: null, dir: 1 })
  const [page, setPage] = useState(0)
  const [chartOn, setChartOn] = useState(false)

  const cols = table.columns
  const rawRows = table.rows

  const rows = useMemo(() => {
    const copy = rawRows.slice()
    if (sort.col !== null) {
      const i = cols.indexOf(sort.col)
      copy.sort((a, b) => {
        const x = a[i], y = b[i]
        if (typeof x === 'number' && typeof y === 'number') return (x - y) * sort.dir
        return String(x).localeCompare(String(y), 'ko') * sort.dir
      })
    }
    return copy
  }, [rawRows, cols, sort])

  const pages = Math.max(Math.ceil(rows.length / PER_PAGE), 1)
  const curPage = Math.min(page, pages - 1)
  const visible = rows.slice(curPage * PER_PAGE, curPage * PER_PAGE + PER_PAGE)

  let numIdx = -1
  for (let i = cols.length - 1; i >= 0; i--) {
    if (rows.length && rows.every((r) => typeof r[i] === 'number')) { numIdx = i; break }
  }
  const hasChart = numIdx >= 0 && cols.length > 1
  const showChart = chartOn && numIdx >= 0
  const max = numIdx >= 0 ? Math.max(...visible.map((r) => Math.abs(r[numIdx])), 0) : 0

  const sortBy = (col) => {
    setSort((s) => ({ col, dir: s.col === col ? -s.dir : 1 }))
    setPage(0)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {table.truncated && (
        <div style={{ border: '1px solid var(--color-accent-400)', background: 'var(--color-accent-100)', padding: '8px 11px', fontSize: 12, lineHeight: 1.5, color: 'var(--color-accent-900)' }}>
          표시된 {table.rows.length}행은 전체 결과의 일부입니다. total_count가 null이라 정확한 총계를 알 수 없습니다.
        </div>
      )}

      {hasChart && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => setChartOn((v) => !v)}>
            {chartOn ? '표로 보기' : '차트로 보기'}
          </button>
        </div>
      )}

      {showChart && (
        <div style={{ border: '1px solid var(--color-divider)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 9 }}>
          <div style={{ font: '10.5px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)' }}>
            {cols[numIdx]} — 현재 페이지 {visible.length}행 ({cols[0]} 기준)
          </div>
          {visible.map((r, i) => {
            const w = max ? Math.max(Math.round(Math.abs(r[numIdx]) / max * 100), 1) : 0
            return (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '170px 1fr 90px', gap: 10, alignItems: 'center' }}>
                <span style={{ fontSize: 12.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(r[0])}</span>
                <span style={{ height: 11, background: 'var(--color-neutral-200)' }}>
                  <span style={{ display: 'block', height: 11, background: 'var(--color-accent)', width: `${w}%` }} />
                </span>
                <span style={{ font: '11px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)', textAlign: 'right' }}>{String(r[numIdx])}</span>
              </div>
            )
          })}
        </div>
      )}

      {(!chartOn || numIdx < 0) && (
        <div style={{ overflowX: 'auto', border: '1px solid var(--color-divider)' }}>
          <table className="table">
            <thead>
              <tr>
                {cols.map((c) => (
                  <th key={c} style={{ cursor: 'pointer', whiteSpace: 'nowrap', userSelect: 'none' }} onClick={() => sortBy(c)}>
                    {c}{sort.col === c ? (sort.dir > 0 ? '  ↑' : '  ↓') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((r, i) => (
                <tr key={i}>
                  {r.map((v, j) => <td key={j} style={{ whiteSpace: 'nowrap' }}>{String(v)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button className="btn btn-secondary" onClick={() => setPage((p) => Math.max(p - 1, 0))}>이전</button>
        <button className="btn btn-secondary" onClick={() => setPage((p) => Math.min(p + 1, pages - 1))}>다음</button>
        <span style={{ font: '11px ui-monospace,Menlo,monospace', color: 'var(--color-neutral-700)' }}>
          {curPage + 1} / {pages} 페이지 · raw_data {rows.length}행 기준
        </span>
      </div>
    </div>
  )
}
