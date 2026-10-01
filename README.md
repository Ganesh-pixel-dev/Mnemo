# Mnemo

A chatbot that answers questions from **your own notes**. Upload lecture PDFs, notes or documents, ask in plain language, and Mnemo answers from your material and shows which file the answer came from.

Unlike a general chatbot, it keeps a clear line between "what your notes say" and "extra explanation from the model".

## Two answer modes

| Mode | When | What you get |
|---|---|---|
| **Recall** | Normal questions | Answer only from your uploaded notes, with the source file cited |
| **Elaboration** | You ask to "explain", give an "example", "why", "how"… | A longer explanation using the model's general knowledge, clearly labelled as going beyond your notes |

Every answer shows a badge for the mode it came from.

## How it works (RAG)

1. **Upload:** PDFs are read with pdfplumber.
2. **Chunk:** text is split into ~300-word pieces with a 50-word overlap, so ideas aren't cut in half.
3. **Embed:** each chunk becomes a vector with `all-MiniLM-L6-v2` (sentence-transformers).
4. **Store:** vectors go into ChromaDB on disk.
5. **Ask:** your question is embedded, the closest chunks are retrieved, and they're sent with the question to a local Llama 3.1 model (via Ollama).
6. **Stream:** the answer streams back word by word; chats are saved in SQLite.

Everything runs on your own machine. Your notes never leave it.

## Tech stack

| Part | Tools |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Framer Motion |
| Backend | Python, FastAPI, Pydantic |
| RAG | ChromaDB, sentence-transformers, pdfplumber |
| LLM | Llama 3.1 8B through Ollama (local) |

## Run it locally

You need Python, Node.js and [Ollama](https://ollama.com).

```bash
ollama pull llama3.1

git clone https://github.com/Ganesh-pixel-dev/Mnemo.git
cd Mnemo/backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# in a second terminal
cd Mnemo/frontend
npm install
npm run dev
```

Open the address Vite prints (usually http://localhost:5173).

## API

| Method | Path | Does |
|---|---|---|
| POST | `/upload` | Upload and index a file |
| GET / DELETE | `/files`, `/files/{name}` | List, view or remove uploaded files |
| POST | `/query` | Ask a question (streamed answer) |
| GET / POST / DELETE | `/chats`, `/chats/{id}` | Saved conversations |

Interactive docs at http://127.0.0.1:8000/docs while the backend is running.

The full design is in [mnemo-project-spec.md](mnemo-project-spec.md).
