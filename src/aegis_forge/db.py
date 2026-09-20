from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = RLock()
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
              id INTEGER PRIMARY KEY AUTOINCREMENT, namespace TEXT NOT NULL,
              content TEXT NOT NULL, importance REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS traces (
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
              event TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS evals (
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
              metric TEXT NOT NULL, score REAL NOT NULL, detail TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def remember(self, namespace: str, content: str, importance: float = 0.5) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT INTO memories(namespace, content, importance) VALUES (?, ?, ?)",
                (namespace, content, importance),
            )
            self.connection.commit()

    def memories(self, namespace: str, limit: int = 10) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM memories WHERE namespace = ? ORDER BY importance DESC, id DESC LIMIT ?",
                (namespace, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def trace(self, run_id: str, event: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT INTO traces(run_id, event, payload) VALUES (?, ?, ?)",
                (run_id, event, json.dumps(payload, default=str)),
            )
            self.connection.commit()

    def trace_for(self, run_id: str) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute("SELECT * FROM traces WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def add_eval(self, run_id: str, metric: str, score: float, detail: str) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT INTO evals(run_id, metric, score, detail) VALUES (?, ?, ?, ?)",
                (run_id, metric, score, detail),
            )
            self.connection.commit()
