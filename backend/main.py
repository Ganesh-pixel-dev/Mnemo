import json
import logging
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

import ingestion
from config import Settings
from database import Database, DuplicateError, new_id
from grounding import Grounder, NLIScorer
from llm import OllamaClient
from rag import QueryService
from vector_store import SentenceEmbedder, VectorStore

log = logging.getLogger("mnemo")

DEFAULT_COLLECTION = "My notes"
READ_BLOCK = 1024 * 1024


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class ChatIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class QueryIn(BaseModel):
    collection_id: str
    chat_id: str | None = None
    text: str = Field(min_length=1, max_length=2000)


def sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def create_app(settings: Settings | None = None, embedder=None, llm=None, scorer=None) -> FastAPI:
    settings = settings or Settings.from_env()
    data_dir = Path(settings.data_dir)
    upload_dir = data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    db = Database(data_dir / "mnemo.db")
    store = VectorStore(data_dir / "chroma", embedder or SentenceEmbedder(settings.embed_model))
    llm = llm or OllamaClient(settings.ollama_url, settings.ollama_model)
    scorer = scorer if scorer is not None else NLIScorer(settings.nli_model)
    service = QueryService(settings, db, store, llm, Grounder(scorer, settings.nli_threshold))

    if not db.list_collections():
        db.create_collection(DEFAULT_COLLECTION)

    app = FastAPI(title="Mnemo API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def collection_or_404(collection_id: str) -> dict:
        collection = db.get_collection(collection_id)
        if not collection:
            raise HTTPException(404, "Collection not found.")
        return collection

    def document_or_404(collection_id: str, doc_id: str) -> dict:
        doc = db.get_document(doc_id)
        if not doc or doc["collection_id"] != collection_id:
            raise HTTPException(404, "Document not found.")
        return doc

    def doc_dir(collection_id: str) -> Path:
        return upload_dir / collection_id

    @app.get("/health")
    def health():
        return {"ollama": llm.status(), "max_upload_mb": settings.max_upload_mb}

    # collections
    @app.get("/collections")
    def list_collections():
        return db.list_collections()

    @app.post("/collections", status_code=201)
    def create_collection(body: CollectionIn):
        try:
            return db.create_collection(body.name.strip())
        except DuplicateError as exc:
            raise HTTPException(409, str(exc))

    @app.delete("/collections/{collection_id}")
    def delete_collection(collection_id: str):
        collection_or_404(collection_id)
        db.delete_collection(collection_id)
        store.delete_collection(collection_id)
        shutil.rmtree(doc_dir(collection_id), ignore_errors=True)
        if not db.list_collections():
            db.create_collection(DEFAULT_COLLECTION)
        return {"status": "deleted"}

    # documents
    @app.get("/collections/{collection_id}/documents")
    def list_documents(collection_id: str):
        collection_or_404(collection_id)
        return db.list_documents(collection_id)

    @app.post("/collections/{collection_id}/documents", status_code=201)
    def upload_document(collection_id: str, file: UploadFile = File(...)):
        collection_or_404(collection_id)
        filename = Path((file.filename or "").replace("\\", "/")).name
        ext = Path(filename).suffix.lower()
        if not filename:
            raise HTTPException(400, "No file was uploaded.")
        if ext not in ingestion.SUPPORTED:
            raise HTTPException(415, f"{ext or 'That'} files aren't supported. Upload a PDF, TXT or MD file.")
        if db.find_document(collection_id, filename):
            raise HTTPException(409, f"{filename} is already in this collection. Delete it first to upload a new version.")

        doc_id = new_id()
        folder = doc_dir(collection_id)
        folder.mkdir(parents=True, exist_ok=True)
        original = folder / f"{doc_id}{ext}"
        text_copy = folder / f"{doc_id}.txt"
        indexed = committed = False
        try:
            size = 0
            with open(original, "wb") as out:
                while block := file.file.read(READ_BLOCK):
                    size += len(block)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, f"That file is over the {settings.max_upload_mb} MB limit.")
                    out.write(block)
            if size == 0:
                raise HTTPException(400, "That file is empty.")
            if ext == ".pdf" and not original.read_bytes()[:1024].lstrip().startswith(b"%PDF"):
                raise HTTPException(400, "That doesn't look like a PDF.")
            try:
                text = ingestion.extract_text(original)
            except ingestion.IngestionError as exc:
                raise HTTPException(422, str(exc))
            chunks = ingestion.chunk_text(text, settings.chunk_words, settings.chunk_overlap)
            text_copy.write_text(text, encoding="utf-8")
            store.add(collection_id, doc_id, filename, chunks)
            indexed = True
            document = db.add_document(collection_id, doc_id, filename, ext, size, len(chunks))
            committed = True
            return document
        except DuplicateError as exc:
            raise HTTPException(409, str(exc))
        except HTTPException:
            raise
        except Exception:
            log.exception("indexing %s failed", filename)
            raise HTTPException(500, "Indexing failed. Check the backend log.")
        finally:
            if not committed:
                if indexed:
                    store.delete_document(collection_id, doc_id)
                original.unlink(missing_ok=True)
                text_copy.unlink(missing_ok=True)

    @app.get("/collections/{collection_id}/documents/{doc_id}/text")
    def document_text(collection_id: str, doc_id: str):
        doc = document_or_404(collection_id, doc_id)
        text_path = doc_dir(collection_id) / f"{doc_id}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        return {"filename": doc["filename"], "content": text}

    @app.get("/collections/{collection_id}/documents/{doc_id}/raw")
    def document_raw(collection_id: str, doc_id: str):
        doc = document_or_404(collection_id, doc_id)
        path = doc_dir(collection_id) / f"{doc_id}{doc['ext']}"
        if not path.exists():
            raise HTTPException(404, "The stored file is missing.")
        media = "application/pdf" if doc["ext"] == ".pdf" else "text/plain; charset=utf-8"
        return FileResponse(path, media_type=media, headers={"X-Content-Type-Options": "nosniff"})

    @app.delete("/collections/{collection_id}/documents/{doc_id}")
    def delete_document(collection_id: str, doc_id: str):
        doc = document_or_404(collection_id, doc_id)
        store.delete_document(collection_id, doc_id)
        db.delete_document(doc_id)
        for path in (doc_dir(collection_id) / f"{doc_id}{doc['ext']}", doc_dir(collection_id) / f"{doc_id}.txt"):
            path.unlink(missing_ok=True)
        return {"status": "deleted"}

    # chats
    @app.get("/collections/{collection_id}/chats")
    def list_chats(collection_id: str):
        collection_or_404(collection_id)
        return db.list_chats(collection_id)

    @app.post("/collections/{collection_id}/chats", status_code=201)
    def create_chat(collection_id: str, body: ChatIn):
        collection_or_404(collection_id)
        return db.create_chat(collection_id, body.title.strip())

    @app.get("/chats/{chat_id}")
    def chat_messages(chat_id: str):
        if not db.get_chat(chat_id):
            raise HTTPException(404, "Chat not found.")
        return db.get_messages(chat_id)

    @app.delete("/chats/{chat_id}")
    def delete_chat(chat_id: str):
        if not db.get_chat(chat_id):
            raise HTTPException(404, "Chat not found.")
        db.delete_chat(chat_id)
        return {"status": "deleted"}

    # query
    @app.post("/query")
    def query(body: QueryIn):
        question = body.text.strip()
        if not question:
            raise HTTPException(400, "The question is empty.")
        collection_or_404(body.collection_id)
        if body.chat_id:
            chat = db.get_chat(body.chat_id)
            if not chat or chat["collection_id"] != body.collection_id:
                raise HTTPException(404, "Chat not found in this collection.")

        def events():
            try:
                for event in service.stream(body.collection_id, question, body.chat_id):
                    yield sse(event)
            except Exception:
                log.exception("query failed")
                yield sse({"type": "error", "code": "internal", "message": "Something went wrong while answering. Check the backend log."})

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
