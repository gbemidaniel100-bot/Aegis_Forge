from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("AEGIS_OLLAMA_URL", "http://localhost:11434")
    model: str = os.getenv("AEGIS_MODEL", "llama3.2:3b")
    db_path: str = os.getenv("AEGIS_DB_PATH", "data/aegis.db")
    max_tool_calls: int = int(os.getenv("AEGIS_MAX_TOOL_CALLS", "6"))


settings = Settings()
