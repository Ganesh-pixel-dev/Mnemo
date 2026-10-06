from dataclasses import asdict, dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings


class SentenceEmbedder:
    """all-MiniLM-L6-v2 by default, on CPU. Loaded on first use so importing the app stays cheap."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def encode(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model.encode(texts, normalize_embeddings=True).tolist()


@dataclass
class Hit:
    doc_id: str
    filename: str
    chunk_index: int
    text: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


class VectorStore:
    """One Chroma collection per note collection, cosine distance."""

    def __init__(self, path: Path, embedder):
        self.embedder = embedder
        self.client = chromadb.PersistentClient(
            path=str(path), settings=ChromaSettings(anonymized_telemetry=False)
        )

    @staticmethod
    def _name(collection_id: str) -> str:
        return f"notes_{collection_id}"

    def _collection(self, collection_id: str):
        return self.client.get_or_create_collection(
            name=self._name(collection_id), metadata={"hnsw:space": "cosine"}
        )

    def add(self, collection_id: str, doc_id: str, filename: str, chunks: list[str]) -> None:
        if not chunks:
            return
        embeddings = self.embedder.encode(chunks)
        self._collection(collection_id).add(
            ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"doc_id": doc_id, "filename": filename, "chunk_index": i} for i in range(len(chunks))],
        )

    def search(self, collection_id: str, query: str, top_k: int, min_similarity: float) -> list[Hit]:
        collection = self._collection(collection_id)
        count = collection.count()
        if count == 0:
            return []
        result = collection.query(
            query_embeddings=self.embedder.encode([query]),
            n_results=min(top_k, count),
        )
        hits = []
        for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            score = 1.0 - distance
            if score >= min_similarity:
                hits.append(Hit(meta["doc_id"], meta["filename"], meta["chunk_index"], text, round(score, 4)))
        return hits

    def delete_document(self, collection_id: str, doc_id: str) -> None:
        self._collection(collection_id).delete(where={"doc_id": doc_id})

    def delete_collection(self, collection_id: str) -> None:
        try:
            self.client.delete_collection(self._name(collection_id))
        except Exception:
            pass
