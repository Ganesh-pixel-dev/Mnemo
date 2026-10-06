import json
from typing import Iterator

import requests


class LLMError(Exception):
    """Ollama can't answer. `code` is stable for the UI, `message` is safe to show."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def _unavailable(self) -> LLMError:
        return LLMError(
            "ollama_unavailable",
            f"Can't reach Ollama at {self.base_url}. Start it (run `ollama serve`) and try again.",
        )

    def _model_missing(self) -> LLMError:
        return LLMError(
            "model_missing",
            f"The model {self.model} isn't installed in Ollama. Run `ollama pull {self.model}`, "
            "or set OLLAMA_MODEL to a model you have.",
        )

    def status(self) -> dict:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
        except (requests.RequestException, ValueError):
            return {"running": False, "model": self.model, "model_available": False}
        wanted = self.model if ":" in self.model else f"{self.model}:latest"
        return {"running": True, "model": self.model, "model_available": wanted in names}

    def stream(self, system: str, prompt: str, temperature: float = 0.1) -> Iterator[str]:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": 4096},
        }
        try:
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, stream=True, timeout=(5, 120))
        except requests.ConnectionError:
            raise self._unavailable()
        except requests.Timeout:
            raise LLMError("ollama_timeout", "Ollama didn't respond in time.")

        try:
            if resp.status_code == 404:
                raise self._model_missing()
            if resp.status_code != 200:
                raise LLMError("ollama_error", f"Ollama returned an error (HTTP {resp.status_code}).")
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except ValueError:
                    raise LLMError("ollama_error", "Ollama sent a response I couldn't read.")
                if "error" in data:
                    if "not found" in data["error"]:
                        raise self._model_missing()
                    raise LLMError("ollama_error", f"Ollama error: {data['error']}")
                if data.get("response"):
                    yield data["response"]
                if data.get("done"):
                    return
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            raise LLMError("ollama_interrupted", "The connection to Ollama dropped while answering.")
        except requests.Timeout:
            raise LLMError("ollama_timeout", "Ollama stopped responding mid-answer.")
        finally:
            resp.close()
