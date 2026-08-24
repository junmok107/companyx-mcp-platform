import { EXAMPLES } from '../data/scenarios'

const CARDS = [
  { kicker: 'NL2SQL', title: '정형 데이터', body: '매출·계약·직원·제품·티켓을 표로. 근거는 실행된 SQL 문입니다.', key: 'nl2sql' },
  { kicker: '지식 그래프', title: '개체 간 관계', body: '담당·소속·사용·리드 관계를 따라갑니다. 근거는 노드입니다.', key: 'knowledge_graph' },
  { kicker: '벡터 검색', title: '사내 문서', body: '장애보고서·기술문서·회의록·제안서 의미 검색. 근거는 문서입니다.', key: 'vector_search' },
]

export default function EmptyState({ onPick }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22, maxWidth: 860 }}>
      <div>
        <h2 style={{ margin: '0 0 6px' }}>무엇을 물어볼 수 있나요</h2>
        <p style={{ margin: 0, fontSize: 14, color: 'var(--color-neutral-700)', maxWidth: '60ch' }}>
          정형 데이터(매출·계약·직원·티켓), 개체 간 관계, 사내 문서 세 가지를 한 입력창에서 물어봅니다.
          기본은 자동 라우팅이고, 도구를 직접 고를 수도 있습니다. 모든 답변에는 어떤 데이터에 근거했는지가 함께 붙습니다.
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
        {CARDS.map((c) => (
          <div key={c.key} className="card blueprint" style={{ padding: 14, gap: 8 }}>
            <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
            <div className="card-kicker">{c.kicker}</div>
            <div className="card-title">{c.title}</div>
            <p className="card-body">{c.body}</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 2 }}>
              {EXAMPLES[c.key].slice(0, 2).map((q) => (
                <button
                  key={q}
                  className="sample-btn"
                  style={{
                    textAlign: 'left', font: 'inherit', fontSize: 12.5, lineHeight: 1.35,
                    border: '1px solid var(--color-divider)', background: 'transparent', padding: '7px 9px',
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
  )
}
