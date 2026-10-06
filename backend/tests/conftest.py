import hashlib
import json
import math
import re

import pytest
from fastapi.testclient import TestClient

from config import Settings
from main import create_app

WORD = re.compile(r"[a-z0-9]+")


class FakeEmbedder:
    """Hashed bag of words. Cosine similarity then tracks word overlap, enough to test retrieval logic."""

    dim = 256

    def encode(self, texts):
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for word in WORD.findall(text.lower()):
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class FakeLLM:
    def __init__(self):
        self.reply = "Gradient descent updates weights step by step [1]."
        self.error = None
        self.calls = []

    def stream(self, system, prompt, temperature=0.1):
        self.calls.append({"system": system, "prompt": prompt})
        if self.error:
            raise self.error
        for word in self.reply.split(" "):
            yield word + " "

    def status(self):
        return {"running": True, "model": "fake", "model_available": True}


class OverlapScorer:
    """Stands in for the NLI model: 0.9 when most hypothesis words are in the premise, else 0.1."""

    def entailment(self, pairs):
        scores = []
        for premise, hypothesis in pairs:
            wanted = set(WORD.findall(hypothesis.lower()))
            have = set(WORD.findall(premise.lower()))
            scores.append(0.9 if wanted and len(wanted & have) / len(wanted) > 0.7 else 0.1)
        return scores


def make_pdf(text: str) -> bytes:
    """A minimal one-page PDF with `text` as wrapped Helvetica lines."""
    lines, line = [], ""
    for w in text.split():
        if len(line) + len(w) > 80:
            lines.append(line)
            line = ""
        line = f"{line} {w}".strip()
    lines.append(line)
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    body = "BT /F1 10 Tf 40 760 Td 12 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines if l) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


NOTES = (
    "Gradient descent is an optimisation method. It updates the weights of a model a little at a time "
    "in the direction that lowers the loss. The learning rate controls the size of each step. "
    "Backpropagation computes the gradient of the loss with respect to every weight by applying the chain rule "
    "backwards through the layers of the network. "
) * 3


def parse_sse(response) -> list[dict]:
    return [json.loads(b[6:]) for b in response.text.split("\n\n") if b.startswith("data: ")]


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def client(tmp_path, llm):
    settings = Settings(data_dir=tmp_path / "data", max_upload_mb=1, min_similarity=0.1)
    app = create_app(settings, embedder=FakeEmbedder(), llm=llm, scorer=OverlapScorer())
    with TestClient(app) as c:
        yield c


@pytest.fixture
def collection_id(client):
    return client.get("/collections").json()[0]["id"]


@pytest.fixture
def notes_doc(client, collection_id):
    r = client.post(
        f"/collections/{collection_id}/documents",
        files={"file": ("ml-notes.txt", NOTES.encode(), "text/plain")},
    )
    assert r.status_code == 201, r.text
    return r.json()
