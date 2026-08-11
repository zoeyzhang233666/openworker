"""Persistent memory — store, index mode, and tools (Wave C Task 6 core)."""

from __future__ import annotations

import sqlite3

from coworker.memory import (
    INDEX_THRESHOLD_CHARS,
    MemoryItem,
    Scope,
    SQLiteMemoryStore,
    format_memories,
    format_memory_index,
    memory_tools,
    render_memory_block,
)
from coworker.tools import ToolRegistry


def _store(tmp_path):
    return SQLiteMemoryStore(tmp_path / "mem.db")


def _items(n, *, content_len=200, with_summary=True):
    return [
        MemoryItem(
            id=i,
            scope=Scope.GLOBAL,
            content=f"fact {i} " + "x" * content_len,
            summary=f"summary {i}" if with_summary else None,
        )
        for i in range(1, n + 1)
    ]


def test_memory_round_trip(tmp_path):
    store = _store(tmp_path)
    item = store.add(
        "prefers tabs over spaces", scope=Scope.WORKSPACE, workspace="/proj"
    )
    assert store.get(item.id).content == "prefers tabs over spaces"
    assert [m.content for m in store.list(workspace="/proj")] == [
        "prefers tabs over spaces"
    ]



def test_workspace_scope_isolation(tmp_path):
    store = _store(tmp_path)
    store.add("A secret", scope=Scope.WORKSPACE, workspace="/proj/a")
    assert store.list(workspace="/proj/b") == []
    assert len(store.list(workspace="/proj/a")) == 1



def test_global_scope_visible_regardless_of_workspace(tmp_path):
    store = _store(tmp_path)
    store.add("use 2-space indent everywhere", scope=Scope.GLOBAL)
    assert len(store.list(scope=Scope.GLOBAL)) == 1



def test_memory_listable_and_editable(tmp_path):
    store = _store(tmp_path)
    item = store.add("old note", scope=Scope.WORKSPACE, workspace="/proj")
    updated = store.update(item.id, "new note")
    assert updated.content == "new note"
    assert store.delete(item.id) is True
    assert store.get(item.id) is None



def test_format_memories_shows_ids(tmp_path):
    store = _store(tmp_path)
    item = store.add("fact one", workspace="/proj")
    rendered = format_memories(store.list(workspace="/proj"))
    assert "fact one" in rendered and "Known memories" in rendered
    assert f"[#{item.id}]" in rendered  # ids let the agent update/forget


# -- summary column + migration (spec §4.1/§7) ---------------------------------



def test_summary_round_trip(tmp_path):
    store = _store(tmp_path)
    item = store.add(
        "prefers short replies — asked for this across all chats",
        scope=Scope.GLOBAL,
        summary="prefers short replies",
    )
    assert store.get(item.id).summary == "prefers short replies"



def test_legacy_db_gains_summary_column(tmp_path):
    """A database created before the summary column existed opens cleanly; old rows
    read back with summary None and new rows carry theirs (no data migration)."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL,
            key TEXT,
            content TEXT NOT NULL,
            workspace TEXT,
            session_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute(
        "INSERT INTO memories (scope, content) VALUES ('global', 'an old fact')"
    )
    conn.commit()
    conn.close()

    store = SQLiteMemoryStore(path)
    old = store.list()[0]
    assert old.content == "an old fact" and old.summary is None
    new = store.add("a new fact", scope=Scope.GLOBAL, summary="new fact")
    assert store.get(new.id).summary == "new fact"



def test_update_can_replace_summary(tmp_path):
    store = _store(tmp_path)
    item = store.add("v1", scope=Scope.GLOBAL, summary="old sum")
    store.update(item.id, "v2", summary="new sum")
    assert store.get(item.id).summary == "new sum"
    # content-only update leaves the summary untouched
    store.update(item.id, "v3")
    assert store.get(item.id).summary == "new sum"



def test_delete_all(tmp_path):
    store = _store(tmp_path)
    store.add("a", scope=Scope.GLOBAL)
    store.add("b", scope=Scope.WORKSPACE, workspace="/proj")
    assert store.delete_all(scope=Scope.GLOBAL) == 1
    assert len(store.list()) == 1
    assert store.delete_all() == 1
    assert store.list() == []


# -- full vs index rendering (spec §7) ------------------------------------------


def test_render_full_under_threshold():
    items = _items(3)
    block = render_memory_block(items)
    assert block == format_memories(items)
    assert "memory_read" not in block  # no index note in full mode



def test_render_flips_to_index_over_threshold():
    items = _items(60)  # ~60 * 210 chars ≫ 8k
    assert len(format_memories(items)) > INDEX_THRESHOLD_CHARS
    block = render_memory_block(items)
    assert "Call memory_read" in block
    # newest 10 (ids 51-60) stay in full; older ones are one-line summaries
    assert f"fact 60 {'x' * 200}" in block
    assert f"fact 50 {'x' * 200}" not in block
    assert "- [#1] summary 1" in block



def test_index_falls_back_to_truncated_content_for_legacy_rows():
    items = _items(60, with_summary=False)
    block = render_memory_block(items)
    # legacy rows (no summary) render a truncated first line, not the whole body
    assert "- [#1] fact 1 " in block
    assert "..." in block
    assert f"fact 1 {'x' * 200}" not in block



def test_index_of_empty_list_is_empty():
    assert format_memory_index([]) == ""
    assert render_memory_block([]) == ""



def test_threshold_boundary_stays_full():
    # A block exactly at the threshold is still full mode (<=, not <).
    items = [MemoryItem(id=1, scope=Scope.GLOBAL, content="x")]
    block = render_memory_block(items, threshold_chars=len(format_memories(items)))
    assert block == format_memories(items)


# -- memory settings store (spec §4.3/§6) ---------------------------------------



def test_remember_tool_persists(tmp_path):
    store = _store(tmp_path)
    reg = ToolRegistry()
    reg.register_all(memory_tools(store, workspace="/proj"))
    assert "remember" in reg.names()

    result = reg.execute("remember", {"content": "deploys on Fridays are banned"})
    assert result["saved"] is True
    assert any(
        m.content == "deploys on Fridays are banned"
        for m in store.list(workspace="/proj")
    )



def test_memory_update_and_forget_tools(tmp_path):
    store = _store(tmp_path)
    reg = ToolRegistry()
    reg.register_all(memory_tools(store, workspace="/proj"))
    assert {"remember", "memory_update", "memory_forget"} <= set(reg.names())

    saved = reg.execute("remember", {"content": "uses npm"})
    updated = reg.execute(
        "memory_update", {"memory_id": saved["id"], "content": "uses pnpm, not npm"}
    )
    assert updated["updated"] is True
    assert store.get(saved["id"]).content == "uses pnpm, not npm"

    gone = reg.execute("memory_forget", {"memory_id": saved["id"]})
    assert gone["deleted"] is True
    assert store.get(saved["id"]) is None



def test_memory_update_and_forget_unknown_id(tmp_path):
    store = _store(tmp_path)
    reg = ToolRegistry()
    reg.register_all(memory_tools(store, workspace="/proj"))
    assert (
        "no memory"
        in reg.execute("memory_update", {"memory_id": 99, "content": "x"})["error"]
    )
    assert "no memory" in reg.execute("memory_forget", {"memory_id": 99})["error"]



def test_remember_summary_scope_and_on_saved(tmp_path):
    """`remember` persists the summary, honors global scope, and fires the toast hook
    with the saved item (spec §5.1)."""
    store = _store(tmp_path)
    seen = []
    reg = ToolRegistry()
    reg.register_all(
        memory_tools(
            store,
            workspace="/proj",
            on_saved=lambda item, previous: seen.append((item, previous)),
        )
    )

    result = reg.execute(
        "remember",
        {"content": "prefers short replies", "summary": "short replies", "scope": "global"},
    )
    assert result["saved"] is True and result["scope"] == "global"
    saved = store.get(result["id"])
    assert saved.scope is Scope.GLOBAL and saved.summary == "short replies"
    assert saved.workspace is None  # global facts aren't pinned to a project
    assert [(item.id, previous) for item, previous in seen] == [(result["id"], None)]



def test_memory_update_announces_itself_with_the_previous_text(tmp_path):
    """The update-don't-duplicate rule sends many saves through `memory_update`, and
    those went unannounced — the user saw nothing and had nothing to undo (owner-hit
    2026-07-28). Updates now notify too, carrying the old text so Undo can restore it."""
    store = _store(tmp_path)
    seen = []
    reg = ToolRegistry()
    reg.register_all(
        memory_tools(
            store,
            workspace="/proj",
            on_saved=lambda item, previous: seen.append((item.content, previous)),
        )
    )

    saved = reg.execute("remember", {"content": "diabetic, lactose-free"})
    reg.execute(
        "memory_update",
        {"memory_id": saved["id"], "content": "diabetic, lactose-free, likes ice cream"},
    )
    assert seen[-1] == ("diabetic, lactose-free, likes ice cream", "diabetic, lactose-free")



def test_on_saved_failure_never_fails_the_save(tmp_path):
    store = _store(tmp_path)

    def explode(_item, _previous):
        raise RuntimeError("socket died")

    reg = ToolRegistry()
    reg.register_all(memory_tools(store, workspace="/proj", on_saved=explode))
    result = reg.execute("remember", {"content": "still saved"})
    assert result["saved"] is True
    assert store.get(result["id"]) is not None



def test_remember_never_saves_session_scope(tmp_path):
    """SESSION is dead scope (spec §3) — a model passing it gets workspace instead."""
    store = _store(tmp_path)
    reg = ToolRegistry()
    reg.register_all(memory_tools(store, workspace="/proj"))
    result = reg.execute("remember", {"content": "x", "scope": "session"})
    assert result["scope"] == "workspace"
    # unknown scopes also fall back to workspace rather than erroring the turn
    assert reg.execute("remember", {"content": "y", "scope": "everywhere"})["scope"] == "workspace"



def test_live_switch_stops_writes_mid_conversation(tmp_path):
    """Turning saving off must apply to conversations ALREADY RUNNING (owner-hit
    2026-07-28: memory turned off mid-chat, the session kept its build-time tools and
    saved anyway). The registry is fixed at build, so the tool stays and refuses."""
    store = _store(tmp_path)
    enabled = {"on": True}
    reg = ToolRegistry()
    reg.register_all(
        memory_tools(store, workspace="/proj", saving_enabled=lambda: enabled["on"])
    )

    saved = reg.execute("remember", {"content": "saved while on"})
    assert saved["saved"] is True

    enabled["on"] = False  # user flips the switch mid-conversation
    blocked = reg.execute("remember", {"content": "must not persist"})
    assert blocked["saved"] is False and "turned off" in blocked["error"]
    assert [m.content for m in store.list(workspace="/proj")] == ["saved while on"]

    # edits and deletes are frozen too — no silent changes while saving is off
    assert reg.execute(
        "memory_update", {"memory_id": saved["id"], "content": "x"}
    )["updated"] is False
    assert reg.execute("memory_forget", {"memory_id": saved["id"]})["deleted"] is False
    assert store.get(saved["id"]).content == "saved while on"

    # ...but reading still works: off means stop learning, not amnesia
    assert reg.execute("memory_read", {"memory_ids": [saved["id"]]})["memories"]

    enabled["on"] = True  # and flipping back on resumes saving at once
    assert reg.execute("remember", {"content": "saved again"})["saved"] is True



def test_memory_read_returns_bodies_and_missing_ids(tmp_path):
    store = _store(tmp_path)
    reg = ToolRegistry()
    reg.register_all(memory_tools(store, workspace="/proj"))
    a = reg.execute("remember", {"content": "full body A", "summary": "A"})
    result = reg.execute("memory_read", {"memory_ids": [a["id"], 999]})
    assert result["memories"] == [
        {"id": a["id"], "scope": "workspace", "content": "full body A"}
    ]
    assert result["missing"] == [999]


# -- sessions -------------------------------------------------------------------


