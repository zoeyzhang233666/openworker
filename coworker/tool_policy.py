"""Turn-level tool/network policy helpers (HARD STOP D/E).

Pure internal classification — not a product capability authority.
Provider-visible schema projection lives in tool_projection.py (Step 34+).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NetworkScope(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class UsageClass(str, Enum):
    SEARCH = "search"
    PRODUCT_CONTROL = "product_control"
    FILE = "file"
    MEMORY = "memory"
    SKILL = "skill"
    OTHER = "other"


@dataclass(frozen=True)
class TurnToolPolicy:
    """Orthogonal constraints — do not collapse into a single route."""

    no_tools: bool = False
    no_search: bool = False
    no_external_network: bool = False


# Explicit known mappings. Unknown custom names → UNKNOWN/OTHER (conservative).
_REMOTE_SEARCH = frozenset(
    {
        "web_search",
        "github_search",
        "gmail_search_messages",
        "outlook_search_messages",
        "jira_search_issues",
        "confluence_search",
        "zendesk_search",
        "linear_search_issues",
        "gitlab_search",
        "asana_search_tasks",
        "hubspot_search",
        "dropbox_search",
        "box_search",
        "search_tenders",
        "search_sam_opportunities",
        "search_huagongshe",
    }
)

_REMOTE_OTHER = frozenset(
    {
        "web_fetch",
        "browser_read_url",
        "lookup_chemical_identity",
        "lookup_legal_entity",
        "validate_eu_vat",
        "lookup_fx_rate",
        "lookup_yahoo_ohlc",
        "lookup_wikipedia",
        "lookup_huagongshe_chemical",
        "fetch_huagongshe_svg",
        "validate_huagongshe_reaction",
        "create_huagongshe_reaction",
        "lookup_trade_flow",
        "send_message",
        "send_file",
        "gmail_send_email",
        "outlook_send_mail",
        "discord_send_message",
        "whatsapp_send_message",
        "hubspot_create_contact",
        "hubspot_update_object",
        "hubspot_log_note",
        "hubspot_create_task",
        "hubspot_get_object",
        "github_get_issue",
        "github_create_issue",
        "github_reply",
        "github_review",
        "github_list_commits",
        "github_clone",
        "github_pull",
        "gmail_get_message",
        "gcal_list_events",
        "gcal_free_busy",
        "gcal_create_event",
        "gcal_update_event",
        "gcal_delete_event",
        "outlook_list_events",
        "outlook_create_event",
        "outlook_update_event",
        "outlook_delete_event",
        "outlook_respond_event",
        "jira_get_issue",
        "jira_create_issue",
        "confluence_get_page",
        "confluence_create_page",
        "zendesk_get_ticket",
        "zendesk_create_ticket",
        "linear_get_issue",
        "linear_list_teams",
        "linear_create_issue",
        "gitlab_get_issue",
        "gitlab_get_merge_request",
        "gitlab_create_issue",
        "discord_list_channels",
        "discord_read_messages",
        "stripe_search_customers",
        "stripe_list_charges",
        "stripe_list_invoices",
        "asana_list_workspaces",
        "asana_get_task",
        "asana_create_task",
        "dropbox_list_folder",
        "dropbox_read_file",
        "box_list_folder",
        "box_read_file",
        "quickbooks_query",
        "quickbooks_list_customers",
        "quickbooks_list_invoices",
        "quickbooks_get_report",
    }
)

_LOCAL_FILE = frozenset(
    {
        "read_file",
        "write_file",
        "edit_file",
        "list_dir",
        "list_files",
        "glob",
        "apply_patch",
        "apply_unified_diff",
        "replace_in_file",
        "read_file_lines",
        "filter_customs_importers",
    }
)

_LOCAL_SEARCH = frozenset({"grep"})

_LOCAL_MEMORY = frozenset(
    {"remember", "memory_read", "memory_update", "memory_forget"}
)

_LOCAL_SKILL = frozenset({"load_skill", "save_skill"})

_LOCAL_PRODUCT_CONTROL = frozenset(
    {
        "ask_user",
        "propose_plan",
        "request_directory",
        "todo_write",
        "todo_read",
        "schedule_task",
        "list_scheduled_tasks",
        "cancel_scheduled_task",
        "self_wake",
        "create_wake",
        "list_wakes",
        "cancel_wake",
        "calculate_quote",
        "format_lead_list",
    }
)

_LOCAL_OTHER = frozenset(
    {
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
)


def classify_tool(name: str) -> tuple[NetworkScope, UsageClass]:
    """Centralized network_scope / usage_class. Unknown → UNKNOWN + OTHER."""
    n = (name or "").strip()
    if not n:
        return NetworkScope.UNKNOWN, UsageClass.OTHER

    if n in _REMOTE_SEARCH:
        return NetworkScope.REMOTE, UsageClass.SEARCH
    if n in _REMOTE_OTHER:
        return NetworkScope.REMOTE, UsageClass.OTHER
    if n.startswith("mcp_") or n.startswith("connector_"):
        return NetworkScope.REMOTE, UsageClass.OTHER

    if n in _LOCAL_FILE:
        return NetworkScope.LOCAL, UsageClass.FILE
    if n in _LOCAL_SEARCH:
        return NetworkScope.LOCAL, UsageClass.SEARCH
    if n in _LOCAL_MEMORY:
        return NetworkScope.LOCAL, UsageClass.MEMORY
    if n in _LOCAL_SKILL:
        return NetworkScope.LOCAL, UsageClass.SKILL
    if n in _LOCAL_PRODUCT_CONTROL:
        return NetworkScope.LOCAL, UsageClass.PRODUCT_CONTROL
    if n in _LOCAL_OTHER:
        return NetworkScope.LOCAL, UsageClass.OTHER

    # Heuristic prefixes for local workspace / product tools.
    if n.startswith(("read_", "write_", "edit_", "list_", "glob")):
        return NetworkScope.LOCAL, UsageClass.FILE
    if n.startswith("memory_") or n in {"remember"}:
        return NetworkScope.LOCAL, UsageClass.MEMORY
    if "skill" in n:
        return NetworkScope.LOCAL, UsageClass.SKILL

    return NetworkScope.UNKNOWN, UsageClass.OTHER


def tool_allowed_under_policy(name: str, policy: TurnToolPolicy) -> bool:
    """Pure eligibility check used by tool projection."""
    if policy.no_tools:
        return False
    scope, usage = classify_tool(name)
    if policy.no_search and usage is UsageClass.SEARCH:
        return False
    if policy.no_external_network:
        if scope is NetworkScope.REMOTE:
            return False
        if scope is NetworkScope.UNKNOWN:
            # Safe default: cannot sneak network via unclassified tools.
            return False
    return True


def filter_tool_names(
    names: list[str] | tuple[str, ...], policy: TurnToolPolicy
) -> list[str]:
    """Return names kept under policy (shared by projection)."""
    return [n for n in names if tool_allowed_under_policy(n, policy)]
