"""Delegation cohort tracking for fan-in synthesis after parallel subagents.

Contract absorbs DeerFlow terminal-status fan-in and Claude Code completion
notification timing: when every agent task in a cohort is terminal, fire once.
Does not own TurnEngine, permissions, or transport — callers deliver the wake.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from ..background_tasks.models import SETTLED_TASK_STATUSES as TERMINAL_TASK_STATUSES


@dataclass(frozen=True)
class CohortMember:
    task_id: str
    profile_id: str = ""
    description: str = ""
    status: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CohortReady:
    cohort_id: str
    owner_session_id: str
    parent_trace_id: str
    members: tuple[CohortMember, ...]


@dataclass
class _Cohort:
    cohort_id: str
    owner_session_id: str
    parent_trace_id: str
    members: dict[str, CohortMember] = field(default_factory=dict)
    synthesis_fired: bool = False
    sealed: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class DelegationCohortTracker:
    """Track open agent-task batches keyed by (owner_session_id, parent_trace_id)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._lock = threading.RLock()
        self._cohorts: dict[str, _Cohort] = {}
        self._task_index: dict[str, str] = {}
        if self.path is not None:
            self._load()

    def register(
        self,
        owner_session_id: str,
        task_id: str,
        *,
        parent_trace_id: str | None = None,
        profile_id: str = "",
        description: str = "",
        require_seal: bool = False,
        new_run: bool = False,
    ) -> str:
        owner = (owner_session_id or "").strip()
        tid = (task_id or "").strip()
        if not owner or not tid:
            raise ValueError("owner_session_id and task_id are required")
        trace = (parent_trace_id or "").strip()
        with self._lock:
            if new_run:
                self._task_index.pop(tid, None)
            existing_cohort_id = self._task_index.get(tid)
            if existing_cohort_id is not None:
                return existing_cohort_id
            cohort = self._open_cohort(owner, trace)
            if require_seal:
                cohort.sealed = False
            cohort.members[tid] = CohortMember(
                task_id=tid,
                profile_id=profile_id or "",
                description=description or "",
            )
            cohort.updated_at = time.time()
            self._task_index[tid] = cohort.cohort_id
            self._save()
            return cohort.cohort_id

    def on_terminal(
        self,
        task_id: str,
        *,
        status: str,
        error: str | None = None,
    ) -> CohortReady | None:
        tid = (task_id or "").strip()
        if not tid:
            return None
        if status not in TERMINAL_TASK_STATUSES:
            return None
        with self._lock:
            cohort_id = self._task_index.get(tid)
            if cohort_id is None:
                return None
            cohort = self._cohorts.get(cohort_id)
            if cohort is None or cohort.synthesis_fired:
                return None
            member = cohort.members.get(tid)
            if member is None:
                return None
            cohort.members[tid] = CohortMember(
                task_id=member.task_id,
                profile_id=member.profile_id,
                description=member.description,
                status=status,
                error=error,
            )
            cohort.updated_at = time.time()
            if not cohort.sealed or not self._all_terminal(cohort):
                self._save()
                return None
            cohort.synthesis_fired = True
            cohort.updated_at = time.time()
            self._save()
            return CohortReady(
                cohort_id=cohort.cohort_id,
                owner_session_id=cohort.owner_session_id,
                parent_trace_id=cohort.parent_trace_id,
                members=tuple(cohort.members[k] for k in sorted(cohort.members)),
            )

    def reap_with_statuses(
        self, statuses: dict[str, tuple[str, str | None]]
    ) -> list[CohortReady]:
        """Re-evaluate open cohorts after restart using known task statuses."""
        ready: list[CohortReady] = []
        with self._lock:
            task_ids = list(self._task_index)
        for task_id in task_ids:
            if task_id not in statuses:
                continue
            status, error = statuses[task_id]
            fired = self.on_terminal(task_id, status=status, error=error)
            if fired is not None:
                ready.append(fired)
        return ready

    def seal(self, owner, trace):
        """The parent finished launching this batch; fast children may now notify."""
        ready = []
        with self._lock:
            for cohort in list(self._cohorts.values()):
                if cohort.owner_session_id != owner or cohort.parent_trace_id != (trace or "") or cohort.synthesis_fired:
                    continue
                cohort.sealed = True
                if self._all_terminal(cohort):
                    member = next(iter(cohort.members.values()))
                    result = self.on_terminal(member.task_id, status=member.status, error=member.error)
                    if result:
                        ready.append(result)
            self._save()
        return ready

    def _open_cohort(self, owner_session_id: str, parent_trace_id: str) -> _Cohort:
        for cohort in self._cohorts.values():
            if (
                cohort.owner_session_id == owner_session_id
                and cohort.parent_trace_id == parent_trace_id
                and not cohort.synthesis_fired
            ):
                return cohort
        cohort = _Cohort(
            cohort_id=f"cohort-{uuid.uuid4().hex[:12]}",
            owner_session_id=owner_session_id,
            parent_trace_id=parent_trace_id,
        )
        self._cohorts[cohort.cohort_id] = cohort
        return cohort

    @staticmethod
    def _all_terminal(cohort: _Cohort) -> bool:
        if not cohort.members:
            return False
        return all(
            (m.status in TERMINAL_TASK_STATUSES) for m in cohort.members.values()
        )

    def _load(self) -> None:
        assert self.path is not None
        if not self.path.is_file():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw.get("cohorts", []):
            members = {
                mid: CohortMember(**m)
                for mid, m in (item.get("members") or {}).items()
            }
            cohort = _Cohort(
                cohort_id=item["cohort_id"],
                owner_session_id=item["owner_session_id"],
                parent_trace_id=item.get("parent_trace_id") or "",
                members=members,
                synthesis_fired=bool(item.get("synthesis_fired")),
                sealed=bool(item.get("sealed", True)),
                created_at=float(item.get("created_at") or time.time()),
                updated_at=float(item.get("updated_at") or time.time()),
            )
            self._cohorts[cohort.cohort_id] = cohort
            for task_id in members:
                self._task_index[task_id] = cohort.cohort_id

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cohorts": [
                {
                    "cohort_id": c.cohort_id,
                    "owner_session_id": c.owner_session_id,
                    "parent_trace_id": c.parent_trace_id,
                    "synthesis_fired": c.synthesis_fired,
                    "sealed": c.sealed,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "members": {
                        mid: asdict(member) for mid, member in c.members.items()
                    },
                }
                for c in self._cohorts.values()
            ]
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)


def format_cohort_synthesis_message(ready: CohortReady) -> str:
    lines = [
        "[子智能体汇合通知]",
        "同批后台子任务已完成或暂停。请结合状态汇总，暂停/截断不等于完成；不要再使用长超时的 "
        "`background_task_gather` 等待。",
        "如需报告正文，请用 `background_task_gather(task_ids, timeout_seconds=5)` "
        "或 `background_task_output` 短读。",
        "",
        "成员：",
    ]
    for member in ready.members:
        label = member.profile_id or "agent"
        desc = f" — {member.description}" if member.description else ""
        err = f"；error={member.error}" if member.error else ""
        lines.append(
            f"- `{member.task_id}` ({label}){desc}: {member.status}{err}"
        )
    return "\n".join(lines)


def iter_terminal_agent_statuses(
    records: Iterable,
) -> dict[str, tuple[str, str | None]]:
    out: dict[str, tuple[str, str | None]] = {}
    for record in records:
        kind = getattr(record, "kind", None)
        status = getattr(record, "status", None)
        task_id = getattr(record, "id", None)
        if kind != "agent" or status not in TERMINAL_TASK_STATUSES or not task_id:
            continue
        out[str(task_id)] = (str(status), getattr(record, "error", None))
    return out
