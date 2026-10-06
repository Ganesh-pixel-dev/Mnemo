import { useEffect, useState } from 'react'
import { api } from '../api'

export function SourcePanel({ source, onClose }) {
  return (
    <aside className="panel" aria-label="Source passage">
      <header>
        <div>
          <p className="label">Source {source.n}</p>
          <h2>{source.filename}</h2>
          <p className="muted">
            Passage {source.chunk_index + 1}, similarity {source.score.toFixed(2)}
          </p>
        </div>
        <button className="secondary" onClick={onClose}>
          Close
        </button>
      </header>
      <blockquote className="prose">{source.text}</blockquote>
    </aside>
  )
}

export function DocumentPanel({ collectionId, doc, onClose }) {
  const [text, setText] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setText(null)
    setError('')
    api
      .documentText(collectionId, doc.id)
      .then((d) => setText(d.content))
      .catch((e) => setError(e.message))
  }, [collectionId, doc.id])

  return (
    <aside className="panel" aria-label="Document text">
      <header>
        <div>
          <p className="label">Extracted text</p>
          <h2>{doc.filename}</h2>
          {doc.ext === '.pdf' && (
            <a href={api.rawUrl(collectionId, doc.id)} target="_blank" rel="noreferrer">
              Open original PDF
            </a>
          )}
        </div>
        <button className="secondary" onClick={onClose}>
          Close
        </button>
      </header>
      {error && <p className="error">{error}</p>}
      {text === null && !error && <p className="muted">Loading...</p>}
      {text !== null && <div className="prose doc-text">{text}</div>}
    </aside>
  )
}
