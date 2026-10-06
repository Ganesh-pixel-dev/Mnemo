import logging
from typing import Iterator

from grounding import Grounder, is_refusal
from llm import LLMError
from modes import ELABORATION, RECALL, detect_mode

log = logging.getLogger("mnemo")

NOT_COVERED = "Your notes don't cover this."

RECALL_SYSTEM = (
    "You answer questions using only the numbered passages from the user's own notes. "
    "After every claim, cite the passage it came from in square brackets, like [1]. "
    "Do not use outside knowledge. Keep the answer short and plain. "
    f"If the passages do not answer the question, reply with exactly: {NOT_COVERED}"
)

ELABORATION_SYSTEM = (
    "The user wants an explanation that goes further than their notes. "
    "Start with what the numbered passages say, citing them like [1]. "
    "Then write a new paragraph that begins with 'Beyond your notes:' and add general knowledge, "
    "examples or reasoning there. Never present general knowledge as coming from the notes."
)


def build_prompt(question: str, hits) -> str:
    passages = "\n\n".join(f"[{i + 1}] ({h.filename})\n{h.text}" for i, h in enumerate(hits))
    if not hits:
        passages = "(no passages from the notes matched this question)"
    return f"Passages:\n\n{passages}\n\nQuestion: {question}"


def source_payload(hits) -> list[dict]:
    return [{"n": i + 1, **h.to_dict()} for i, h in enumerate(hits)]


class QueryService:
    def __init__(self, settings, db, store, llm, grounder):
        self.settings = settings
        self.db = db
        self.store = store
        self.llm = llm
        self.grounder = grounder

    def retrieval_query(self, question: str, mode: str, chat_id: str | None) -> str:
        """A short follow-up like "explain more" has nothing to search for, so borrow the last question."""
        if mode == ELABORATION and chat_id and len(question.split()) < 8:
            earlier = [m["content"] for m in self.db.get_messages(chat_id) if m["role"] == "user"]
            if earlier:
                return f"{earlier[-1]} {question}"
        return question

    def stream(self, collection_id: str, question: str, chat_id: str | None = None) -> Iterator[dict]:
        mode = detect_mode(question)
        try:
            hits = self.store.search(
                collection_id,
                self.retrieval_query(question, mode, chat_id),
                self.settings.top_k,
                self.settings.min_similarity,
            )
        except Exception:
            log.exception("retrieval failed")
            yield {"type": "error", "code": "retrieval_failed", "message": "Searching your notes failed. Check the backend log."}
            return

        if chat_id:
            self.db.add_message(chat_id, "user", question)

        if mode == RECALL and not hits:
            yield {"type": "metadata", "mode": mode, "sources": []}
            yield {"type": "chunk", "text": NOT_COVERED}
            self._save(chat_id, NOT_COVERED, mode, [], None)
            yield {"type": "done"}
            return

        sources = source_payload(hits)
        yield {"type": "metadata", "mode": mode, "sources": sources}

        system = RECALL_SYSTEM if mode == RECALL else ELABORATION_SYSTEM
        answer = ""
        try:
            for piece in self.llm.stream(system, build_prompt(question, hits), 0.1 if mode == RECALL else 0.4):
                answer += piece
                yield {"type": "chunk", "text": piece}
        except LLMError as exc:
            if answer:
                self._save(chat_id, answer, mode, sources, None)
            yield {"type": "error", "code": exc.code, "message": exc.message}
            return
        except GeneratorExit:
            if answer:
                self._save(chat_id, answer, mode, sources, None)
            raise

        grounding = None
        if mode == RECALL and answer.strip() and not is_refusal(answer):
            grounding = self._ground(answer, [h.text for h in hits])
            yield {"type": "grounding", **grounding}

        self._save(chat_id, answer, mode, sources, grounding)
        yield {"type": "done"}

    def _ground(self, answer: str, passages: list[str]) -> dict:
        grounder = self.grounder
        try:
            verdicts = grounder.check(answer, passages)
        except Exception:
            log.exception("NLI check failed, using the lexical fallback")
            grounder = Grounder(None)
            verdicts = grounder.check(answer, passages)
        return {"method": grounder.method, "sentences": [v.to_dict() for v in verdicts]}

    def _save(self, chat_id, answer, mode, sources, grounding) -> None:
        if chat_id and answer.strip():
            self.db.add_message(chat_id, "assistant", answer, mode, sources, grounding)
