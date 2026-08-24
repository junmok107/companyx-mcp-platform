# MCP·QUERY 프론트엔드

Company-X MCP 플랫폼의 대화형 콘솔 UI. [Claude Design](https://claude.ai/design) 목업
(`MCP Query Platform.dc.html`)을 React + Vite로 그대로 구현한 것이다.

## 데모 모드 안내

백엔드(`mcp_server/`)는 MCP stdio 프로토콜로만 노출되어 있어 브라우저에서 직접 호출할 수
없다. 이 프론트엔드는 [`src/data/scenarios.js`](src/data/scenarios.js)에 담긴 목업
시나리오로 동작하며, 실제 PostgreSQL/Ollama 호출은 하지 않는다. 화면 우측 상단의
"데모 모드 · 목업 데이터" 표시가 이를 알려준다.

실제 데이터와 연동하려면 MCP 도구(`ask`, `nl2sql_query`, `knowledge_graph_query`,
`vector_search_query`)를 HTTP로 감싸는 별도의 브릿지 서버가 필요하다 — 이 프론트엔드의
범위 밖이다. `docs/frontend_requirements.md`에 이 응답 계약이 문서화되어 있다.

## 실행

```bash
npm install
npm run dev      # 개발 서버
npm run build    # 프로덕션 빌드
npm run lint      # oxlint
```

## 구조

- `src/data/scenarios.js` — 질문 매칭용 목업 시나리오(도구별 답변/근거/원자료)
- `src/lib/pick.js` — 데모용 라우팅 로직 (실제 백엔드의 규칙 기반 라우터를 흉내)
- `src/components/` — 화면 구성 요소 (Header, Sidebar, Composer, AnswerMessage 등)
- `src/styles/design-system.css` — Claude Design이 만든 "Industry" 디자인 시스템 원본
