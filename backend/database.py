import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "mnemo.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create chats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            mode TEXT,
            sources_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_chat(chat_id: str, title: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chats (id, title) VALUES (?, ?)', (chat_id, title))
    conn.commit()
    conn.close()

def get_chats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chats ORDER BY created_at DESC')
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return chats

def add_message(chat_id: str, role: str, content: str, mode: str = None, sources: list = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    sources_str = json.dumps(sources) if sources else None
    cursor.execute(
        'INSERT INTO messages (chat_id, role, content, mode, sources_json) VALUES (?, ?, ?, ?, ?)', 
        (chat_id, role, content, mode, sources_str)
    )
    conn.commit()
    conn.close()

def get_messages(chat_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC', (chat_id,))
    
    messages = []
    for row in cursor.fetchall():
        msg = dict(row)
        if msg['sources_json']:
            msg['sources'] = json.loads(msg['sources_json'])
        else:
            msg['sources'] = []
        messages.append(msg)
        
    conn.close()
    return messages

def delete_chat(chat_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
    cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
    conn.commit()
    conn.close()

