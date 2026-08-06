"""Engine assembly from an Agent (Code / Chat / …).

Wires the agent's base tools + permissions + AGENTS.md (workspace agents) + memory +
the skill catalog (progressive disclosure) + load_skill into a TurnEngine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from .agents import Agent, AgentContext, code_agent
from .automation import scheduling_tools
from .selfwake import selfwake_tools
from .subscriptions import subscription_tools
from .config import load_config
from .connectors import (
    connector_list,
    load_settings,
    make_integration_tools,
    make_send_file_tool,
    make_send_message_tool,
)
from .engine import Approver, TurnEngine
from .environment import environment_context
from .memory import MemoryStore, Scope, format_memories, memory_tools
from .permissions import Mode, PermissionEngine
from .project import load_agents_md
from .roots import RootDir, normalize_roots, render_context
from .providers import ProviderClient, ProviderRouter
from .overrides import RiskOverrideStore
from .secrets import SecretStore, state_dir
from .skills import SkillLoader, save_skill_tool, skill_catalog_text, skill_tools
from .tools import ToolRegistry
from .tools.ask import ask_user_tool
from .tools.directories import request_directory_tool
from .tools.plan import propose_plan_tool
from .tools.subagent import explorer_tools
from .web import make_web_fetch_tool, make_web_search_tool
from .workspace_trust import WorkspaceTrustStore
from .tools.shell import LocalExecutor
from .tools.todo import TodoList

# Appended each turn while discuss mode is active: enforcement-only read-only, with no
# pressure toward a plan proposal (that's what distinguishes it from plan mode).
_DISCUSS_MODE_CONTEXT = """\
Discuss mode is active: write and shell tools are disabled. Explore and answer freely; if
the user asks for a change, describe it in chat instead of attempting it (they can switch
to plan or approval mode to have you make it)."""

# Appended to the latest user message every turn while plan mode is active. The mode can
# flip mid-session (plan approval), so this can't live in the static instructions.
_PLAN_MODE_CONTEXT = """\
Plan mode is active: write and shell tools are blocked. Explore read-only and design an
approach. When you've committed to one, present it with `propose_plan` (what you'll change,
in which files, how you'll verify) — don't describe edits as if you were making them. If
the plan is approved, this same session switches to execution and you implement it; if
rejected, revise the plan using the feedback."""

# When-to-remember rules, injected only when a memory store is wired. Without these,
# models either never call `remember` or save noise the repo already records.
_MEMORY_GUIDANCE = """\
Memory:
- You have persistent memory across sessions. Use `remember` for durable facts: the user's \
corrections and stated preferences (include the why), and project context you couldn't \
rederive from the code. Don't save what the repo already records (code structure, git \
history, AGENTS.md) or details that only matter to the current task. Use absolute dates, \
never "yesterday".
- Before saving, check the known-memories list: if an entry already covers it, revise that \
entry with `memory_update` instead of adding a near-duplicate; retire wrong or obsolete \
entries with `memory_forget`.
- Memories reflect when they were written. If one names a file, flag, or URL, verify it \
still exists before relying on it."""

# UX-015 (§33): the GUI interleaves these status lines with humanized tool rows inside a
# collapsed "turn" — they're what the user reads while the agent works. Universal (appended
# for every persona); models that ignore it degrade gracefully to a turn with no narration.
_NARRATION_GUIDANCE = """\
Narration: before each batch of tool calls, write ONE short plain sentence saying what \
you're doing and why (e.g. "Checking what merged since yesterday's digest."). It is shown \
to the user as live progress. Don't narrate trivial single-call follow-ups, don't repeat \
the previous line, and never let narration replace your final answer."""

# ChemClaw long-turn hard guidance (D-073): resume via compacted-history + deliverables.
_LONG_TASK_GUIDANCE = """\
Long-turn research:
- After context compaction/Trim, resume from the injected `<compacted-history>` block \
(summary, working_state, user messages, recent turns). Re-read workspace deliverables or \
re-run tools when needed — do NOT call write_file/create_artifact solely to checkpoint \
scratch memory (that would trigger a write-approval card).
- When delivering the user-facing final report, write a normal deliverable artifact \
(outside `._chemclaw/`) and keep updating the same report file across phases. End the \
reply with a markdown link `[标题](artifact:相对路径.md)` using the exact workspace-relative \
path you wrote — never a bare filename without the link, never `file://`, never an absolute \
OS path. After writing, the chip must open the right-rail preview.
- Do NOT use browser tools (`browser_open_url`, `browser_read_url`, etc.) to verify local \
HTML/Markdown deliverables. `file://` and `localhost`/`127.0.0.1` are blocked by design. \
Validate local pages with static checks (tag balance, script syntax) or rely on the in-app \
artifact preview — never start a local HTTP server just to open it in the browser tool."""

# ChemClaw D-063 / D-071 (M4): shared Mermaid rules for every persona.
# Do not copy into each Agent/Skill. Industry-chain type→shape/color lives in 产业链层级测绘.
_DIAGRAM_GUIDANCE = """\
Mermaid diagrams (all conversations):
- Directed graphs (flowchart/graph/sequenceDiagram): every edge MUST have a semantic label. \
Good: `A -->|"采购"| B` or `A->>B: 请求`. Bad: bare `A --> B`. Default Chinese labels \
(English if the user asked for English). Quote labels with special characters.
- Content first: only include entities and relations you have grounds for. Freely choose \
grouping, node count, and depth from the facts. Do NOT invent nodes or subgraphs for aesthetics \
or to fill a template. If a category has no evidence, omit it.
- Safety: never put citation marks (e.g. [1], [网1]), URLs, or footnotes inside node IDs, \
display names, edge labels, or subgraph titles. Put sources after the fence under a separate \
heading if needed. One statement per line (nodes, edges, style, classDef); never two edges on \
one line. Prefer short safe node IDs; put real names (CAS, /, %, brackets, etc.) in display text.
- Beauty toolbox (optional): when a node type exists, you MAY apply soft low-saturation \
classDef colors; do not add nodes just to use a color. Prefer readable information-design \
style over neon/glow.
- Prefer `graph LR` for value-chain style flows when it fits; do not force a fixed subgraph \
checklist."""

# ChemClaw D-072 (G4): one-line pointer to real process skills — not a parallel "clarify" protocol.
_CLARIFY_POINTER = """\
Clarification: when the user's goal, scope, or deliverable shape is unclear, call `load_skill` \
for a thin process skill such as `grilling` or `grill-me` (one question at a time) instead of \
guessing. Default deliverable format is Markdown. If a polished page might help, ask in plain \
language whether they also want a nicer-looking webpage — do not assume they know what HTML is."""



def _enabled_connector_tools(secrets: SecretStore) -> tuple[set[str], set[str]]:
    connectors = {c["name"]: c for c in connector_list(secrets)}
    enabled_connectors = {
        name
        for name, c in connectors.items()
        if c.get("connected") and c.get("enabled")
    }
    enabled_tools = {
        tool["name"]
        for c in connectors.values()
        if c.get("name") in enabled_connectors
        for tool in c.get("tools", [])
        if tool.get("enabled")
    }
    return enabled_connectors, enabled_tools


def _loaded_skill_names(messages: list[dict[str, Any]]) -> set[str]:
    """Skills whose instructions successfully entered THIS conversation (a load_skill call
    with a non-error result). Drives the disable countermand: a menu quietly shrinking is
    passive, but instructions already in history keep steering the model unless it is
    explicitly asked to stop."""
    import json as _json

    results: dict[str, str] = {}
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_call_id"):
            content = m.get("content")
            results[m["tool_call_id"]] = (
                content if isinstance(content, str) else _json.dumps(content)
            )
    loaded: set[str] = set()
    for m in messages:
        if m.get("role") != "assistant" or not m.get("tool_calls"):
            continue
        for tc in m["tool_calls"]:
            fn = tc.get("function") or {}
            if fn.get("name") != "load_skill":
                continue
            try:
                name = str(_json.loads(fn.get("arguments") or "{}").get("name", ""))
            except Exception:
                continue
            result = results.get(tc.get("id", ""), "")
            if name and '"instructions"' in result:
                loaded.add(name)
    return loaded


def _skill_dirs(workspace: Optional[Path]) -> list[Path]:
    dirs = [state_dir() / "skills"]
    if workspace is not None:
        dirs.append(workspace / ".coworker" / "skills")
    return dirs


def build_engine(
    *,
    agent: Agent,
    workspace: Optional[str | Path] = None,
    model: str = "apihub-cn:deepseek-v4-flash",
    mode: Mode = Mode.INTERACTIVE,
    approver: Optional[Approver] = None,
    provider: Optional[ProviderClient] = None,
    allowed_commands: Optional[list[str]] = None,
    max_iterations: Optional[int] = None,
    model_settings: Optional[dict[str, Any]] = None,
    memory_store: Optional[MemoryStore] = None,
    messages: Optional[list[dict[str, Any]]] = None,
    extra_tools: Optional[list[Any]] = None,
    secrets: Optional[SecretStore] = None,
    task_store: Optional[Any] = None,
    wake_store: Optional[Any] = None,
    session_id: Optional[str] = None,
    audit_sink: Optional[Any] = None,
    roots: Optional[list] = None,
    directory_requester: Optional[Any] = None,
    plan_approver: Optional[Any] = None,
    question_asker: Optional[Any] = None,
    subscription_store: Optional[Any] = None,
    channel_buffer: Optional[Any] = None,
    routing_targets: Optional[list[str]] = None,
    connector_filter: Optional[set[str]] = None,
    # A set (static snapshot) or a zero-arg callable (live, re-evaluated per load_skill).
    skill_filter: Optional[set[str] | Callable[[], set[str]]] = None,
    # Persona frontmatter `skills:` (D-068) — remind the model to load_skill these first.
    default_skill_ids: Optional[list[str]] = None,
) -> TurnEngine:
    ws = Path(workspace).expanduser().resolve() if workspace else None
    if agent.needs_workspace and ws is None:
        raise ValueError(f"agent '{agent.name}' requires a workspace")

    # The session's directories. Explicit `roots` (orphan Cowork: scratch + added folders) wins;
    # otherwise the single workspace is the sole writable root. One shared, mutable list flows to
    # the file tools, the permission engine, and the context injector so add/remove is seen by all.
    if roots:
        root_list: list[RootDir] = normalize_roots(roots)
    elif ws is not None:
        root_list = [RootDir(path=ws, writable=True)]
    else:
        root_list = []

    workspace_trusted = bool(ws and WorkspaceTrustStore().is_trusted(ws))
    config = load_config(ws, workspace_trusted=workspace_trusted)
    executor = (
        LocalExecutor(cwd=ws) if (agent.needs_workspace and ws is not None) else None
    )
    todo = TodoList()
    context = AgentContext(
        workspace=ws, executor=executor, todo=todo, roots=root_list or None
    )

    registry = ToolRegistry()
    registry.register_all(agent.build_tools(context))
    # MCP / connector tools (supplied by the manager) carry their own metadata + schema.
    if extra_tools:
        registry.register_all(extra_tools)
    # Messaging personas (Cowork / Ops / MyHelper) expose send_message; MyHelper also uses it as
    # the reply path for inbound Telegram/Slack super-agent sessions.
    secrets = secrets or SecretStore()
    if agent.messaging and any(s.enabled for s in load_settings(secrets).values()):
        registry.register(make_send_message_tool(secrets))
        # send_file (§34): hand deliverables into the chat — same targets, but its OWN
        # approval surface (a thread's standing send_message grant never covers uploads).
        registry.register(
            make_send_file_tool(secrets, workspace=ws, roots=root_list or None)
        )
        # Channel subscriptions (inbound): listen to a channel, catch up, (un)subscribe. The agent
        # obtains a channel via ask_user or from a channel message it's reacting to.
        if subscription_store is not None and channel_buffer is not None and session_id:
            registry.register_all(
                subscription_tools(
                    subscription_store,
                    session_id,
                    channel_buffer,
                    routing_targets=routing_targets,
                )
            )
    # Knowledge surfaces with a multi-root workspace can ask the user mid-task for another folder.
    if agent.family == "knowledge" and root_list:
        registry.register(request_directory_tool())
    if agent.connectors:
        enabled_connectors, enabled_tools = _enabled_connector_tools(secrets)
        # Per-session connection hierarchy (UI-REFRESH §4.3): when the caller supplies the session's
        # effective connector set, intersect it so only effective-enabled connectors expose tools.
        # Default None preserves CLI / direct callers (no per-session restriction).
        if connector_filter is not None:
            enabled_connectors = enabled_connectors & connector_filter
        registry.register_all(
            make_integration_tools(
                secrets,
                enabled_connectors=enabled_connectors,
                enabled_tools=enabled_tools,
                roots=root_list or None,
            )
        )
    # Web search + fetch: research tools for every agent (keyless DuckDuckGo default).
    registry.register(make_web_search_tool(secrets))
    registry.register(make_web_fetch_tool())
    # ask_user: the universal human-in-the-loop Q&A primitive (every agent; engine-intercepted).
    if question_asker is not None:
        registry.register(ask_user_tool())
    # Route by the model's `provider:` prefix (OpenAI default, Ollama, …). The manager normally
    # passes its shared router; this fallback covers the TUI / direct build_engine() callers.
    # Resolved here (not at engine construction) because the explorer subagent captures it.
    provider = provider or ProviderRouter(secrets, default_provider="openai")
    # Code-family personas can fan broad research out to read-only explorer subagents, keeping
    # their own context for the actual change.
    if agent.family == "code" and ws is not None:
        registry.register_all(
            explorer_tools(
                workspace=ws,
                provider=provider,
                model=model,
                model_settings=model_settings,
            )
        )
    # Scheduling: knowledge surfaces with a workspace can set up scheduled tasks (origin = this
    # session). Code stays out (it fans out to explorers instead).
    if task_store is not None and ws is not None and agent.family == "knowledge":
        origin = {
            "surface": agent.name,
            "session_id": session_id or "",
            "workspace": str(ws),
            "agent": agent.name,
        }
        registry.register_all(
            scheduling_tools(task_store, origin=origin, default_workspace=str(ws))
        )
    # Self-wake: knowledge surfaces can suspend + schedule their own resumption (timer /
    # on-completion / on-event). The scheduler tick resumes due wakes.
    if wake_store is not None and session_id and agent.family == "knowledge":
        registry.register_all(selfwake_tools(wake_store, session_id))

    instructions = (
        f"{agent.system_prompt}\n\n{_NARRATION_GUIDANCE}\n\n"
        f"{_LONG_TASK_GUIDANCE}\n\n"
        f"{_DIAGRAM_GUIDANCE}\n\n{_CLARIFY_POINTER}"
    )
    if default_skill_ids:
        listed = ", ".join(f"`{s}`" for s in default_skill_ids)
        instructions = (
            f"{instructions}\n\nDefault skills for this role: {listed}. "
            "At the start of specialized work, call `load_skill` for each that is still "
            "available in the catalog (skip any that are missing or disabled)."
        )
    if ws is not None:
        instructions = f"{instructions}\n\n{environment_context(ws)}"
        conventions = load_agents_md(ws)
        if conventions:
            instructions = f"{instructions}\n\n{conventions}"

    if memory_store is not None:
        registry.register_all(
            memory_tools(memory_store, workspace=str(ws) if ws else None)
        )
        instructions = f"{instructions}\n\n{_MEMORY_GUIDANCE}"
        remembered = memory_store.list(scope=Scope.GLOBAL)
        if ws is not None:
            remembered += memory_store.list(scope=Scope.WORKSPACE, workspace=str(ws))
        block = format_memories(remembered)
        if block:
            instructions = f"{instructions}\n\n{block}"

    skill_loader = SkillLoader(_skill_dirs(ws))
    # Per-session effective menu (SKILLS-SPEC §3). The manager passes a CALLABLE so
    # load_skill consults the LIVE state per call (a Settings disable applies to running
    # sessions; a skill created after this build is still loadable). The catalog itself
    # is injected per turn via context_provider (below), NOT here — so the menu the model
    # sees is also live: skill changes apply from the next message, no new session needed.
    # Default None preserves CLI / direct callers.
    registry.register_all(skill_tools(skill_loader, allowed=skill_filter))
    # The worker-authors door (SKILLS-SPEC §5.2): save_skill proposes installing a finished
    # skill; requires_approval routes it through the standard approval card, so the review-
    # before-save rule holds without any bespoke plumbing. Bundled files may only come from
    # this session's roots.
    registry.register(
        save_skill_tool(
            allowed_dirs=[r.path for r in (root_list or [])] or ([ws] if ws else [])
        )
    )

    # User-local risk overrides (mainly to relax MCP's conservative default). Empty store →
    # no-op; never written by persona loading (the no-self-grant rule).
    risk_overrides = RiskOverrideStore(state_dir() / "risk_overrides.json").resolver()
    permissions = PermissionEngine(
        workspace_root=ws or (root_list[0].path if root_list else Path.cwd()),
        mode=mode,
        # `[]` is an explicit deny-by-default override, not a request to fall back to config.
        allowed_commands=(
            allowed_commands if allowed_commands is not None else config.allowed_commands
        ),
        auto_allow_tools=set(config.auto_allow),
        roots=root_list or None,
        risk_overrides=risk_overrides,
    )
    # The plan-mode exit door. Always registered (surfaces can flip a live session into
    # plan mode via set_mode, and the registry is fixed at build); the engine rejects the
    # call whenever the session isn't actually in plan mode.
    registry.register(propose_plan_tool())

    # Per-turn ephemeral context, appended to the latest user message since mid-thread system
    # messages aren't reliable across providers. Two producers: the plan-mode reminder (mode can
    # flip mid-session, so it's checked each turn, not baked into the instructions) and the live
    # directory list (orphan Cowork can gain folders mid-session; Cowork/MyHelper only).
    roots_context = (
        (lambda: render_context(root_list))
        if root_list and agent.family == "knowledge"
        else None
    )

    # Late-bound engine ref: the closure needs the conversation history (for the disable
    # countermand) but the engine is constructed after the closure. Filled below.
    _engine_box: list = []

    def context_provider() -> str:
        parts = []
        if permissions.mode is Mode.PLAN:
            parts.append(_PLAN_MODE_CONTEXT)
        elif permissions.mode is Mode.DISCUSS:
            parts.append(_DISCUSS_MODE_CONTEXT)
        if roots_context is not None:
            ctx = roots_context()
            if ctx:
                parts.append(ctx)
        # Live skill menu (SKILLS-SPEC §4.1): recomputed every turn like the roots list, so
        # a skill installed/enabled/disabled mid-session applies from the NEXT MESSAGE —
        # no new session, no lost context.
        skill_loader.rescan()
        allowed = skill_filter() if callable(skill_filter) else skill_filter
        skills_ctx = skill_catalog_text(skill_loader, allowed=allowed)
        if skills_ctx:
            parts.append(skills_ctx)
        # Disable countermand (§3): instructions already loaded into this conversation keep
        # steering the model even after the skill is turned off/deleted — history can't be
        # un-read. So a loaded-but-no-longer-available skill gets an explicit stop note,
        # recomputed fresh each turn (re-enable → the note disappears; never persisted).
        eng = _engine_box[0] if _engine_box else None
        if eng is not None:
            available = set(skill_loader.names()) if allowed is None else set(allowed)
            for name in sorted(_loaded_skill_names(eng.messages) - available):
                parts.append(
                    f'Note: the skill "{name}" has been disabled by the user — stop '
                    "following its instructions from here on."
                )
        return "\n\n".join(parts)

    engine = TurnEngine(
        provider=provider,
        registry=registry,
        permissions=permissions,
        model=model,
        instructions=instructions,
        approver=approver,
        # Stop kills the in-flight foreground shell command, not just the loop.
        interrupt_hooks=[executor.interrupt_now] if executor is not None else None,
        max_iterations=(
            max_iterations if max_iterations is not None else config.max_iterations
        ),
        model_settings=model_settings,
        messages=messages,
        audit_sink=audit_sink,
        context_provider=context_provider,
        directory_requester=directory_requester,
        plan_approver=plan_approver,
        question_asker=question_asker,
    )
    engine.executor = executor  # type: ignore[attr-defined]
    engine.todo = todo  # type: ignore[attr-defined]
    engine.agent_name = agent.name  # type: ignore[attr-defined]
    engine.roots = root_list  # type: ignore[attr-defined]  # shared list; Slice C mutates in place
    engine.audit_context = {
        "session_id": session_id or "",
        "agent": agent.name,
        "workspace": str(ws) if ws else "",
    }
    engine.skill_loader = skill_loader  # type: ignore[attr-defined]
    _engine_box.append(engine)  # late-bind for the countermand (see context_provider)
    return engine


def build_code_engine(**kwargs: Any) -> TurnEngine:
    """Back-compat shim: build the Code agent's engine."""
    return build_engine(agent=code_agent(), **kwargs)
