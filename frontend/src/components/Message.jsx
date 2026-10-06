const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g
const BEYOND = 'Beyond your notes:'

function withCitations(text, sources, onCite, keyPrefix) {
  const parts = []
  let last = 0
  for (const match of text.matchAll(CITATION)) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    for (const n of match[1].split(',').map((s) => Number(s.trim()))) {
      const source = sources.find((s) => s.n === n)
      parts.push(
        source ? (
          <button
            key={`${keyPrefix}-${match.index}-${n}`}
            className="cite"
            onClick={() => onCite(source)}
            title={`${source.filename}, passage ${source.chunk_index + 1}`}
            aria-label={`Show source ${n}: ${source.filename}`}
          >
            {n}
          </button>
        ) : (
          `[${n}]`
        ),
      )
    }
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

// Cuts `content` into plain and flagged pieces using the sentences the grounding check rejected.
function splitFlagged(content, grounding) {
  if (!grounding) return [{ text: content, flagged: false }]
  const ranges = []
  for (const s of grounding.sentences) {
    if (s.supported) continue
    const start = content.indexOf(s.text)
    if (start >= 0) ranges.push([start, start + s.text.length, s.score])
  }
  ranges.sort((a, b) => a[0] - b[0])
  const pieces = []
  let at = 0
  for (const [start, end, score] of ranges) {
    if (start < at) continue
    if (start > at) pieces.push({ text: content.slice(at, start), flagged: false })
    pieces.push({ text: content.slice(start, end), flagged: true, score })
    at = end
  }
  if (at < content.length) pieces.push({ text: content.slice(at), flagged: false })
  return pieces
}

function Body({ content, grounding, sources, onCite }) {
  return splitFlagged(content, grounding).map((piece, i) =>
    piece.flagged ? (
      <mark key={i} className="flag" title={`Not supported by the cited passages (entailment ${piece.score})`}>
        {withCitations(piece.text, sources, onCite, i)}
        <span className="flag-note"> not found in your notes</span>
      </mark>
    ) : (
      <span key={i}>{withCitations(piece.text, sources, onCite, i)}</span>
    ),
  )
}

function Badge({ mode, refused }) {
  if (refused) return <span className="badge beyond">Not in your notes</span>
  if (mode === 'Recall') return <span className="badge recall">From your notes</span>
  if (mode === 'Elaboration') return <span className="badge beyond">Beyond your notes</span>
  return null
}

export default function Message({ message, onCite, streaming }) {
  if (message.role === 'user') {
    return (
      <div className="turn user">
        <p>{message.content}</p>
      </div>
    )
  }

  const { content, mode, sources = [], grounding, error } = message
  const split = mode === 'Elaboration' ? content.indexOf(BEYOND) : -1
  const refused = mode === 'Recall' && content.trim().toLowerCase().startsWith("your notes don't cover this")
  const unsupported = grounding ? grounding.sentences.filter((s) => !s.supported).length : 0

  return (
    <article className="turn assistant" aria-busy={streaming}>
      <header>
        <Badge mode={mode} refused={refused} />
        {mode === 'Recall' && !refused && sources.length > 0 && !streaming && (
          <span className="sources-line">
            {[...new Set(sources.map((s) => s.filename))].join(', ')}
          </span>
        )}
      </header>

      {!content && streaming && <p className="thinking">Searching your notes</p>}

      <div className="prose">
        {split >= 0 ? (
          <>
            <p>{withCitations(content.slice(0, split).trim(), sources, onCite, 'a')}</p>
            <p className="beyond-block">{content.slice(split).trim()}</p>
          </>
        ) : (
          <p>
            <Body content={content} grounding={grounding} sources={sources} onCite={onCite} />
          </p>
        )}
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {!streaming && mode === 'Recall' && grounding && (
        <footer className="check">
          {grounding.sentences.length === 0
            ? 'Nothing to check.'
            : unsupported === 0
              ? `Each sentence was checked against the cited passages and all ${grounding.sentences.length} look supported.`
              : `${unsupported} of ${grounding.sentences.length} sentences are not supported by the passages. They are marked.`}
          {grounding.method === 'lexical' && ' (Word-overlap check only: the NLI model was not available.)'}
        </footer>
      )}
      {!streaming && mode === 'Elaboration' && content && (
        <footer className="check">This answer goes beyond your notes and was not checked against them. Verify it yourself.</footer>
      )}
      {!streaming && mode === 'Elaboration' && sources.length > 0 && (
        <div className="source-chips">
          {sources.map((s) => (
            <button key={s.n} className="chip" onClick={() => onCite(s)}>
              <span className="cite static">{s.n}</span> {s.filename}
            </button>
          ))}
        </div>
      )}
    </article>
  )
}
