import pytest

from llm import LLMError
from tests.conftest import NOTES, make_pdf, parse_sse


def ask(client, collection_id, text, chat_id=None):
    r = client.post("/query", json={"collection_id": collection_id, "text": text, "chat_id": chat_id})
    assert r.status_code == 200, r.text
    return parse_sse(r)


def test_default_collection_exists(client):
    assert [c["name"] for c in client.get("/collections").json()] == ["My notes"]


def test_collections_create_duplicate_delete(client):
    r = client.post("/collections", json={"name": "Physics"})
    assert r.status_code == 201
    assert client.post("/collections", json={"name": "Physics"}).status_code == 409
    cid = r.json()["id"]
    assert client.delete(f"/collections/{cid}").status_code == 200
    assert client.delete(f"/collections/{cid}").status_code == 404


def test_deleting_last_collection_leaves_a_default(client, collection_id):
    client.delete(f"/collections/{collection_id}")
    assert len(client.get("/collections").json()) == 1


def test_upload_txt_and_pdf(client, collection_id):
    r = client.post(f"/collections/{collection_id}/documents", files={"file": ("a.txt", NOTES.encode(), "text/plain")})
    assert r.status_code == 201 and r.json()["chunk_count"] >= 1
    pdf = make_pdf("Osmosis is the movement of water across a membrane toward higher solute concentration. " * 4)
    r = client.post(f"/collections/{collection_id}/documents", files={"file": ("bio.pdf", pdf, "application/pdf")})
    assert r.status_code == 201
    assert [d["filename"] for d in client.get(f"/collections/{collection_id}/documents").json()] == ["a.txt", "bio.pdf"]


@pytest.mark.parametrize(
    "name,content,status,fragment",
    [
        ("virus.exe", b"MZ" * 50, 415, "aren't supported"),
        ("empty.txt", b"", 400, "empty"),
        ("fake.pdf", b"not a pdf at all" * 5, 400, "doesn't look like a PDF"),
        ("scan.pdf", make_pdf(""), 422, "OCR"),
        ("tiny.txt", b"hi there", 422, "almost no text"),
    ],
)
def test_upload_validation(client, collection_id, name, content, status, fragment):
    r = client.post(f"/collections/{collection_id}/documents", files={"file": (name, content, "application/octet-stream")})
    assert r.status_code == status
    assert fragment in r.json()["detail"]
    assert client.get(f"/collections/{collection_id}/documents").json() == []


def test_upload_too_large(client, collection_id):
    big = b"word " * (300 * 1024)
    r = client.post(f"/collections/{collection_id}/documents", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413


def test_duplicate_upload_is_rejected(client, collection_id, notes_doc):
    r = client.post(f"/collections/{collection_id}/documents", files={"file": ("ml-notes.txt", NOTES.encode(), "text/plain")})
    assert r.status_code == 409


def test_path_traversal_filename_is_flattened(client, collection_id):
    r = client.post(f"/collections/{collection_id}/documents", files={"file": ("../../evil.txt", NOTES.encode(), "text/plain")})
    assert r.status_code == 201
    assert r.json()["filename"] == "evil.txt"


def test_collections_are_separate(client, notes_doc):
    other = client.post("/collections", json={"name": "Other"}).json()["id"]
    events = ask(client, other, "What is gradient descent?")
    assert [e["type"] for e in events] == ["metadata", "chunk", "done"]
    assert "don't cover" in events[1]["text"]


def test_recall_answer_has_sources_and_grounding(client, collection_id, notes_doc, llm):
    events = ask(client, collection_id, "What does my note say about gradient descent weights?")
    types = [e["type"] for e in events]
    assert types[0] == "metadata" and types[-1] == "done" and "grounding" in types
    assert events[0]["mode"] == "Recall"
    source = events[0]["sources"][0]
    assert source["filename"] == "ml-notes.txt" and source["n"] == 1 and source["text"]
    assert "only" in llm.calls[0]["system"]


def test_recall_flags_an_unsupported_sentence(client, collection_id, notes_doc, llm):
    llm.reply = "The learning rate controls the size of each step [1]. Gradient descent was patented by Google in 2009."
    grounding = next(e for e in ask(client, collection_id, "Tell me about the learning rate step") if e["type"] == "grounding")
    assert [s["supported"] for s in grounding["sentences"]] == [True, False]


def test_recall_refuses_without_calling_the_llm(client, collection_id, notes_doc, llm):
    events = ask(client, collection_id, "Zebra quantum chromodynamics football")
    assert events[1]["text"] == "Your notes don't cover this."
    assert events[0]["sources"] == []
    assert llm.calls == []


def test_elaboration_mode_is_labelled_and_not_grounded(client, collection_id, notes_doc, llm):
    events = ask(client, collection_id, "Explain gradient descent with an example")
    assert events[0]["mode"] == "Elaboration"
    assert "grounding" not in [e["type"] for e in events]
    assert "Beyond your notes" in llm.calls[0]["system"]


def test_ollama_down_is_a_clear_error_event(client, collection_id, notes_doc, llm):
    llm.error = LLMError("ollama_unavailable", "Can't reach Ollama. Start it and try again.")
    chat = client.post(f"/collections/{collection_id}/chats", json={"title": "t"}).json()
    events = ask(client, collection_id, "What is gradient descent weights", chat["id"])
    assert events[-1] == {"type": "error", "code": "ollama_unavailable", "message": "Can't reach Ollama. Start it and try again."}
    assert [m["role"] for m in client.get(f"/chats/{chat['id']}").json()] == ["user"]


def test_chat_history_is_saved_in_order(client, collection_id, notes_doc):
    chat = client.post(f"/collections/{collection_id}/chats", json={"title": "ml"}).json()
    ask(client, collection_id, "What does gradient descent do to weights", chat["id"])
    ask(client, collection_id, "What is the learning rate step", chat["id"])
    messages = client.get(f"/chats/{chat['id']}").json()
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[1]["sources"] and messages[1]["grounding"]["sentences"]
    assert client.get(f"/collections/{collection_id}/chats").json()[0]["id"] == chat["id"]
    assert client.delete(f"/chats/{chat['id']}").status_code == 200
    assert client.get(f"/chats/{chat['id']}").status_code == 404


def test_chat_from_another_collection_is_rejected(client, collection_id):
    other = client.post("/collections", json={"name": "Other"}).json()["id"]
    chat = client.post(f"/collections/{other}/chats", json={"title": "x"}).json()
    r = client.post("/query", json={"collection_id": collection_id, "chat_id": chat["id"], "text": "hi there"})
    assert r.status_code == 404


def test_delete_document_removes_it_from_search(client, collection_id, notes_doc):
    assert client.delete(f"/collections/{collection_id}/documents/{notes_doc['id']}").status_code == 200
    assert "don't cover" in ask(client, collection_id, "What is gradient descent")[1]["text"]


def test_document_text_and_raw(client, collection_id, notes_doc):
    base = f"/collections/{collection_id}/documents/{notes_doc['id']}"
    assert "Gradient descent" in client.get(f"{base}/text").json()["content"]
    assert client.get(f"{base}/raw").headers["content-type"].startswith("text/plain")


def test_cors_only_allows_the_frontend_origin(client):
    ok = client.options("/collections", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/collections", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_empty_question_is_rejected(client, collection_id):
    assert client.post("/query", json={"collection_id": collection_id, "text": "   "}).status_code == 400
