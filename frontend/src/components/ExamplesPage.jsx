import { EXAMPLES } from '../data/scenarios'

const GROUPS = [
  { key: 'nl2sql', kicker: 'NL2SQL', title: '정형 데이터', body: '매출·계약·직원·제품·티켓 등 수치와 집계' },
  { key: 'knowledge_graph', kicker: '지식 그래프', title: '개체 간 관계', body: '담당·소속·사용·리드 관계 탐색' },
  { key: 'vector_search', kicker: '벡터 검색', title: '사내 문서', body: '장애보고서·기술문서·회의록·제안서 의미 검색' },
]

export default function ExamplesPage({ onPick }) {
  return (
    <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '34px 30px 40px' }}>
      <div style={{ maxWidth: 1240, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div>
          <h2 style={{ margin: '0 0 6px' }}>예시 질문 30개</h2>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--color-neutral-700)', maxWidth: '66ch' }}>
            도구별 10개씩입니다. 클릭하면 콘솔 입력창에 채워집니다. 채점용 내부 힌트는 화면에 노출하지 않습니다.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 18 }}>
          {GROUPS.map((g) => (
            <div key={g.key} className="blueprint" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
              <div>
                <div className="card-kicker">{g.kicker}</div>
                <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 20 }}>{g.title}</div>
                <div style={{ fontSize: 12.5, color: 'var(--color-neutral-700)', lineHeight: 1.5, marginTop: 3 }}>{g.body}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {EXAMPLES[g.key].map((q) => (
                  <button
                    key={q}
                    className="example-btn"
                    style={{
                      textAlign: 'left', font: 'inherit', fontSize: 13, lineHeight: 1.4,
                      border: '1px solid var(--color-divider)', background: 'transparent', padding: '8px 10px',
                      cursor: 'pointer', color: 'var(--color-text)',
                    }}
                    onClick={() => onPick(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
