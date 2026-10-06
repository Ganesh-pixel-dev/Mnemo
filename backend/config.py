import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        raise SystemExit(f"{name} must be a number")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = BASE_DIR / "data"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    frontend_origins: tuple = ("http://localhost:5173", "http://127.0.0.1:5173")
    max_upload_mb: int = 20
    top_k: int = 4
    min_similarity: float = 0.25
    embed_model: str = "all-MiniLM-L6-v2"
    nli_model: str = "cross-encoder/nli-deberta-v3-xsmall"
    nli_threshold: float = 0.5
    chunk_words: int = 300
    chunk_overlap: int = 50

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("MNEMO_FRONTEND_ORIGINS")
        return cls(
            data_dir=Path(os.environ.get("MNEMO_DATA_DIR", cls.data_dir)),
            ollama_url=os.environ.get("OLLAMA_URL", cls.ollama_url).rstrip("/"),
            ollama_model=os.environ.get("OLLAMA_MODEL", cls.ollama_model),
            frontend_origins=tuple(o.strip() for o in origins.split(",") if o.strip())
            if origins
            else cls.frontend_origins,
            max_upload_mb=int(_float("MNEMO_MAX_UPLOAD_MB", cls.max_upload_mb)),
            top_k=int(_float("MNEMO_TOP_K", cls.top_k)),
            min_similarity=_float("MNEMO_MIN_SIMILARITY", cls.min_similarity),
            embed_model=os.environ.get("MNEMO_EMBED_MODEL", cls.embed_model),
            nli_model=os.environ.get("MNEMO_NLI_MODEL", cls.nli_model),
            nli_threshold=_float("MNEMO_NLI_THRESHOLD", cls.nli_threshold),
        )
