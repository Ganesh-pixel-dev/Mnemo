import os
import shutil
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse

from models import QueryRequest, QueryResponse, UploadResponse, CreateChatRequest
from ingestion import extract_text_from_file, chunk_text
from vector_store import add_chunks_to_db, delete_file_chunks
from llm_orchestrator import handle_query_stream
import database

app = FastAPI(title="Mnemo API")

# Initialize SQLite database
database.init_db()

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Default Vite port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/chats")
async def get_chats():
    return database.get_chats()

@app.post("/chats")
async def create_chat(request: CreateChatRequest):
    database.create_chat(request.id, request.title)
    return {"status": "success"}

@app.get("/chats/{chat_id}")
async def get_chat_messages(chat_id: str):
    return database.get_messages(chat_id)

@app.delete("/chats/{chat_id}")
async def delete_chat_endpoint(chat_id: str):
    database.delete_chat(chat_id)
    return {"status": "success"}

@app.get("/files")
async def get_files():
    if not os.path.exists(UPLOAD_DIR):
        return []
    
    files = []
    for f in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, f)
        if os.path.isfile(path):
            stats = os.stat(path)
            files.append({
                "filename": f,
                "size": stats.st_size,
                "uploaded_at": datetime.fromtimestamp(stats.st_mtime).isoformat()
            })
    return files

@app.get("/files/{filename}")
def get_file_content(filename: str):
    # BUGFIX: sanitize the filename so a value like "../../etc/passwd" can't
    # escape UPLOAD_DIR. basename() strips any directory components, and we
    # additionally verify the resolved path still lives inside UPLOAD_DIR.
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if os.path.commonpath([os.path.abspath(file_path), os.path.abspath(UPLOAD_DIR)]) != os.path.abspath(UPLOAD_DIR):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        text = extract_text_from_file(file_path)
        return {"filename": safe_name, "content": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{filename}/raw")
def get_raw_file(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if os.path.commonpath([os.path.abspath(file_path), os.path.abspath(UPLOAD_DIR)]) != os.path.abspath(UPLOAD_DIR):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)

@app.delete("/files/{filename}")
async def delete_file_endpoint(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if os.path.commonpath([os.path.abspath(file_path), os.path.abspath(UPLOAD_DIR)]) != os.path.abspath(UPLOAD_DIR):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if os.path.exists(file_path):
        os.remove(file_path)
    
    delete_file_chunks(safe_name)
    return {"status": "success"}


# BUGFIX: this route is declared as a plain `def`, not `async def`.
# extract_text_from_file (pdfplumber) and add_chunks_to_db (sentence-transformers
# embedding) are blocking, synchronous calls. If this were `async def`, that work
# would run directly on the event loop and freeze every other request (e.g. GET
# /chats, GET /files) for the whole duration of the upload. FastAPI automatically
# runs plain `def` routes in a worker thread, so declaring it this way fixes that.
@app.post("/upload", response_model=UploadResponse)
def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # BUGFIX: sanitize the filename here too — otherwise an uploaded file named
    # "../../../etc/cron.d/evil" could be written outside UPLOAD_DIR.
    safe_name = os.path.basename(file.filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(UPLOAD_DIR, safe_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 1. Extract text
        text = extract_text_from_file(file_path)
        
        # 2. Chunk text
        chunks = chunk_text(text)
        
        # 3. Store in Vector DB
        date_added = datetime.now().strftime("%Y-%m-%d")
        add_chunks_to_db(chunks, safe_name, date_added)
        
        return UploadResponse(
            message=f"Successfully processed {safe_name}",
            chunks_indexed=len(chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_notes(request: QueryRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # BUGFIX (was dead code): handle_query_stream is a generator function, so
    # calling it here only builds a generator object — none of its body runs
    # yet. That means this try/except could never actually catch an error
    # raised during retrieval or generation; those happen later, while
    # StreamingResponse iterates the generator to send bytes to the client.
    # The try/except is removed here and the real error handling now lives
    # inside handle_query_stream itself (see llm_orchestrator.py), which
    # catches failures and yields a graceful SSE error chunk instead of
    # crashing the stream.
    return StreamingResponse(
        handle_query_stream(request.text, request.chat_id),
        media_type="text/event-stream"
    )