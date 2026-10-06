import { useRef, useState } from 'react'

export default function Sidebar({
  collections,
  collection,
  documents,
  chats,
  chatId,
  viewDocId,
  status,
  onSelectCollection,
  onCreateCollection,
  onDeleteCollection,
  onUpload,
  onDeleteDocument,
  onViewDocument,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}) {
  const fileInput = useRef(null)
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [dragging, setDragging] = useState(false)

  const submitName = (e) => {
    e.preventDefault()
    if (name.trim()) onCreateCollection(name.trim())
    setName('')
    setAdding(false)
  }

  const drop = (e) => {
    e.preventDefault()
    setDragging(false)
    for (const file of e.dataTransfer.files) onUpload(file)
  }

  return (
    <nav className="sidebar" aria-label="Collections, notes and chats">
      <h1 className="logo">Mnemo</h1>

      <div className="block">
        <label htmlFor="collection" className="label">
          Collection
        </label>
        <div className="row">
          <select id="collection" value={collection.id} onChange={(e) => onSelectCollection(e.target.value)}>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.document_count})
              </option>
            ))}
          </select>
          <button className="icon" onClick={() => setAdding(true)} aria-label="New collection" title="New collection">
            +
          </button>
          <button
            className="icon danger"
            aria-label={`Delete collection ${collection.name}`}
            title="Delete collection"
            onClick={() => onDeleteCollection(collection)}
          >
            x
          </button>
        </div>
        {adding && (
          <form onSubmit={submitName} className="row">
            <input autoFocus value={name} maxLength={60} placeholder="Collection name" onChange={(e) => setName(e.target.value)} />
            <button type="submit">Add</button>
          </form>
        )}
      </div>

      <div className="block">
        <h2 className="label">Notes</h2>
        <ul className="list">
          {documents.map((d) => (
            <li key={d.id} className={viewDocId === d.id ? 'active' : ''}>
              <button className="item" onClick={() => onViewDocument(d)} title={`${d.chunk_count} passages`}>
                {d.filename}
                <small>{d.chunk_count} {d.chunk_count === 1 ? 'passage' : 'passages'}</small>
              </button>
              <button className="icon danger" aria-label={`Delete ${d.filename}`} onClick={() => onDeleteDocument(d)}>
                x
              </button>
            </li>
          ))}
          {documents.length === 0 && <li className="muted">Nothing uploaded.</li>}
        </ul>
        <div
          className={`drop ${dragging ? 'over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={drop}
        >
          <button className="secondary" disabled={status.uploading} onClick={() => fileInput.current.click()}>
            {status.uploading ? 'Reading and indexing...' : 'Upload notes'}
          </button>
          <span className="muted">PDF, TXT or MD. Drop files here.</span>
          <input
            ref={fileInput}
            type="file"
            hidden
            multiple
            accept=".pdf,.txt,.md"
            onChange={(e) => {
              for (const file of e.target.files) onUpload(file)
              e.target.value = ''
            }}
          />
        </div>
        {status.message && (
          <p className={status.error ? 'error' : 'ok'} role="status">
            {status.message}
          </p>
        )}
      </div>

      <div className="block grow">
        <div className="row spread">
          <h2 className="label">Chats</h2>
          <button className="link" onClick={onNewChat}>
            New chat
          </button>
        </div>
        <ul className="list">
          {chats.map((c) => (
            <li key={c.id} className={chatId === c.id && !viewDocId ? 'active' : ''}>
              <button className="item" onClick={() => onSelectChat(c.id)}>
                {c.title}
              </button>
              <button className="icon danger" aria-label={`Delete chat ${c.title}`} onClick={() => onDeleteChat(c)}>
                x
              </button>
            </li>
          ))}
          {chats.length === 0 && <li className="muted">No chats yet.</li>}
        </ul>
      </div>
    </nav>
  )
}
