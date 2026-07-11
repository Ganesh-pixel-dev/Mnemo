import requests
import json
from vector_store import search_db

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1" # Using Llama 3.1 8B (fits well in 10GB RAM)

def is_elaboration_query(query: str) -> bool:
    """Simple heuristic to check if the user is asking for more explanation."""
    elaboration_keywords = ["explain", "more", "elaborate", "example", "why", "how", "detail", "beyond"]
    query_lower = query.lower()
    for kw in elaboration_keywords:
        if kw in query_lower:
            return True
    return False

def call_ollama_stream(prompt: str, system_prompt: str):
    """Calls the local Ollama API with streaming enabled."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if not data.get("done"):
                    yield data.get("response", "")
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama: {e}")
        yield "Sorry, I am unable to connect to the local LLM to generate a response. Please ensure Ollama is running."

def handle_query_stream(query: str, chat_id: str = None):
    from database import add_message
    
    if chat_id:
        add_message(chat_id, "user", query)
        
    # 1. Detect Mode
    is_elaboration = is_elaboration_query(query)
    
    # 2. Retrieve relevant chunks
    # BUGFIX: search_db can raise (e.g. embedding model or Chroma errors). Since
    # this whole function is a generator being consumed inside a StreamingResponse,
    # an uncaught exception here doesn't surface as a clean 500 — it breaks the
    # SSE stream mid-flight and the client just sees a dead connection. Catch it
    # and tell the user gracefully instead.
    try:
        results = search_db(query, top_k=3)
    except Exception as e:
        print(f"Error retrieving from vector store: {e}")
        err_msg = "Sorry, I had trouble searching your notes just now. Please try again."
        yield f"data: {json.dumps({'type': 'metadata', 'mode': 'Recall', 'sources': []})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'text': err_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        if chat_id:
            add_message(chat_id, "assistant", err_msg, "Recall", [])
        return
    
    # 3. Format context
    context = ""
    sources = []
    seen_files = set()
    
    for res in results:
        context += f"---\n{res['content']}\n"
        meta = res['metadata']
        
        # Avoid duplicate citations for the same file
        if meta['file_name'] not in seen_files:
            sources.append({
                "file_name": meta['file_name'],
                "date_added": meta.get('date_added')
            })
            seen_files.add(meta['file_name'])
            
    if not results:
        mode = "Recall"
        msg = "I couldn't find any relevant information in your notes."
        yield f"data: {json.dumps({'type': 'metadata', 'mode': mode, 'sources': []})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'text': msg})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        if chat_id:
            add_message(chat_id, "assistant", msg, mode, [])
        return
        
    # 4. Prompt construction
    if is_elaboration:
        mode = "Elaboration"
        system_prompt = (
            "You are a helpful knowledge assistant. The user is asking a follow-up question or for an elaboration. "
            "Use the provided context from their notes as a starting point, but feel free to use your general knowledge "
            "to explain further, give examples, or clarify. Always distinguish what is from their notes vs your general knowledge."
        )
        prompt = f"Context from user's notes:\n{context}\n\nUser Question:\n{query}"
    else:
        mode = "Recall"
        system_prompt = (
            "You are a strict retrieval-augmented generation bot. You MUST answer the user's question ONLY using the "
            "information provided in the context. Do not include outside knowledge. If the context does not contain the answer, "
            "say 'I cannot answer this based on the provided notes.'"
        )
        prompt = f"Context:\n{context}\n\nQuestion:\n{query}"
        
    # Send metadata first
    yield f"data: {json.dumps({'type': 'metadata', 'mode': mode, 'sources': sources})}\n\n"
    
    # 5. Call LLM and stream chunks
    full_response = ""
    for chunk in call_ollama_stream(prompt, system_prompt):
        full_response += chunk
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
        
    if chat_id:
        add_message(chat_id, "assistant", full_response, mode, sources)
        
    yield f"data: {json.dumps({'type': 'done'})}\n\n"