import { useEffect, useRef, useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import EmptyState from './components/EmptyState'
import UserMessage from './components/UserMessage'
import PendingMessage from './components/PendingMessage'
import AnswerMessage from './components/AnswerMessage'
import Composer from './components/Composer'
import ExamplesPage from './components/ExamplesPage'
import InfoPage from './components/InfoPage'
import { TOOLS } from './data/scenarios'
import { pick } from './lib/pick'

const MAX_QUESTION_CHARS = 2000

export default function App() {
  const [page, setPage] = useState('console')
  const [draft, setDraft] = useState('')
  const [tool, setTool] = useState('ask')
  const [chats, setChats] = useState([])
  const [activeId, setActiveId] = useState(null)

  const scrollRef = useRef(null)
  const elapsedRef = useRef(null)
  const timerRef = useRef(null)
  const jobRef = useRef(null)

  const activeChat = chats.find((c) => c.id === activeId) || null
  const activeMessages = activeChat ? activeChat.messages : []
  const isBusy = activeMessages.some((m) => m.role === 'pending')

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [activeMessages.length, activeId])

  useEffect(() => () => {
    clearInterval(timerRef.current)
    clearTimeout(jobRef.current)
  }, [])

  const pushMessages = (chatId, title, entries, extra) => {
    setChats((prev) => {
      let list = prev.slice()
      let idx = list.findIndex((c) => c.id === chatId)
      if (idx < 0) {
        list = [{ id: chatId, title, messages: [] }, ...list]
        idx = 0
      }
      list[idx] = { ...list[idx], messages: list[idx].messages.concat(entries) }
      return list
    })
    setActiveId(chatId)
    if (extra?.draft !== undefined) setDraft(extra.draft)
  }

  const patchMessage = (chatId, msgId, patch) => {
    setChats((prev) => prev.map((c) => (
      c.id !== chatId ? c : { ...c, messages: c.messages.map((m) => (m.id === msgId ? { ...m, ...patch } : m)) }
    )))
  }

  // Resolves a question against the mock router/scenarios and drives it
  // through a pending message to a patched-in answer, on the given chat.
  const runQuestion = (chatId, title, q) => {
    const id = 'm' + Date.now()
    const forced = tool !== 'ask'
    const sc = pick(q, forced ? tool : null)
    const routed = forced ? pick(q, null) : null
    const mismatch = routed && routed.tool !== sc.tool ? TOOLS[routed.tool].label : null

    clearInterval(timerRef.current)
    clearTimeout(jobRef.current)

    pushMessages(chatId, title, [
      { id: id + 'u', role: 'user', text: q },
      { id, role: 'pending', tool: sc.tool, forced },
    ], { draft: '' })

    const t0 = Date.now()
    timerRef.current = setInterval(() => {
      const el = elapsedRef.current
      if (el) el.textContent = ((Date.now() - t0) / 1000).toFixed(1) + '초 경과'
    }, 100)

    jobRef.current = setTimeout(() => {
      clearInterval(timerRef.current)
      const sec = (sc.latency / 1000).toFixed(1)
      patchMessage(chatId, id, { role: 'answer', question: q, forced, routerWould: mismatch, elapsed: sec, ...sc })
    }, sc.latency)
  }

  const submit = () => {
    if (isBusy) return
    const q = draft.trim()
    const chatId = activeChat ? activeId : 'c' + Date.now()

    if (!q) {
      pushMessages(chatId, '빈 질문', [{
        id: 'm' + Date.now(), role: 'answer', error: true, tool: null,
        answer: '질문이 비어 있습니다. 질문을 입력해 주세요.', elapsed: 0,
        refusal: '사전 거부 — 도구를 실행하지 않았습니다. sql·spec·routed_to 부가 필드가 응답에 없습니다.',
      }])
      return
    }
    if (q.length > MAX_QUESTION_CHARS) {
      pushMessages(chatId, q, [
        { id: 'm' + Date.now() + 'u', role: 'user', text: q.slice(0, 120) + ` …(${q.length}자)` },
        {
          id: 'm' + Date.now(), role: 'answer', error: true, tool: null,
          answer: '질문이 너무 깁니다. 2,000자 이내로 입력해 주세요.', elapsed: 0,
          refusal: '사전 거부 — 입력 길이 초과. 부가 필드 없음.',
        },
      ], { draft: '' })
      return
    }

    runQuestion(chatId, q, q)
  }

  // Sample-question buttons submit immediately with a specific question text
  // rather than going through setDraft()+submit(), since submit() reads
  // `draft` from state and a setDraft() just before it would race the update.
  const handlePickAndSubmit = (q) => {
    if (isBusy) return
    const chatId = activeChat ? activeId : 'c' + Date.now()
    runQuestion(chatId, q, q)
  }

  const onNew = () => {
    clearInterval(timerRef.current)
    clearTimeout(jobRef.current)
    setActiveId(null)
    setDraft('')
    setPage('console')
  }

  const onDeleteChat = (chatId) => {
    setChats((prev) => prev.filter((c) => c.id !== chatId))
    setActiveId((cur) => (cur === chatId ? null : cur))
  }

  const pendingMsg = activeMessages.find((m) => m.role === 'pending')

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Header page={page} onNavigate={setPage} />

      {page === 'console' && (
        <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
          <Sidebar
            chats={chats}
            activeId={activeId}
            onNew={onNew}
            onOpenExamples={() => setPage('examples')}
            onOpenChat={(id) => { setPage('console'); setActiveId(id) }}
            onDeleteChat={onDeleteChat}
          />

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div ref={scrollRef} className="scr" style={{ flex: 1, overflowY: 'auto', padding: '26px 26px 30px', display: 'flex', flexDirection: 'column', gap: 22 }}>
              {activeMessages.length === 0 && <EmptyState onPick={handlePickAndSubmit} />}

              {activeMessages.map((m) => {
                if (m.role === 'user') return <UserMessage key={m.id} text={m.text} />
                if (m.role === 'pending') {
                  return <PendingMessage key={m.id} tool={m.tool} forced={m.forced} elapsedRef={m.id === pendingMsg?.id ? elapsedRef : undefined} />
                }
                return <AnswerMessage key={m.id} m={m} />
              })}
            </div>

            <Composer
              tool={tool}
              onToolChange={setTool}
              draft={draft}
              onDraftChange={setDraft}
              busy={isBusy}
              onSubmit={submit}
            />
          </div>
        </div>
      )}

      {page === 'examples' && (
        <ExamplesPage onPick={(q) => { setDraft(q); setPage('console') }} />
      )}

      {page === 'info' && <InfoPage />}
    </div>
  )
}
