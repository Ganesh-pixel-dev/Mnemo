import os
import pdfplumber

def extract_text_from_file(file_path: str) -> str:
    """Extracts raw text from a given file (.txt, .md, .pdf)."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.txt', '.md']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.pdf':
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def chunk_text(text: str, chunk_size_words: int = 300, overlap_words: int = 50) -> list[str]:
    """Splits text into chunks of roughly `chunk_size_words` with `overlap_words` overlap."""
    # BUGFIX: if overlap_words >= chunk_size_words, `start` never advances
    # (or goes backwards) and the while loop below never terminates. The
    # defaults are safe, but nothing stopped a future caller from passing
    # bad values and hanging the request.
    if overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be smaller than chunk_size_words")

    words = text.split()
    chunks = []
    
    if not words:
        return chunks
        
    start = 0
    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        
        if end == len(words):
            break
            
        start += (chunk_size_words - overlap_words)
        
    return chunks