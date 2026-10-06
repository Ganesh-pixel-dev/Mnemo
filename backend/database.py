import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    ext TEXT NOT NULL,
    size INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (collection_id, filename)
);
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    mode TEXT,
    sources_json TEXT,
    grounding_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class DuplicateError(Exception):
    pass


def new_id() -> str:
    return uuid.uuid4().hex


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _one(self, sql: str, args=()):
        with self._conn() as conn:
            row = conn.execute(sql, args).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, args=()):
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    # collections
    def create_collection(self, name: str) -> dict:
        cid = new_id()
        try:
            with self._conn() as conn:
                conn.execute("INSERT INTO collections (id, name) VALUES (?, ?)", (cid, name))
        except sqlite3.IntegrityError:
            raise DuplicateError(f'A collection called "{name}" already exists.')
        return self.get_collection(cid)

    def get_collection(self, cid: str):
        return self._one("SELECT * FROM collections WHERE id = ?", (cid,))

    def list_collections(self) -> list[dict]:
        return self._all(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM documents d WHERE d.collection_id = c.id) AS document_count,
                      (SELECT COALESCE(SUM(chunk_count), 0) FROM documents d WHERE d.collection_id = c.id) AS chunk_count
               FROM collections c ORDER BY c.rowid"""
        )

    def delete_collection(self, cid: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (cid,))

    # documents
    def add_document(self, collection_id: str, doc_id: str, filename: str, ext: str, size: int, chunk_count: int) -> dict:
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO documents (id, collection_id, filename, ext, size, chunk_count) VALUES (?, ?, ?, ?, ?, ?)",
                    (doc_id, collection_id, filename, ext, size, chunk_count),
                )
        except sqlite3.IntegrityError:
            raise DuplicateError(f"{filename} is already in this collection. Delete it first to upload a new version.")
        return self.get_document(doc_id)

    def get_document(self, doc_id: str):
        return self._one("SELECT * FROM documents WHERE id = ?", (doc_id,))

    def find_document(self, collection_id: str, filename: str):
        return self._one("SELECT * FROM documents WHERE collection_id = ? AND filename = ?", (collection_id, filename))

    def list_documents(self, collection_id: str) -> list[dict]:
        return self._all("SELECT * FROM documents WHERE collection_id = ? ORDER BY rowid", (collection_id,))

    def delete_document(self, doc_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    # chats
    def create_chat(self, collection_id: str, title: str) -> dict:
        chat_id = new_id()
        with self._conn() as conn:
            conn.execute("INSERT INTO chats (id, collection_id, title) VALUES (?, ?, ?)", (chat_id, collection_id, title))
        return self.get_chat(chat_id)

    def get_chat(self, chat_id: str):
        return self._one("SELECT * FROM chats WHERE id = ?", (chat_id,))

    def list_chats(self, collection_id: str) -> list[dict]:
        return self._all("SELECT * FROM chats WHERE collection_id = ? ORDER BY rowid DESC", (collection_id,))

    def delete_chat(self, chat_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    # messages
    def add_message(self, chat_id: str, role: str, content: str, mode=None, sources=None, grounding=None) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (chat_id, role, content, mode, sources_json, grounding_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    chat_id,
                    role,
                    content,
                    mode,
                    json.dumps(sources) if sources is not None else None,
                    json.dumps(grounding) if grounding is not None else None,
                ),
            )

    def get_messages(self, chat_id: str) -> list[dict]:
        rows = self._all("SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
        for row in rows:
            row["sources"] = json.loads(row.pop("sources_json") or "[]")
            grounding = row.pop("grounding_json")
            row["grounding"] = json.loads(grounding) if grounding else None
        return rows
