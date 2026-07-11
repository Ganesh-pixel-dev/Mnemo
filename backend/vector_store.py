import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid

# Initialize ChromaDB in the backend directory
db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(name="mnemo_notes")

# Load the sentence transformer model
# all-MiniLM-L6-v2 is small, fast, and good for general semantic search
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def add_chunks_to_db(chunks: list[str], file_name: str, date_added: str):
    """Embeds and adds chunks to the ChromaDB vector store."""
    if not chunks:
        return
        
    embeddings = embedding_model.encode(chunks).tolist()
    
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"file_name": file_name, "date_added": date_added} for _ in chunks]
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

def search_db(query: str, top_k: int = 5):
    """Searches the database for the top_k most similar chunks to the query."""
    # BUGFIX: querying an empty (or near-empty) collection can raise in some
    # Chroma versions instead of just returning fewer results. Guard against
    # that so the very first query before any file is uploaded doesn't 500.
    if collection.count() == 0:
        return []

    query_embedding = embedding_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count())
    )
    
    if not results['documents']:
        return []
        
    # results format from chroma: 
    # {'documents': [['chunk1', 'chunk2']], 'metadatas': [[{'file_name': '...', ...}, ...]], ...}
    
    formatted_results = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        formatted_results.append({
            "content": doc,
            "metadata": meta
        })
        
    return formatted_results

def delete_file_chunks(file_name: str):
    """Deletes all chunks associated with a specific file from the database."""
    collection.delete(where={"file_name": file_name})