# Mnemo — Project Specification

## What is Mnemo

Mnemo is a personal knowledge chatbot built on Retrieval-Augmented Generation (RAG). It lets a user (primarily students, but usable by anyone) upload their own notes, journals, lecture PDFs, or documents, and then ask natural-language questions about that content. Unlike generic AI chatbots (ChatGPT, Claude, Gemini), Mnemo's core value is that it answers **grounded in the user's own material first**, with clear transparency about what came from their notes versus what came from general knowledge.

### The core problem it solves
Big LLMs don't have access to a user's private notes, can't guarantee they aren't hallucinating even when notes are pasted in, and don't cleanly distinguish between "this is what you wrote" and "this is general knowledge I'm adding." Mnemo solves this by explicitly separating two response modes and citing sources for grounded claims.

### How it works (conceptually)
1. User uploads notes (text, markdown, PDF).
2. Documents are split into chunks and converted into vector embeddings.
3. Embeddings are stored in a vector database.
4. When the user asks a question, Mnemo retrieves the most relevant chunks from their own notes.
5. **Recall Mode**: if the question is answerable from the notes, Mnemo answers strictly from the retrieved content and cites the exact source (file name, date/section).
6. **Elaboration Mode**: if the user asks a follow-up like "explain more" or "give an example," Mnemo clearly labels the response as going beyond the notes and uses general knowledge (either from a local LLM or a cloud LLM API) to explain further — while still showing what the original notes said for continuity.
7. Every answer visually indicates which mode it came from, so the user always knows what's a grounded fact versus a generated explanation.

### Example use cases
- A student asking "what did my notes say about backpropagation vs gradient descent?" then following up with "explain more elaborately with an example."
- Someone journaling and asking "how did I feel about my job around March 2024?" with the bot citing the exact entry and date.
- A professional searching meeting notes: "what did we decide about the Q2 pricing model?"
- Searching a personal recipe collection for something described vaguely rather than by exact name.

---

## Tech Stack

### Frontend
- **React** (with **Vite** as the build tool — not Create React App)
- **Tailwind CSS** for styling
- **Framer Motion** for animations and micro-interactions (upload progress, thinking indicators, streaming text, fade-ins)
- **Axios** or native `fetch` for API calls to the backend
- State management via React's built-in `useState`/`useContext` (no Redux needed at this scale)

### Backend
- **Python** with **FastAPI** (async-friendly, auto-generates API docs, integrates cleanly with ML libraries)
- **Pydantic** for request/response validation (comes with FastAPI)
- CORS middleware configured to allow the React frontend origin

### AI / ML Components
- **Embeddings**: `sentence-transformers` library, using the `all-MiniLM-L6-v2` model — small, fast, runs well on CPU, good semantic quality for short-to-medium text chunks.
- **Vector Database**: **ChromaDB** — runs embedded within the Python backend, no separate server needed for local/small-scale use. (For future hosted/scaled version: Pinecone, Weaviate Cloud, or Supabase pgvector.)
- **Local LLM runtime**: **Ollama**, running a small quantized model:
  - `phi3:mini` (~3.8B params, ~2.3GB) — good balance of speed and quality on modest hardware.
  - Alternative: `llama3.2:3b`.
- **Optional cloud LLM (for Elaboration Mode, if local model quality is insufficient)**: Claude API (e.g., Claude Haiku) or OpenAI API (e.g., GPT-4o-mini) — used only for the "beyond your notes" explanation layer, kept separate from the private/local Recall Mode pipeline.
- **Document parsing**: `pypdf` or `pdfplumber` for PDF text extraction; plain file reading for `.txt`/`.md`.
- **Chunking**: custom or LangChain-style recursive text splitter, ~300 words per chunk with slight overlap (~50 words) to preserve context across chunk boundaries.
- **Intent/mode detection**: a lightweight classification step (either a simple keyword/phrase heuristic, or a single LLM call) to decide whether an incoming query is a Recall-type question or an Elaboration-type follow-up.
- **(Optional, advanced) Verification layer**: an NLI-based check (e.g., a pretrained `DeBERTa-MNLI` model) to confirm that Recall Mode answers are actually entailed by the retrieved chunks, catching hallucination even in grounded mode.

### Languages
- **Python** — backend, all AI/ML logic, embedding generation, retrieval, LLM orchestration.
- **JavaScript / JSX** — frontend, React components, UI logic, animations.
- **HTML/CSS** — underlying structure and styling (via JSX and Tailwind utility classes).
- **SQL** (optional, later) — if using a relational database (e.g., Postgres/Supabase) for user accounts, chat history, or metadata once the project grows beyond local single-user use.

---

## System Architecture (data flow)

```
User uploads notes (PDF/txt/md)
        ↓
[Document Parser] → extract raw text
        ↓
[Chunker] → split into ~300-word overlapping chunks
        ↓
[Embedding Model: all-MiniLM-L6-v2] → convert each chunk to a vector
        ↓
[ChromaDB] → store vector + text + metadata (filename, date)

--- at query time ---

User question
        ↓
[Mode Detector] → Recall or Elaboration?
        ↓
[Embed question] → same embedding model
        ↓
[ChromaDB similarity search] → top-k relevant chunks retrieved
        ↓
   ┌─────────────────────┬─────────────────────────┐
   │   Recall Mode        │   Elaboration Mode        │
   │ Answer ONLY from      │ Show notes context, then  │
   │ retrieved chunks,     │ generate broader          │
   │ cite source           │ explanation, clearly       │
   │ (local Ollama LLM)    │ labeled "beyond your      │
   │                       │ notes" (local or cloud     │
   │                       │ LLM)                       │
   └─────────────────────┴─────────────────────────┘
        ↓
Answer + citations + mode label returned to frontend
        ↓
React chat UI renders response with badge + source tags
```

---

## UI / UX Design

### Overall aesthetic
Clean, minimal, flat design similar in spirit to modern chat products (ChatGPT-familiar layout so no learning curve), but with a warmer, slightly more playful personality suited to students — not sterile or corporate. No gradients, drop shadows, or heavy visual noise. Generous whitespace. Two-column layout: sidebar + main chat.

### Layout
- **Sidebar (left, ~220px)**: app logo/name, "New chat" button, list of recent conversations, a "Sources" section showing indexed note collections with chunk counts, and an "Upload notes" button.
- **Main chat panel**: message thread (user messages right-aligned in a muted bubble, assistant responses left-aligned as plain text blocks), input box pinned at the bottom.

### Key UI elements specific to Mnemo
- **Mode badges**: every assistant response is tagged with a small pill label — *"From your notes"* (accent color) for Recall Mode, *"Beyond your notes"* (neutral gray) for Elaboration Mode. This is the single most important UI element, since it makes the grounding/trust mechanism visible rather than hidden.
- **Source citations**: small muted text under grounded answers showing file name and date/section (e.g., `Lecture_5.md · Oct 3`).
- **"Verify against your notes/syllabus" button**: appears under Elaboration Mode answers as a small trust-building nudge.

### Micro-interactions / animations
- **Upload flow**: drag-and-drop zone with a spinner, live status text ("Reading Lecture_5.pdf..."), a progress bar, and a completion checkmark with a summary ("42 new chunks indexed").
- **Thinking indicator**: animated bouncing-dots loader paired with rotating status text ("Digging through your notes..." → "Cross-checking dates..." → "Almost there...") instead of a static spinner, to make retrieval/generation latency feel intentional.
- **Streaming responses**: assistant answers stream in word-by-word (like ChatGPT) rather than appearing all at once, implemented with Framer Motion or simple incremental state updates.
- **Empty states**: friendly and inviting rather than apologetic (e.g., "Your second brain is empty" with an upload prompt), avoiding generic "No data found" messaging.
- **Subtle hover/reveal effects**: citation tags can expand slightly on hover to preview the cited text.
- Implementation library: **Framer Motion** for all transitions, fades, and staggered animations in React.

### Design tokens (for consistency)
- Colors: one accent color (e.g., blue) reserved for "grounded/Recall" state, neutral gray for "general/Elaboration" state — kept to a minimal palette so the mode distinction reads instantly.
- Typography: sans-serif UI font throughout, sentence case for all labels/buttons, two font weights only (regular/medium) to keep it light and modern.
- Corners: consistently rounded (8–12px radius) for cards, inputs, and buttons.
- No emoji in UI copy; icons via a consistent outline icon set (e.g., Tabler icons) for actions like upload, folder, check, send.

---

## Suggested Build Order
1. Backend: file ingestion + chunking + embedding + ChromaDB storage (test via API docs/Swagger UI).
2. Backend: retrieval endpoint + Ollama integration for Recall Mode.
3. Backend: mode detection + Elaboration Mode logic.
4. Frontend: basic chat UI wired to backend (no animations yet).
5. Frontend: mode badges, citations, empty states.
6. Frontend: animations and micro-interactions (upload progress, thinking indicator, streaming text).
7. Polish: file management UI, multiple note collections, chat history persistence.
