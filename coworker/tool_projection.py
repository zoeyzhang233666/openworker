"""Provider-visible tool schema projection (HARD STOP E / Section 65 Steps 34–38).

Filters outbound schemas only — never unregister/rebuild the runtime ToolRegistry.
Built-in default tool_projection_enabled is candidate ON (Step 57); callers may override.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable, Optional

from .execution_profile import ExecutionProfile, RequestRoute
from .tool_policy import TurnToolPolicy, filter_tool_names, tool_allowed_under_policy

if TYPE_CHECKING:
    from .tools.registry import ToolRegistry


def select_verified_tool_names(
    text: str, available: Iterable[str]
) -> tuple[str, ...] | None:
    """Pick a minimal VERIFIED subset when safe; None → keep full legacy set.

    Conservative: if no targeted match intersects the registry, return None so
    capabilities are not silently emptied.
    """
    avail = set(available)
    t = (text or "").strip()
    low = t.lower()
    candidates: list[str] = []

    if re.search(
        r"(\bcas\b|cas号|cas\s*号|inchi|smiles|分子式|闪点|熔点|沸点|密度|"
        r"什么化学品|是什么化合物|chemical identity|"
        r"\b\d{2,7}-\d{2}-\d\b)",
        t,
        re.I,
    ):
        candidates.append("lookup_chemical_identity")

    if re.search(r"(汇率|fx\b|exchange rate|usd/?cny|欧元汇率)", t, re.I):
        candidates.append("lookup_fx_rate")

    cn_stock = bool(
        re.search(
            r"(A\s*股|上证|深证|创业板|科创板|沪市|深市|北向|南向|龙虎榜|两融|"
            r"茅台|财务三张|三张表|年报|季报|A-?share)",
            t,
            re.I,
        )
        or re.search(r"\b\d{6}(\.(SH|SZ|SS|BJ))?\b", t, re.I)
    )
    cn_futures = bool(
        re.search(
            r"(甲醇|液化气|工业硅|郑醇|国内期货|中国期货|PTA|沪铜|螺纹钢)",
            t,
            re.I,
        )
        or re.search(
            r"\b(MA|PG|EB|PP|SC|FU|RU|TA|SA|EG|SH|FG|SI|LC|PX|PF|BR|UR|BU)\d{0,4}\b",
            t,
        )
    )
    cn_options = bool(
        re.search(
            r"(期权|50ETF|300ETF|500ETF|科创50ETF|股指期权)",
            t,
            re.I,
        )
    )
    if cn_stock:
        candidates.extend(
            [
                "lookup_cn_stock_quote",
                "lookup_cn_stock_ohlc",
                "lookup_cn_stock_minute",
                "lookup_cn_stock_financials",
                "lookup_cn_stock_feature",
            ]
        )
    if cn_futures:
        candidates.extend(
            [
                "lookup_cn_futures_quote",
                "lookup_cn_futures_ohlc",
                "lookup_cn_futures_minute",
                "lookup_cn_futures_l1",
                "calculate_cn_futures_margin",
            ]
        )
    if cn_options:
        candidates.append("lookup_cn_option_market")

    yahoo_global = bool(
        re.search(
            r"(yahoo|美股|港股|恒生|nasdaq|nyse|wti|brent|\bcl=f\b|\bbz=f\b|"
            r"\baapl\b|\btsla\b|黄金期货|\bgc=f\b)",
            t,
            re.I,
        )
    )
    generic_ohlc = bool(
        re.search(
            r"(期货|原油期货|股票|股价|k线|蜡烛|ohlc|大盘|futures?\b|\bstock\b)",
            t,
            re.I,
        )
    )
    if yahoo_global or (generic_ohlc and not (cn_stock or cn_futures or cn_options)):
        candidates.append("lookup_yahoo_ohlc")

    if re.search(r"(\bvat\b|增值税号|eu\s*vat)", t, re.I):
        candidates.append("validate_eu_vat")

    if re.search(
        r"(企业主体|法定主体|gleif|lei\b|公司注册|legal entity|lei code)",
        t,
        re.I,
    ):
        candidates.append("lookup_legal_entity")

    if re.search(r"(维基|wikipedia)", t, re.I):
        candidates.append("lookup_wikipedia")

    if re.search(
        r"(法规|reach|tsca|危险分类|禁限用|regulation|regulatory)",
        t,
        re.I,
    ):
        for name in (
            "lookup_chemical_identity",
            "web_search",
            "web_fetch",
        ):
            if name not in candidates:
                candidates.append(name)

    if re.search(r"(价格|price|产能|current price)", t, re.I) and not candidates:
        for name in ("web_search", "web_fetch", "lookup_fx_rate"):
            if name not in candidates:
                candidates.append(name)

    # Generic "verify current fact" fallback when risk gate fired but no niche match:
    # prefer chemical identity + web_search if present; else None (legacy full).
    if not candidates and (
        re.search(r"(今天|最新|当前|实时|currently|today)", t, re.I)
        or "exact" in low
    ):
        for name in ("web_search", "web_fetch", "lookup_chemical_identity"):
            if name in avail and name not in candidates:
                candidates.append(name)

    selected = tuple(n for n in candidates if n in avail)
    if not selected:
        return None
    # Preserve deterministic order while unique.
    seen: set[str] = set()
    ordered: list[str] = []
    for n in selected:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return tuple(ordered)


_CONTROL_TOOLS = frozenset(
    {
        "ask_user",
        "propose_plan",
        "request_directory",
        "todo_read",
        "todo_write",
    }
)

_CAPABILITY_PACKS = {
    "workspace": frozenset(
        {
            "read_file",
            "write_file",
            "edit_file",
            "list_dir",
            "list_files",
            "glob",
            "grep",
            "apply_patch",
            "apply_unified_diff",
            "replace_in_file",
            "read_file_lines",
            "run_terminal_cmd",
            "run_shell",
            "bash",
            "shell",
            "shell_task_kill",
            "shell_task_output",
            "git_status",
            "git_diff",
            "git_log",
            "git_show",
        }
    ),
    "memory": frozenset(
        {"remember", "memory_read", "memory_update", "memory_forget"}
    ),
    "skills": frozenset({"search_skills", "load_skill", "save_skill"}),
    "schedule": frozenset(
        {
            "schedule_task",
            "list_scheduled_tasks",
            "cancel_scheduled_task",
            "self_wake",
            "create_wake",
            "list_wakes",
            "cancel_wake",
        }
    ),
    "messages": frozenset({"send_message", "send_file"}),
    "sales": frozenset(
        {
            "calculate_quote",
            "format_lead_list",
            "filter_customs_importers",
            "lookup_trade_flow",
            "search_tenders",
            "search_sam_opportunities",
        }
    ),
}


def select_agent_tool_names(
    text: str, available: Iterable[str]
) -> tuple[str, ...] | None:
    """Select a strong-intent AGENT capability pack, else retain full registry.

    Generic MCP/connector wording and ambiguous actions deliberately return ``None``:
    dynamic tools cannot be classified safely without silently losing capability.
    """
    t = (text or "").strip()
    avail = list(dict.fromkeys(available))
    if not t:
        return None
    if re.search(r"(\bmcp\b|connector|连接器|连接\s*[^，。 ]+)", t, re.I):
        return None

    packs: list[str] = []
    if re.search(
        r"(文件|工作区|workspace|\.md\b|\.py\b|\.csv\b|运行测试|执行命令|"
        r"read|write|edit|modify|save|open|shell|git\b)",
        t,
        re.I,
    ):
        packs.append("workspace")
    if re.search(r"(记住|忘掉|忘记|memory|remember|save .*preference)", t, re.I):
        packs.append("memory")
    if re.search(r"(skill|技能|/skill|load_skill|search_skills)", t, re.I):
        packs.extend(["skills", "workspace"])
    if re.search(r"(提醒我|定时|计划任务|schedule|remind|self-?wake)", t, re.I):
        packs.append("schedule")
    if re.search(r"(发给|发送给|发消息|发邮件|send .* to|message .+)", t, re.I):
        packs.append("messages")
    if re.search(
        r"(hubspot|crm\b|报价|quote|线索|lead|进口商|海关|招标|采购机会)",
        t,
        re.I,
    ):
        packs.append("sales")

    if not packs:
        return None

    wanted = set(_CONTROL_TOOLS)
    for pack in packs:
        wanted.update(_CAPABILITY_PACKS[pack])
    # Registered CRM/message connector tools are capability-namespaced but not all
    # are statically known. Include only after the user explicitly selected that pack.
    if "sales" in packs:
        wanted.update(name for name in avail if name.startswith("hubspot_"))
    if "messages" in packs:
        wanted.update(
            name
            for name in avail
            if name.endswith(("_send_email", "_send_mail", "_send_message"))
        )

    selected = tuple(name for name in avail if name in wanted)
    return selected or None


def project_provider_visible_schemas(
    registry: "ToolRegistry",
    *,
    tool_projection_enabled: bool,
    profile: Optional[ExecutionProfile],
    tool_policy: Optional[TurnToolPolicy] = None,
    mandatory_tool_names: Optional[Iterable[str]] = None,
) -> list[dict] | None:
    """Return provider-visible OpenAI tool schemas, or None for tools=None.

    Kill switch OFF → legacy full registry exposure (still agent/session registered set).
    Does not mutate registry.
    """
    all_schemas = list(registry.schemas())
    if not tool_projection_enabled:
        return all_schemas or None

    if profile is None:
        return all_schemas or None

    policy = tool_policy or TurnToolPolicy()
    mandatory = {n for n in (mandatory_tool_names or ()) if registry.get(n) is not None}

    # Pure FAST_CHAT / KNOWLEDGE: API-level tools=None unless mandatory continuation tools.
    if not profile.tools_enabled or profile.route in (
        RequestRoute.FAST_CHAT,
        RequestRoute.KNOWLEDGE,
    ):
        if not mandatory:
            return None
        names = sorted(mandatory)
        return _schemas_for_names(registry, names) or None

    registered = list(registry.names())

    if profile.allowed_tool_names is None:
        # Conservative AGENT/DEEP (and uncertain VERIFIED): full legacy set.
        candidate_names = list(registered)
    else:
        allowed = set(profile.allowed_tool_names)
        candidate_names = [n for n in registered if n in allowed]

    # Merge mandatory capabilities for this turn.
    for name in mandatory:
        if name not in candidate_names:
            candidate_names.append(name)

    # ToolPolicy final filtering (unified classify_tool / network_scope).
    if policy.no_tools:
        kept = [n for n in candidate_names if n in mandatory]
    else:
        kept = filter_tool_names(candidate_names, policy)
        # Mandatory tools still respect hard no_tools above; otherwise ensure present
        # when policy allows them.
        for name in mandatory:
            if name not in kept and tool_allowed_under_policy(name, policy):
                kept.append(name)

    if not kept:
        return None
    return _schemas_for_names(registry, kept) or None


def _schemas_for_names(registry: "ToolRegistry", names: Iterable[str]) -> list[dict]:
    out: list[dict] = []
    for name in names:
        spec = registry.get(name)
        if spec is not None:
            out.append(spec.schema)
    return out
