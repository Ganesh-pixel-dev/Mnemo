from pathlib import Path

import pdfplumber

SUPPORTED = {".pdf", ".txt", ".md"}
MIN_WORDS = 20


class IngestionError(Exception):
    """The file can't be turned into searchable text. The message is safe to show the user."""


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".txt", ".md"):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raise IngestionError("That file isn't valid UTF-8 text. Save it as UTF-8 and try again.")
    elif ext == ".pdf":
        text = _pdf_text(path)
    else:
        raise IngestionError(f"Unsupported file type {ext or '(none)'}. Use PDF, TXT or MD.")

    if len(text.split()) < MIN_WORDS:
        if ext == ".pdf":
            raise IngestionError(
                "No readable text found in this PDF. It is probably a scan or images. "
                "Mnemo can't do OCR, so run it through an OCR tool first."
            )
        raise IngestionError("That file has almost no text in it.")
    return text


def _pdf_text(path: Path) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        name = type(exc).__name__
        if "Password" in name or "Encrypt" in name:
            raise IngestionError("This PDF is password protected.")
        raise IngestionError("Couldn't read this PDF. It may be damaged.")
    return "\n".join(pages)


def chunk_text(text: str, size: int = 300, overlap: int = 50) -> list[str]:
    """Split into windows of `size` words that share `overlap` words with the previous one."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("need 0 <= overlap < size")
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks
