# Overnight fixes: Mnemo

## What was broken (audit of the original code)

I ran the original backend and uploaded a real PDF (`MODULE 5 CG.pdf`, 15 chunks) and asked questions in both modes.

Backend
- Uploading the same file twice indexed it twice (30 chunks for a 15 chunk file). Answers then cite duplicates.
- Upload saved the file to disk before checking anything. Wrong type, an empty file or a broken PDF left the file behind. An empty PDF gave the raw library error "No /Root object! - Is this really a PDF?". No size limit. A scanned PDF with no text would index zero chunks and report success.
- When Ollama wasn't running, the "Sorry, I am unable to connect..." text was streamed as if it were the model's answer, shown with a mode badge, and saved into the chat history as an assistant message. A missing model was not detected at all.
- Retrieval always returned the 3 nearest chunks, however unrelated. Recall mode therefore "answered" off-topic questions from irrelevant text, and cited the file anyway.
- Mode detection was a substring match: "show" matched "how", "moreover" matched "more", "somehow" and so on. "How many pages does it have?" went to Elaboration.
- Citations were file names only. You could not see which passage an answer came from.
- Chat messages were ordered by a one-second timestamp, so messages written in the same second could swap places.
- Everything lived in one global Chroma collection and one list of files: no way to keep subjects apart. Files were listed from the uploads folder, not from what was indexed.
- CORS origins, Ollama URL, model name and paths were hardcoded (model `llama3.1`, no tag).
- No tests. Internal exception text (`str(e)`) was returned to the client as the 500 detail.
- Dead comments describing old bug fixes ("BUGFIX: ...") all over the code.
- No grounding check: nothing verified that a Recall answer was supported by the notes.

Frontend
- API URL `http://localhost:8000` hardcoded in 10 places.
- Upload errors showed "Oops, that upload popped!" whatever the cause. Query errors showed a generic message.
- Mascot, bouncing animations, gradients and "Yum!" copy. Text bubbles at `whitespace-pre-wrap` with no citation interaction.
- Loads fonts from Google at runtime.
- Dead template files (Vite/React logos, hero.png, icons.svg, App.css, template README).

## What I changed

Commits on branch `overnight-fixes`: `7641510` (audit), `b92056b` (backend), `abcaf00` (grounding windows, eval, threshold), `491405f` (front end), plus the README and this file in the last commit.

Backend (`b92056b`, `abcaf00`)
- Split the old two big files into `main.py` (routes), `rag.py` (query flow), `llm.py` (Ollama), `grounding.py`, `ingestion.py`, `modes.py`, `vector_store.py`, `database.py`, `config.py`. Removed `llm_orchestrator.py`, `models.py` and the "BUGFIX" comments.
- Upload validation: extension, 20 MB limit (streamed, so a huge file is cut off early), PDF header, empty file, scanned or empty PDF ("no readable text, probably a scan, no OCR"), damaged or password PDF, non UTF-8 text, duplicate filename (409). Failed uploads leave no file or vectors behind. Filenames are flattened to a base name.
- Ollama down, model missing, timeout, dropped connection: each gives a specific `error` event the UI shows. Nothing is saved as an assistant answer for these. `/health` reports Ollama and model status. The model is `OLLAMA_MODEL`, default `llama3.1:8b`.
- Streaming: errors inside the stream become error events, a closed connection keeps the partial answer, the Ollama response is always closed.
- CORS only for `MNEMO_FRONTEND_ORIGINS`, only GET/POST/DELETE, no credentials. All config from env with `.env.example`. No hardcoded paths. Data lives in `backend/data/`.
- Mode detection uses word boundaries, so "show", "moreover", "somehow" no longer trigger Elaboration, and "how many/much/long" stays Recall.
- Recall now refuses ("Your notes don't cover this.") when no chunk reaches the similarity threshold, without calling the model. Sources are numbered passages with their text and score, so citations can be opened.
- Grounding check with an NLI cross-encoder (`nli-deberta-v3-xsmall`), word-overlap fallback, result stored with the message.
- Separate collections (own Chroma collection, uploads, chats). Chat messages ordered by id.

Front end (`491405f`)
- Rewrote it with plain CSS. Removed Tailwind, Framer Motion, lucide, axios, the mascot, gradients, Google Fonts and the template leftovers. Calm reading layout (serif body for answers), one accent colour, light and dark by system setting, keyboard reachable controls, a menu drawer at 390 px.
- Clickable citation numbers open the passage in a side panel. Mode badge on every answer. Flagged sentences are highlighted with "not found in your notes". Upload, indexing, error, empty and "Ollama not running" states are real states with real messages. Collections can be created, switched and deleted. Notes can be viewed as extracted text.
- Checked at 1440 px and 390 px with Playwright and Edge: no horizontal scroll at either, no page errors. Screenshots in `docs/screenshots/`. I did not capture a "before" screenshot of the old interface.

## Results

- `pytest` in `backend/`: 63 passed (chunking, mode detection, retrieval threshold, grounding, upload validation, API routes, CORS, collections, chat history). The LLM, embedder and NLI model are faked in these tests. The real embedding model and the real NLI model were run separately, see below.
- End to end with real models on CPU, real PDF (a 15 chunk lecture PDF of Ganesh's, not committed) and `qwen2.5:0.5b`: upload, retrieval, streamed Recall and Elaboration answers, refusal on unrelated questions, grounding check, error events when Ollama is unreachable (`OLLAMA_URL` pointed at a dead port) and when the model is missing (`llama3.1:8b` not installed). All behaved.
- Grounding check on my 48 hand-written sentences: NLI 0.94 accuracy, word overlap 0.71. Small, self-written, tuned after one failure on a real sentence, so optimistic. Details in the README.
- Retrieval scores with all-MiniLM-L6-v2, best chunk per question: about 0.52 to 0.75 for on-topic questions on a 15 chunk PDF, 0.22 to 0.49 on a one-chunk note, under 0.15 for unrelated questions, 0.30 for "what is clipping" against animation notes. Default threshold 0.2.

## Still not done / didn't work

- Real answer quality with Llama 3.1 8B was not tested. I pulled only `qwen2.5:0.5b` (about 400 MB) to run the pipeline, to stay in the download budget. Citation style, refusal behaviour and Elaboration structure ("Beyond your notes:") depend on the model following the prompt, and a 0.5B model does that badly. Expect to tune the prompts with the real model.
- The NLI check was never run on real Llama output.
- The chat history is not given to the model, only used to widen the retrieval query for short follow-ups.
- 300 word chunks dilute similarity. Small facts inside long mixed chunks can be missed. Smaller chunks would help but change the spec; I left it.
- Old local data is not migrated. The previous `backend/mnemo.db`, `chroma_db/` and `uploads/` are untouched (and git-ignored). The new version uses `backend/data/`, so re-upload your PDFs.
- No OCR, no cloud model option from the spec, no animations (the spec's Framer Motion ideas were dropped on purpose), no "verify against your notes" button (the Elaboration footer says it in text).
- `npm audit` reports advisories I did not look into.

## Check yourself

- Pull `llama3.1:8b` and ask real questions in both modes. See if it cites as [1], whether flags look sensible, and whether the refusal threshold (0.2) feels right for your notes. Adjust `MNEMO_MIN_SIMILARITY` and `MNEMO_NLI_THRESHOLD`.
- Try your own PDFs, especially ones with tables or two columns.
- Try the interface on your phone against the backend on your laptop (set `MNEMO_FRONTEND_ORIGINS` and `VITE_API_URL`).
- The dark theme (follows the system setting) was not looked at by me. The layout was checked only in Edge.
