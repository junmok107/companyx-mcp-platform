const LIMITATIONS = [
  '어휘가 전혀 겹치지 않는 패러프레이즈 질문 일부는 문서를 놓칩니다. "관련 문서를 찾지 못했습니다"로 나오며, 오류가 아니라 알려진 동작입니다.',
  '목록형 답변은 LLM 요약을 쓰지 않습니다. 누락 없이 전달하기 위한 결정론적 렌더링이라, answer 목록과 raw_data 건수가 다를 수 있습니다.',
  '라우터 키워드 사전은 표현이 달라지면 점수가 0이 되고 LLM 폴백이 처리합니다. 이 질문은 약 2.8초가 추가됩니다.',
  '데이터에 이름이 같은 서로 다른 프로젝트가 있어 같은 이름이 중복 표시될 수 있습니다. 데이터 그대로의 결과입니다.',
  '답변 문장은 읽기 편하게 금액을 억/만원으로, 상태를 한글로, 일시를 날짜로 다듬어 보여줍니다. 원본 값(초 단위 시각, 정수 금액 등)은 아래 원자료(raw_data)에 그대로 보존됩니다.',
]

export default function InfoPage() {
  return (
    <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '34px 30px 44px' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 30 }}>
        <div>
          <h2 style={{ margin: '0 0 6px' }}>시스템 안내</h2>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--color-neutral-700)', maxWidth: '66ch' }}>
            질문 1건은 이 순서로 처리됩니다. 질문 → 규칙 기반 라우터가 도구 선택 → 선택된 도구 실행(SQL 생성·그래프 순회·문서 검색) → 근거와 함께 자연어 답변 반환.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
          <div className="blueprint" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 7 }}>
            <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 9, height: 9, background: 'var(--color-accent-700)' }} />
              <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 18 }}>NL2SQL</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--color-neutral-800)' }}>
              매출·계약·직원·제품·티켓 등 수치와 집계를 다룹니다. 근거는 실제로 실행된 SQL 문 한 줄입니다.
            </div>
            <div style={{ font: '10.5px/1.6 ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
              raw_data: columns, rows, row_count, total_count, truncated
            </div>
          </div>
          <div className="blueprint" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 7 }}>
            <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 9, height: 9, borderRadius: '50%', border: '2px solid var(--color-accent-700)' }} />
              <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 18 }}>지식 그래프</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--color-neutral-800)' }}>
              담당·소속·사용·리드 같은 개체 간 관계를 따라갑니다. 근거는 노드 id이므로 화면에서는 이름과 함께 보여줍니다.
            </div>
            <div style={{ font: '10.5px/1.6 ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
              raw_data: nodes[] · 추가 필드 spec
            </div>
          </div>
          <div className="blueprint" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 7 }}>
            <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 9, height: 9, background: 'var(--color-accent-700)', transform: 'rotate(45deg)' }} />
              <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 18 }}>벡터 검색</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--color-neutral-800)' }}>
              장애보고서·기술문서·회의록·제안서를 의미로 검색합니다. 후보 청크 전부를 보여주고, 답변에 반영된 것만 근거로 표시합니다.
            </div>
            <div style={{ font: '10.5px/1.6 ui-monospace,Menlo,monospace', color: 'var(--color-neutral-600)' }}>
              raw_data: chunk[] (근거 + 미반영 후보)
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 26 }}>
          <div>
            <h4 style={{ margin: '0 0 10px' }}>응답 규격</h4>
            <table className="table">
              <thead><tr><th>필드</th><th>내용</th></tr></thead>
              <tbody>
                <tr><td>answer</td><td>항상 채워지는 자연어 답변. 실패·거부 시에도 존재</td></tr>
                <tr><td>raw_data</td><td>도구가 조회한 원자료. 쿼리를 실행하지 못한 경우에만 null</td></tr>
                <tr><td>tool</td><td>응답을 만든 도구 이름</td></tr>
                <tr><td>source</td><td>근거 목록. 비어 있을 수 있음</td></tr>
                <tr><td>routed_to</td><td>ask 사용 시 실제 라우팅된 도구</td></tr>
              </tbody>
            </table>
            <p style={{ margin: '10px 0 0', fontSize: 12.5, color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>
              "결과 없음"은 raw_data가 null인지로 판정하지 않습니다. source가 비었는지, raw_data.error가 있는지, rows·nodes가 비었는지로 구분해 표시합니다.
            </p>
          </div>
          <div>
            <h4 style={{ margin: '0 0 10px' }}>응답 지연 (실측 중앙값)</h4>
            <table className="table">
              <thead><tr><th>구간</th><th>중앙값</th></tr></thead>
              <tbody>
                <tr><td>라우팅 — 규칙 경로</td><td>0.01ms 미만</td></tr>
                <tr><td>라우팅 — LLM 폴백</td><td>약 2.8초</td></tr>
                <tr><td>NL2SQL — 목록형</td><td>약 5.5초</td></tr>
                <tr><td>NL2SQL — 단일값</td><td>약 10초</td></tr>
                <tr><td>지식 그래프 — 목록형</td><td>약 5.2초</td></tr>
                <tr><td>벡터 검색</td><td>약 7초</td></tr>
              </tbody>
            </table>
            <p style={{ margin: '10px 0 0', fontSize: 12.5, color: 'var(--color-neutral-700)', lineHeight: 1.6 }}>
              표시되는 경과 시간은 브릿지(:8000)를 통해 실제 백엔드가 처리한 실측값입니다. 대부분은 로컬 Ollama(gemma2:9b) LLM 호출 시간이며, 스트리밍이 아니라 완료 후 일괄 응답입니다.
            </p>
          </div>
        </div>

        <div>
          <h4 style={{ margin: '0 0 10px' }}>알려진 한계 — 화면에서 정상 응답으로 다루는 것들</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {LIMITATIONS.map((text) => (
              <div key={text} style={{ border: '1px dashed var(--color-neutral-400)', padding: '12px 14px', fontSize: 13, lineHeight: 1.6, color: 'var(--color-neutral-800)' }}>
                {text}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
