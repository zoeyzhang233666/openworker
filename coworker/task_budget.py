"""Durable task-wide budget. Atomic reservations cover concurrent child requests."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path


class TaskBudgetStore:
    def __init__(self, path: str | Path):
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS task_budgets (id TEXT PRIMARY KEY, owner TEXT, data TEXT)")
        self._db.commit()
        # A request pending at process death has unknown usage. Retain its reservation
        # as uncertain consumption rather than silently giving the budget back.
        with self._lock:
            for group, raw in self._db.execute("SELECT id,data FROM task_budgets").fetchall():
                data = json.loads(raw)
                if data["leases"]:
                    data["uncertain"] += len(data["leases"])
                    data["leases"] = {}
                    self._save(group, data)

    def create(self, owner: str, *, size=300, reserve=15):
        if size < 1 or not 0 <= reserve < size:
            raise ValueError("invalid task budget")
        group = uuid.uuid4().hex
        data = dict(owner=owner, size=size, reserve=reserve, segment=1, used=0,
                    uncertain=0, leases={}, stopped=False, model_calls=0, usage={})
        with self._lock:
            self._db.execute("INSERT INTO task_budgets VALUES (?,?,?)", (group, owner, json.dumps(data)))
            self._db.commit()
        return BudgetHandle(self, group, owner, owner, True)

    def bind(self, group, owner, actor, *, parent=False):
        with self._lock:
            if self._read(group)["owner"] != owner:
                raise ValueError("task budget belongs to another session")
        return BudgetHandle(self, group, owner, actor, parent)

    def _read(self, group):
        row = self._db.execute("SELECT data FROM task_budgets WHERE id=?", (group,)).fetchone()
        if row is None:
            raise ValueError("unknown task budget")
        return json.loads(row[0])

    def _save(self, group, data):
        self._db.execute("UPDATE task_budgets SET data=? WHERE id=?", (json.dumps(data), group))
        self._db.commit()

    def snapshot(self, group):
        with self._lock:
            d = self._read(group)
            return {k: v for k, v in d.items() if k != "leases"} | {
                "id": group, "reserved": len(d["leases"]),
                "limit": d["segment"] * d["size"],
                "remaining": max(0, d["segment"] * d["size"] - d["used"] - d["uncertain"] - len(d["leases"])),
            }

    def acquire(self, handle):
        with self._lock:
            d = self._read(handle.group)
            limit = d["segment"] * d["size"] - (0 if handle.parent else d["reserve"])
            if d["stopped"] or d["used"] + d["uncertain"] + len(d["leases"]) >= limit:
                return None
            if handle.actor in d["leases"]:
                raise RuntimeError("concurrent model calls for one task actor")
            token = uuid.uuid4().hex
            d["leases"][handle.actor] = token
            d["model_calls"] += 1
            self._save(handle.group, d)
            return token

    def settle(self, handle, token, *, success=False, usage=None):
        with self._lock:
            d = self._read(handle.group)
            if d["leases"].get(handle.actor) != token:
                return
            del d["leases"][handle.actor]
            d["used"] += int(success)
            for key, value in (usage or {}).items():
                if isinstance(value, (int, float)):
                    d["usage"][key] = d["usage"].get(key, 0) + value
            self._save(handle.group, d)

    def continue_segment(self, handle, expected_segment):
        if not handle.parent:
            raise ValueError("only the owning user turn can extend the task budget")
        with self._lock:
            d = self._read(handle.group)
            if d["segment"] != expected_segment or d["leases"]:
                return False
            if d["used"] + d["uncertain"] < d["segment"] * d["size"] - d["reserve"]:
                return False
            d["segment"] += 1
            d["stopped"] = False
            self._save(handle.group, d)
            return True

    def stop(self, group):
        with self._lock:
            d = self._read(group)
            d["stopped"] = True
            self._save(group, d)


class BudgetHandle:
    def __init__(self, store, group, owner, actor, parent):
        self.store, self.group, self.owner, self.actor, self.parent = store, group, owner, actor, parent

    def snapshot(self):
        return self.store.snapshot(self.group)

    @property
    def summarizing(self):
        d = self.snapshot()
        return d["remaining"] <= d["reserve"]

    def acquire(self):
        return self.store.acquire(self)

    def settle(self, token, *, success=False, usage=None):
        self.store.settle(self, token, success=success, usage=usage)
