"""Dictation history and stats in SQLite (%APPDATA%\\FreeFlow\\history.db)."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .config import APP_DIR

TYPING_WPM = 45  # average typing speed used for the "time saved" stat


class History:
    def __init__(self, path: Path | None = None):
        self.path = path or (APP_DIR / "history.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS dictations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                text TEXT NOT NULL,
                words INTEGER NOT NULL,
                duration_s REAL NOT NULL,
                app TEXT DEFAULT '',
                language TEXT DEFAULT ''
            )"""
        )
        self._conn.commit()

    def add(self, text: str, duration_s: float, app: str = "", language: str = "") -> None:
        words = len(text.split())
        with self._lock:
            self._conn.execute(
                "INSERT INTO dictations (ts, text, words, duration_s, app, language) VALUES (?,?,?,?,?,?)",
                (time.time(), text, words, duration_s, app, language),
            )
            self._conn.commit()

    def recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, ts, text, words, duration_s, app, language "
                "FROM dictations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        keys = ("id", "ts", "text", "words", "duration_s", "app", "language")
        return [dict(zip(keys, r)) for r in rows]

    def delete(self, row_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM dictations WHERE id = ?", (row_id,))
            self._conn.commit()

    def stats(self) -> dict:
        with self._lock:
            total_words, total_secs, count = self._conn.execute(
                "SELECT COALESCE(SUM(words),0), COALESCE(SUM(duration_s),0), COUNT(*) FROM dictations"
            ).fetchone()
        speaking_minutes = total_secs / 60
        avg_wpm = (total_words / speaking_minutes) if speaking_minutes > 0.05 else 0
        typing_minutes = total_words / TYPING_WPM
        saved_minutes = max(0.0, typing_minutes - speaking_minutes)
        return {
            "total_words": int(total_words),
            "dictations": int(count),
            "avg_wpm": round(avg_wpm),
            "minutes_saved": round(saved_minutes, 1),
        }
