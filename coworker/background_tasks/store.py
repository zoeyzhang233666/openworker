"""SQLite persistence for BackgroundTaskManager.

Task metadata and output live in dedicated tables inside coworker.db.  Conversation
messages remain owned by ConversationStore; this store never persists prompts or tool args.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from .models import (
    BackgroundTaskRecord,
    TERMINAL_TASK_STATUSES,
    TaskOutputChunk,
    TaskOutputPage,
    TaskStatus,
)


class BackgroundTaskStore:
    def __init__(
        self,
        db_path: str | Path,
        *,
        retention_days: int = 30,
        max_terminal_tasks: int = 5000,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_days = max(1, int(retention_days))
        self.max_terminal_tasks = max(1, int(max_terminal_tasks))
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS background_tasks (
                task_id TEXT PRIMARY KEY,
                owner_session_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                data TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_background_tasks_owner
                ON background_tasks(owner_session_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_background_tasks_status
                ON background_tasks(status, updated_at DESC);
            CREATE TABLE IF NOT EXISTS background_task_output (
                task_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                stream TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY(task_id, seq),
                FOREIGN KEY(task_id) REFERENCES background_tasks(task_id) ON DELETE CASCADE
            );
            """
        )
        self._conn.commit()

    def put(self, record: BackgroundTaskRecord) -> BackgroundTaskRecord:
        payload = record.model_dump_json()
        with self._lock:
            self._conn.execute(
                """INSERT INTO background_tasks
                   (task_id, owner_session_id, kind, status, created_at, updated_at, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       owner_session_id=excluded.owner_session_id,
                       kind=excluded.kind,
                       status=excluded.status,
                       created_at=excluded.created_at,
                       updated_at=excluded.updated_at,
                       data=excluded.data""",
                (
                    record.id,
                    record.owner_session_id,
                    record.kind,
                    record.status,
                    record.created_at,
                    record.updated_at,
                    payload,
                ),
            )
            self._conn.commit()
        return record

    def get(self, task_id: str) -> BackgroundTaskRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM background_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return BackgroundTaskRecord.model_validate_json(row["data"]) if row else None

    def list(
        self,
        *,
        owner_session_id: str | None = None,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[BackgroundTaskRecord]:
        where: list[str] = []
        args: list[object] = []
        if owner_session_id is not None:
            where.append("owner_session_id = ?")
            args.append(owner_session_id)
        if status is not None:
            where.append("status = ?")
            args.append(status)
        clause = " WHERE " + " AND ".join(where) if where else ""
        args.append(max(1, min(int(limit), 500)))
        with self._lock:
            rows = self._conn.execute(
                f"SELECT data FROM background_tasks{clause} ORDER BY created_at DESC LIMIT ?",
                args,
            ).fetchall()
        return [BackgroundTaskRecord.model_validate_json(row["data"]) for row in rows]

    def append_output(
        self, task_id: str, *, stream: str, text: str, created_at: float | None = None
    ) -> TaskOutputChunk:
        now = float(created_at or time.time())
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) AS n FROM background_task_output WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            seq = int(row["n"]) + 1
            self._conn.execute(
                """INSERT INTO background_task_output(task_id, seq, stream, text, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (task_id, seq, stream, text, now),
            )
            record = self.get(task_id)
            if record is not None:
                updated = record.model_copy(
                    update={
                        "output_size": record.output_size + len(text),
                        "updated_at": now,
                    }
                )
                self._conn.execute(
                    """UPDATE background_tasks SET updated_at = ?, data = ?
                       WHERE task_id = ?""",
                    (now, updated.model_dump_json(), task_id),
                )
            self._conn.commit()
        return TaskOutputChunk(
            task_id=task_id, seq=seq, stream=stream, text=text, created_at=now
        )

    def read_output(
        self,
        task_id: str,
        *,
        cursor: int = 0,
        max_chars: int = 20_000,
        max_chunks: int = 200,
    ) -> TaskOutputPage:
        cursor = max(0, int(cursor))
        max_chars = max(1, min(int(max_chars), 100_000))
        max_chunks = max(1, min(int(max_chunks), 500))
        with self._lock:
            rows = self._conn.execute(
                """SELECT task_id, seq, stream, text, created_at
                   FROM background_task_output WHERE task_id = ? AND seq > ?
                   ORDER BY seq ASC LIMIT ?""",
                (task_id, cursor, max_chunks + 1),
            ).fetchall()
        chunks: list[TaskOutputChunk] = []
        total = 0
        truncated = len(rows) > max_chunks
        for row in rows[:max_chunks]:
            text = str(row["text"])
            if chunks and total + len(text) > max_chars:
                truncated = True
                break
            if not chunks and len(text) > max_chars:
                text = text[-max_chars:]
                truncated = True
            chunk = TaskOutputChunk(
                task_id=row["task_id"],
                seq=row["seq"],
                stream=row["stream"],
                text=text,
                created_at=row["created_at"],
            )
            chunks.append(chunk)
            total += len(text)
        next_cursor = chunks[-1].seq if chunks else cursor
        return TaskOutputPage(
            task_id=task_id,
            chunks=tuple(chunks),
            next_cursor=next_cursor,
            truncated=truncated,
        )

    def reconcile_incomplete(self, *, reason: str = "process restarted") -> int:
        now = time.time()
        changed = 0
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM background_tasks WHERE status IN ('queued', 'running')"
            ).fetchall()
        for row in rows:
            record = BackgroundTaskRecord.model_validate_json(row["data"])
            updated = record.model_copy(
                update={
                    "status": "interrupted",
                    "updated_at": now,
                    "finished_at": now,
                    "error": reason,
                }
            )
            self.put(updated)
            self.append_output(record.id, stream="system", text=f"{reason}\n")
            changed += 1
        return changed

    def cleanup(self, *, now: float | None = None) -> int:
        now = float(now or time.time())
        cutoff = now - self.retention_days * 86400
        terminal = tuple(TERMINAL_TASK_STATUSES)
        placeholders = ",".join("?" for _ in terminal)
        with self._lock:
            old_rows = self._conn.execute(
                f"""SELECT task_id FROM background_tasks
                    WHERE status IN ({placeholders}) AND updated_at < ?""",
                (*terminal, cutoff),
            ).fetchall()
            keep_rows = self._conn.execute(
                f"""SELECT task_id FROM background_tasks
                    WHERE status IN ({placeholders}) ORDER BY updated_at DESC
                    LIMIT -1 OFFSET ?""",
                (*terminal, self.max_terminal_tasks),
            ).fetchall()
            ids = {row["task_id"] for row in (*old_rows, *keep_rows)}
            if ids:
                self._conn.executemany(
                    "DELETE FROM background_tasks WHERE task_id = ?", ((i,) for i in ids)
                )
                self._conn.commit()
        return len(ids)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
