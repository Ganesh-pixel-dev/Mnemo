# Overnight fixes: Mnemo

## What was broken (audit of the original code)

I ran the original backend and uploaded a real PDF (`MODULE 5 CG.pdf`, 15 chunks) and asked questions in both modes.

Backend
- Uploading the same file twice indexed it twice (30 chunks for a 15 chunk file). Answers then cite duplicates.
- Upload saved the file to disk before checking anything. Wrong type, an empty file or a broken PDF left the file behind. An empty PDF gave the raw library error "No /Root object! - Is this really a PDF?". No size limit. A scanned PDF with no text would index zero chunks and report success.
- When Ollama wasn't running, the "Sorry, I am unable to connect..." text was streamed as if it were the model's answer, shown with a mode badge, and saved into the chat history as an assistant message. A missing model was not detected at all.
- Retrieval always returned the 3 nearest chunks, however unrelated. Recall mode therefore "answered" off-topic questions from irrelevant text, and cited the file anyway.
- Mode detection was a substring match: "show" matched "how", "moreover" matched "more", "somehow", "whywhy" and so on. "How many pages does it have?" went to Elaboration.
- Citations were file names only. You could not see which passage an answer came from.
- Chat messages were ordered by a one-second timestamp, so messages written in the same second could swap places.
- Everything lived in one global Chroma collection and one list of files: no way to keep subjects apart. Files were listed from the uploads folder, not from what was indexed.
- CORS origins, Ollama URL, model name and paths were hardcoded (model `llama3.1`, no tag).
- No tests. The stack trace of any internal error was returned to the client as the 500 detail.
- Dead comments describing old bug fixes ("BUGFIX: ...") all over the code.
- No grounding check: nothing verified that a Recall answer was supported by the notes.

Frontend
- API URL `http://localhost:8000` hardcoded in 10 places.
- Upload errors showed "Oops, that upload popped!" whatever the cause. Query errors showed a generic message.
- Mascot, bouncing animations, gradients and "Yum!" copy. Text bubbles at `whitespace-pre-wrap` with no citation interaction.
- Loads fonts from Google at runtime.
- Dead template files (Vite/React logos, hero.png, icons.svg, App.css, template README).

Not a bug but worth knowing: the spec calls for phi3/llama3.2, the code uses Llama 3.1 8B. README is right about the code on that point.
