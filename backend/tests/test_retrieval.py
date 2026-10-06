from tests.conftest import FakeEmbedder
from vector_store import VectorStore


def make_store(tmp_path):
    store = VectorStore(tmp_path / "chroma", FakeEmbedder())
    store.add("c1", "d1", "ml.txt", [
        "gradient descent lowers the loss by updating weights",
        "the french revolution began in 1789 in paris",
    ])
    return store


def test_relevant_chunk_ranks_first(tmp_path):
    hits = make_store(tmp_path).search("c1", "how does gradient descent update weights", top_k=2, min_similarity=0.0)
    assert hits[0].text.startswith("gradient descent")
    assert hits[0].filename == "ml.txt" and hits[0].chunk_index == 0
    assert hits[0].score > hits[1].score


def test_threshold_drops_unrelated_chunks(tmp_path):
    store = make_store(tmp_path)
    hits = store.search("c1", "gradient descent weights", top_k=2, min_similarity=0.3)
    assert [h.chunk_index for h in hits] == [0]
    assert store.search("c1", "quantum chromodynamics lecture", top_k=2, min_similarity=0.3) == []


def test_empty_and_other_collections_return_nothing(tmp_path):
    store = make_store(tmp_path)
    assert store.search("c2", "gradient descent", top_k=3, min_similarity=0.0) == []


def test_delete_document_and_collection(tmp_path):
    store = make_store(tmp_path)
    store.delete_document("c1", "d1")
    assert store.search("c1", "gradient descent", top_k=3, min_similarity=0.0) == []
    store.delete_collection("c1")
    store.delete_collection("never-existed")
