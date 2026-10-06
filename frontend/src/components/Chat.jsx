import { useEffect, useRef, useState } from 'react'
import { api, streamQuery } from '../api'
import Message from './Message'

const EXAMPLES = ['What does my note say about ...?', 'Explain ... with an example']

export default function Chat({ collection, chatId, hasDocuments, health, onChatCreated, onCite }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [loadError, setLoadError] = useState('')
  const currentChat = useRef(chatId)
  const abort = useRef(null)
  const endRef = useRef(null)

  useEffect(() => {
    // Only the history this chat opened with. A chat created while sending is already on screen.
    if (!currentChat.current) return
    api
      .messages(currentChat.current)
      .then((rows) => setMessages(rows.map((m) => ({ ...m, id: `db-${m.id}` }))))
      .catch((e) => setLoadError(e.message))
  }, [])

  useEffect(() => () => abort.current?.abort(), [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  const patchLast = (patch) =>
    setMessages((prev) => prev.map((m, i) => (i === prev.length - 1 ? { ...m, ...patch(m) } : m)))

  async function send(event) {
    event?.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setBusy(true)
    setLoadError('')
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', content: text },
      { id: `a-${Date.now()}`, role: 'assistant', content: '', sources: [] },
    ])

    const controller = new AbortController()
    abort.current = controller
    try {
      if (!currentChat.current) {
        const title = text.length > 40 ? `${text.slice(0, 40)}...` : text
        const chat = await api.createChat(collection.id, title)
        currentChat.current = chat.id
        onChatCreated(chat.id)
      }
      await streamQuery(
        { collection_id: collection.id, chat_id: currentChat.current, text },
        (e) => {
          if (e.type === 'metadata') patchLast(() => ({ mode: e.mode, sources: e.sources }))
          else if (e.type === 'chunk') patchLast((m) => ({ content: m.content + e.text }))
          else if (e.type === 'grounding') patchLast(() => ({ grounding: e }))
          else if (e.type === 'error') patchLast(() => ({ error: e.message }))
        },
        controller.signal,
      )
    } catch (err) {
      if (err.name !== 'AbortError') patchLast(() => ({ error: err.message }))
    } finally {
      setBusy(false)
      abort.current = null
    }
  }

  const ollamaProblem =
    health && !health.ollama.running
      ? 'Ollama is not running. Answers need it. Start it with "ollama serve".'
      : health && !health.ollama.model_available
        ? `The model ${health.ollama.model} is not installed. Run "ollama pull ${health.ollama.model}".`
        : ''

  return (
    <section className="chat" aria-label="Conversation">
      <div className="thread" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty">
            <h2>{hasDocuments ? 'Ask your notes' : 'No notes in this collection yet'}</h2>
            {hasDocuments ? (
              <>
                <p>
                  Ordinary questions are answered only from your notes, with the passages they came from. Ask to
                  explain, or for an example, and Mnemo goes beyond them and says so.
                </p>
                <ul>
                  {EXAMPLES.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Upload a PDF, TXT or MD file from the left. Scanned PDFs without text can't be read.</p>
            )}
          </div>
        )}
        {loadError && <p className="error">{loadError}</p>}
        {messages.map((m, i) => (
          <Message key={m.id} message={m} onCite={onCite} streaming={busy && i === messages.length - 1} />
        ))}
        <div ref={endRef} />
      </div>

      {ollamaProblem && <p className="banner">{ollamaProblem}</p>}
      <form className="composer" onSubmit={send}>
        <label htmlFor="q" className="sr-only">
          Your question
        </label>
        <textarea
          id="q"
          rows={1}
          value={input}
          maxLength={2000}
          placeholder={`Ask about ${collection.name}`}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) send(e)
          }}
        />
        {busy ? (
          <button type="button" className="secondary" onClick={() => abort.current?.abort()}>
            Stop
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()}>
            Ask
          </button>
        )}
      </form>
    </section>
  )
}
