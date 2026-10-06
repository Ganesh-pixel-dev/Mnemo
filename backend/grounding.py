"""Check each sentence of a Recall answer against the passages it was supposed to come from.

Primary check: a small NLI cross-encoder. Premise is a window of a retrieved passage,
hypothesis is the answer sentence, and the sentence counts as supported when the
entailment probability reaches the threshold in at least one window.

Fallback when the NLI model can't be loaded: the share of the sentence's content words
that appear in the best-matching window.
"""

import re
from dataclasses import asdict, dataclass

CITATION = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an the of to in on at by for with from and or but if then so as is are was were be been being it its this that these "
    "those there their they them he she his her we you i our your not no do does did done has have had can could will would "
    "should may might also than into about over under which who whom what when where how why".split()
)
MAX_WINDOW_WORDS = 60
WINDOWS_PER_SENTENCE = 3
LEXICAL_THRESHOLD = 0.6
REFUSALS = ("your notes don't cover this", "your notes do not cover this", "i cannot answer")


@dataclass
class SentenceVerdict:
    text: str
    supported: bool
    score: float
    source: int | None  # index into the retrieved passages that supported it

    def to_dict(self) -> dict:
        return asdict(self)


def split_sentences(answer: str) -> list[str]:
    sentences = []
    for block in re.split(r"\n+", answer):
        block = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", block).strip()
        if block:
            sentences.extend(s.strip() for s in SENTENCE_END.split(block) if s.strip())
    return sentences


def content_words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 1}


def is_refusal(text: str) -> bool:
    lowered = text.strip().lower().replace("’", "'")
    return lowered.startswith(REFUSALS)


def windows(text: str) -> list[str]:
    """Short premises: each sentence, and each pair of neighbouring sentences.

    The NLI model scored a verbatim sentence at 0.11 against a 120 word premise and 0.70 against
    the first 40 words, so long premises are avoided. Runs of text with no sentence ends are cut
    into pieces of at most MAX_WINDOW_WORDS words.
    """
    pieces = []
    for sentence in split_sentences(text):
        words = sentence.split()
        for start in range(0, len(words), MAX_WINDOW_WORDS):
            pieces.append(" ".join(words[start : start + MAX_WINDOW_WORDS]))
    out = list(pieces)
    for first, second in zip(pieces, pieces[1:]):
        if len(first.split()) + len(second.split()) <= MAX_WINDOW_WORDS:
            out.append(f"{first} {second}")
    return out or [text]


class NLIScorer:
    """Entailment probability for (premise, hypothesis) pairs. Loaded on first use."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._tokenizer = None
        self._model = None
        self._entail = None

    def load(self) -> None:
        if self._model is not None:
            return
        import torch  # noqa: F401
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).eval()
        labels = {int(i): str(l).lower() for i, l in self._model.config.id2label.items()}
        self._entail = next(i for i, l in labels.items() if l.startswith("entail"))

    def entailment(self, pairs: list[tuple[str, str]]) -> list[float]:
        import torch

        self.load()
        scores = []
        for start in range(0, len(pairs), 16):
            batch = pairs[start : start + 16]
            enc = self._tokenizer(
                [p for p, _ in batch],
                [h for _, h in batch],
                truncation="only_first",
                max_length=512,
                padding=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                probs = torch.softmax(self._model(**enc).logits, dim=-1)
            scores.extend(probs[:, self._entail].tolist())
        return scores


class Grounder:
    def __init__(self, scorer=None, threshold: float = 0.5):
        self.scorer = scorer
        self.threshold = threshold
        self.method = "nli" if scorer is not None else "lexical"

    def check(self, answer: str, passages: list[str]) -> list[SentenceVerdict]:
        """Verdicts for each checkable sentence of `answer`. Refusals and fragments are skipped."""
        sentences = [s for s in split_sentences(answer) if not is_refusal(s)]
        sentences = [(s, CITATION.sub("", s).strip()) for s in sentences]
        sentences = [(raw, clean) for raw, clean in sentences if len(clean.split()) >= 3]
        if not sentences:
            return []

        wins = [(i, w) for i, passage in enumerate(passages) for w in windows(passage)]
        verdicts = []
        for raw, clean in sentences:
            wanted = content_words(clean)
            ranked = sorted(wins, key=lambda iw: -self._overlap(wanted, iw[1]))
            best = ranked[:WINDOWS_PER_SENTENCE]
            if not best:
                verdicts.append(SentenceVerdict(raw, False, 0.0, None))
                continue
            if self.scorer is not None:
                scores = self.scorer.entailment([(w, clean) for _, w in best])
                threshold = self.threshold
            else:
                scores = [self._overlap(wanted, w) for _, w in best]
                threshold = LEXICAL_THRESHOLD
            top = max(range(len(scores)), key=scores.__getitem__)
            verdicts.append(
                SentenceVerdict(raw, scores[top] >= threshold, round(scores[top], 3), best[top][0])
            )
        return verdicts

    @staticmethod
    def _overlap(wanted: set[str], window: str) -> float:
        if not wanted:
            return 0.0
        return len(wanted & content_words(window)) / len(wanted)
