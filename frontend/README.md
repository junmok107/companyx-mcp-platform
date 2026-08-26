# MCP·QUERY 프론트엔드

Company-X MCP 플랫폼의 대화형 콘솔 UI. [Claude Design](https://claude.ai/design) 목업
(`MCP Query Platform.dc.html`)을 React + Vite로 그대로 구현한 것이다.

## 실데이터 연동

이 프론트엔드는 HTTP 브릿지([`bridge/server.py`](../bridge/server.py))를 통해 실제
백엔드(PostgreSQL/pgvector + Ollama)와 연동된다. 브릿지는 MCP stdio로만 노출되는 세 도구
파이프라인을 그대로 import해 HTTP POST(`/ask`, `/tool/{name}`, `/health`)로 노출하며,
응답은 `{answer, raw_data, tool, source}` 계약을 따른다.

[`src/lib/api.js`](src/lib/api.js)가 브릿지를 호출하고 그 응답을 화면 렌더링 형태로 변환한다.
브릿지 주소 기본값은 `http://127.0.0.1:8000`이며 `VITE_BRIDGE_URL`로 바꿀 수 있다.

목업(`src/data/scenarios.js`, `src/lib/pick.js`)은 브릿지 없이 UI만 볼 때를 위한 참고용으로
보존하지만, 실제 화면 동작에는 더 이상 쓰지 않는다.

## 실행

먼저 백엔드 브릿지를 띄운다(프로젝트 루트에서, PostgreSQL·Ollama 기동 상태):

```bash
export PGPASSWORD=<mcp_reader 비밀번호>
python -m uvicorn bridge.server:app --host 127.0.0.1 --port 8000
```

그다음 프론트엔드를 실행한다:

```bash
npm install
npm run dev      # 개발 서버 (기본 http://localhost:5173)
npm run build    # 프로덕션 빌드
npm run lint      # oxlint
```

## 구조

- `src/data/scenarios.js` — 질문 매칭용 목업 시나리오(도구별 답변/근거/원자료)
- `src/lib/pick.js` — 데모용 라우팅 로직 (실제 백엔드의 규칙 기반 라우터를 흉내)
- `src/components/` — 화면 구성 요소 (Header, Sidebar, Composer, AnswerMessage 등)
- `src/styles/design-system.css` — Claude Design이 만든 "Industry" 디자인 시스템 원본
