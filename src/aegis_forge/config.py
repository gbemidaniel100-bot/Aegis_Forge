import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("AEGIS_OLLAMA_URL", "http://localhost:11434")
    model: str = os.getenv("AEGIS_MODEL", "llama3.2:3b")
    db_path: str = os.getenv("AEGIS_DB_PATH", "data/aegis.db")
    max_tool_calls: int = _positive_int("AEGIS_MAX_TOOL_CALLS", 6)
    request_timeout_seconds: float = float(os.getenv("AEGIS_REQUEST_TIMEOUT_SECONDS", "20"))
    environment: str = os.getenv("AEGIS_ENVIRONMENT", "development")
    api_token: str = os.getenv("AEGIS_API_TOKEN", "")
    model_fallback: str = os.getenv("AEGIS_MODEL_FALLBACK", "")
    embedding_model: str = os.getenv("AEGIS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    enable_embeddings: bool = os.getenv("AEGIS_ENABLE_EMBEDDINGS", "false").lower() == "true"

    def ensure_data_dir(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
