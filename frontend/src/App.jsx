import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import Chat from './components/Chat'
import Sidebar from './components/Sidebar'
import { DocumentPanel, SourcePanel } from './components/SidePanel'

export default function App() {
  const [collections, setCollections] = useState([])
  const [collectionId, setCollectionId] = useState(() => localStorage.getItem('mnemo.collection'))
  const [documents, setDocuments] = useState([])
  const [chats, setChats] = useState([])
  const [chatId, setChatId] = useState(null)
  const [chatKey, setChatKey] = useState(0)
  const [source, setSource] = useState(null)
  const [viewDoc, setViewDoc] = useState(null)
  const [health, setHealth] = useState(null)
  const [status, setStatus] = useState({ uploading: false, message: '', error: false })
  const [fatal, setFatal] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)

  const collection = collections.find((c) => c.id === collectionId) || collections[0]

  const refreshCollections = useCallback(async () => {
    try {
      const list = await api.collections()
      setCollections(list)
      setCollectionId((id) => (list.some((c) => c.id === id) ? id : list[0]?.id))
      setFatal('')
    } catch (e) {
      setFatal(e.message)
    }
  }, [])

  const refreshCollection = useCallback(async (id) => {
    try {
      const [docs, chatList] = await Promise.all([api.documents(id), api.chats(id)])
      setDocuments(docs)
      setChats(chatList)
    } catch (e) {
      setFatal(e.message)
    }
  }, [])

  useEffect(() => {
    refreshCollections()
    api.health().then(setHealth).catch(() => {})
  }, [refreshCollections])

  useEffect(() => {
    if (!collection) return
    localStorage.setItem('mnemo.collection', collection.id)
    refreshCollection(collection.id)
  }, [collection?.id, refreshCollection])

  const resetView = () => {
    setChatId(null)
    setChatKey((k) => k + 1)
    setSource(null)
    setViewDoc(null)
  }

  const selectCollection = (id) => {
    setCollectionId(id)
    resetView()
    setMenuOpen(false)
  }

  const createCollection = async (name) => {
    try {
      const created = await api.createCollection(name)
      await refreshCollections()
      selectCollection(created.id)
    } catch (e) {
      setStatus({ uploading: false, message: e.message, error: true })
    }
  }

  const deleteCollection = async (c) => {
    if (!window.confirm(`Delete the collection "${c.name}", its notes and its chats?`)) return
    try {
      await api.deleteCollection(c.id)
      resetView()
      await refreshCollections()
    } catch (e) {
      setStatus({ uploading: false, message: e.message, error: true })
    }
  }

  const upload = async (file) => {
    setStatus({ uploading: true, message: '', error: false })
    try {
      const doc = await api.upload(collection.id, file)
      setStatus({ uploading: false, message: `${doc.filename}: ${doc.chunk_count} ${doc.chunk_count === 1 ? 'passage' : 'passages'} indexed.`, error: false })
      await Promise.all([refreshCollection(collection.id), refreshCollections()])
    } catch (e) {
      setStatus({ uploading: false, message: `${file.name}: ${e.message}`, error: true })
    }
  }

  const deleteDocument = async (doc) => {
    if (!window.confirm(`Remove ${doc.filename} from this collection?`)) return
    try {
      await api.deleteDocument(collection.id, doc.id)
      if (viewDoc?.id === doc.id) setViewDoc(null)
      await Promise.all([refreshCollection(collection.id), refreshCollections()])
    } catch (e) {
      setStatus({ uploading: false, message: e.message, error: true })
    }
  }

  const deleteChat = async (chat) => {
    try {
      await api.deleteChat(chat.id)
      if (chat.id === chatId) resetView()
      refreshCollection(collection.id)
    } catch (e) {
      setStatus({ uploading: false, message: e.message, error: true })
    }
  }

  if (fatal && !collection) {
    return (
      <main className="fatal">
        <h1>Mnemo</h1>
        <p className="error">{fatal}</p>
        <button onClick={refreshCollections}>Try again</button>
      </main>
    )
  }
  if (!collection) return <main className="fatal"><p className="muted">Loading...</p></main>

  return (
    <div className={`app ${menuOpen ? 'menu-open' : ''}`}>
      <button className="menu-toggle secondary" onClick={() => setMenuOpen((o) => !o)} aria-expanded={menuOpen}>
        {menuOpen ? 'Close menu' : 'Menu'}
      </button>
      <Sidebar
        collections={collections}
        collection={collection}
        documents={documents}
        chats={chats}
        chatId={chatId}
        viewDocId={viewDoc?.id}
        status={status}
        onSelectCollection={selectCollection}
        onCreateCollection={createCollection}
        onDeleteCollection={deleteCollection}
        onUpload={upload}
        onDeleteDocument={deleteDocument}
        onViewDocument={(d) => {
          setViewDoc(d)
          setSource(null)
          setMenuOpen(false)
        }}
        onNewChat={() => {
          resetView()
          setMenuOpen(false)
        }}
        onSelectChat={(id) => {
          setChatId(id)
          setChatKey((k) => k + 1)
          setSource(null)
          setViewDoc(null)
          setMenuOpen(false)
        }}
        onDeleteChat={deleteChat}
      />
      <main className="main">
        {fatal && <p className="banner">{fatal}</p>}
        <Chat
          key={`${collection.id}-${chatKey}`}
          collection={collection}
          chatId={chatId}
          hasDocuments={documents.length > 0}
          health={health}
          onChatCreated={(id) => {
            setChatId(id)
            refreshCollection(collection.id)
          }}
          onCite={(s) => {
            setSource(s)
            setViewDoc(null)
          }}
        />
      </main>
      {source && <SourcePanel source={source} onClose={() => setSource(null)} />}
      {viewDoc && <DocumentPanel collectionId={collection.id} doc={viewDoc} onClose={() => setViewDoc(null)} />}
    </div>
  )
}
