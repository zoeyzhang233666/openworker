"""SQLite persistence and retention for content-free TurnTrace records."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import TurnTrace


class TurnTraceStore:
    def __init__(
        self,
        db_path: str | Path,
        *,
        retention_days: int = 30,
        max_rows: int = 5000,
    ) -> None:
        self.db_path = Path(db_path).expanduser()
        self.retention_days = max(1, int(retention_days))
        self.max_rows = max(1, int(max_rows))
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS turn_traces (
                trace_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_turn_traces_session_started ON turn_traces(session_id, started_at DESC)"
        )
        self._conn.commit()

    def append(self, trace: TurnTrace) -> None:
        payload = trace.model_dump_json()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO turn_traces(trace_id, session_id, started_at, status, payload) VALUES (?, ?, ?, ?, ?)",
                (trace.trace_id, trace.session_id, trace.started_at, trace.status, payload),
            )
            self._prune_locked()
            self._conn.commit()

    def get(self, trace_id: str) -> TurnTrace | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM turn_traces WHERE trace_id = ?", (trace_id,)
            ).fetchone()
        return TurnTrace.model_validate_json(row["payload"]) if row else None

    def list(self, *, session_id: str | None = None, limit: int = 100) -> list[TurnTrace]:
        capped = max(1, min(int(limit or 100), 500))
        if session_id:
            sql = "SELECT payload FROM turn_traces WHERE session_id = ? ORDER BY started_at DESC, rowid DESC LIMIT ?"
            params = (session_id, capped)
        else:
            sql = "SELECT payload FROM turn_traces ORDER BY started_at DESC, rowid DESC LIMIT ?"
            params = (capped,)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [TurnTrace.model_validate_json(row["payload"]) for row in rows]

    def _prune_locked(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        self._conn.execute("DELETE FROM turn_traces WHERE started_at < ?", (cutoff,))
        self._conn.execute(
            """
            DELETE FROM turn_traces WHERE trace_id IN (
                SELECT trace_id FROM turn_traces ORDER BY started_at DESC, rowid DESC LIMIT -1 OFFSET ?
            )
            """,
            (self.max_rows,),
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
