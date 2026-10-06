export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {}

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(`${API}${path}`, options)
  } catch {
    throw new ApiError(`Can't reach the Mnemo backend at ${API}. Is it running?`)
  }
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status}).`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join('. ')
    } catch {}
    throw new ApiError(detail)
  }
  return res.json()
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => request('/health'),
  collections: () => request('/collections'),
  createCollection: (name) => request('/collections', json('POST', { name })),
  deleteCollection: (id) => request(`/collections/${id}`, { method: 'DELETE' }),
  documents: (cid) => request(`/collections/${cid}/documents`),
  upload: (cid, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/collections/${cid}/documents`, { method: 'POST', body: form })
  },
  deleteDocument: (cid, id) => request(`/collections/${cid}/documents/${id}`, { method: 'DELETE' }),
  documentText: (cid, id) => request(`/collections/${cid}/documents/${id}/text`),
  rawUrl: (cid, id) => `${API}/collections/${cid}/documents/${id}/raw`,
  chats: (cid) => request(`/collections/${cid}/chats`),
  createChat: (cid, title) => request(`/collections/${cid}/chats`, json('POST', { title })),
  deleteChat: (id) => request(`/chats/${id}`, { method: 'DELETE' }),
  messages: (id) => request(`/chats/${id}`),
}

// Streams a query. Calls onEvent for each server event. Resolves when the stream ends.
export async function streamQuery(body, onEvent, signal) {
  let res
  try {
    res = await fetch(`${API}/query`, { ...json('POST', body), signal })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError(`Can't reach the Mnemo backend at ${API}. Is it running?`)
  }
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status}).`
    try {
      const b = await res.json()
      if (typeof b.detail === 'string') detail = b.detail
    } catch {}
    throw new ApiError(detail)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop()
    for (const block of blocks) {
      if (!block.startsWith('data: ')) continue
      try {
        onEvent(JSON.parse(block.slice(6)))
      } catch {}
    }
  }
}
