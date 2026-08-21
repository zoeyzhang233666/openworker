"""Request router — optimization layer for answer/execution intensity (HARD STOP D/E).

Not a product capability authority. Provider-visible schema projection is gated by
tool_projection_enabled (independent kill switch; Step 57 candidate ON).
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass, field, replace
from typing import Callable

from .config import Config
from .execution_profile import ExecutionProfile, RequestRoute, make_execution_profile
from .tool_policy import TurnToolPolicy
from .tool_projection import select_verified_tool_names

ROUTER_TIMEOUT_SECONDS = 5.0

# Universe for VERIFIED targeting before registry intersection (Step 35).
_VERIFIED_TOOL_UNIVERSE = frozenset(
    {
        "lookup_chemical_identity",
        "lookup_fx_rate",
        "validate_eu_vat",
        "lookup_legal_entity",
        "lookup_wikipedia",
        "web_search",
        "web_fetch",
    }
)

ClassifierFn = Callable[[str], str]

_CLASSIFIER_PROMPT = """Classify the user's CURRENT request into exactly one category:

FAST_CHAT
- Greetings, acknowledgements, writing, rewriting, translation,
  summarization of supplied content, brainstorming, or trivial conversation,
  only when no product action/tool execution is required.

KNOWLEDGE
- Stable non-current knowledge that can reasonably be answered directly.
  Includes conceptual chemistry explanations that do not require exact external verification
  and do not require a ChemClaw product action.

VERIFIED
- A short or moderate request where one or a few precise facts should be checked
  using authoritative external/domain tools. Includes chemical identity, exact properties,
  safety, regulations, legal/entity status, current prices, or time-sensitive facts.

AGENT
- Requires product actions or execution: memory, scheduling, messaging, skills,
  workspace/file operations, coding, connectors, MCP, multiple tools,
  multi-step execution, or moderate research.

DEEP_RESEARCH
- Explicitly asks for comprehensive multi-source investigation, due diligence,
  systematic research, or a substantial research report.

Rules:
- Never classify a known pending interaction/resume as FAST_CHAT or KNOWLEDGE.
- Product actions belong to AGENT even when the user message is short.
- Prefer FAST_CHAT/KNOWLEDGE only when no external evidence and no product action are materially required.
- Prefer VERIFIED over AGENT when a small number of targeted checks is enough and no additional product action is requested.
- Prefer AGENT over DEEP_RESEARCH unless deep research is explicit.
- Do not use DEEP_RESEARCH merely because the user says "detailed".
- Return exactly one token:
FAST_CHAT
KNOWLEDGE
VERIFIED
AGENT
DEEP_RESEARCH
"""

_ROUTE_TOKEN = {
    "FAST_CHAT": RequestRoute.FAST_CHAT,
    "KNOWLEDGE": RequestRoute.KNOWLEDGE,
    "VERIFIED": RequestRoute.VERIFIED,
    "AGENT": RequestRoute.AGENT,
    "DEEP_RESEARCH": RequestRoute.DEEP_RESEARCH,
}


@dataclass(frozen=True)
class RouteDecision:
    route: RequestRoute
    source: str
    reason: str
    confidence: float = 1.0
    allowed_tool_names: tuple[str, ...] | None = None
    tool_policy: TurnToolPolicy = field(default_factory=TurnToolPolicy)
    classifier_calls: int = 0


@dataclass(frozen=True)
class RouterContext:
    """Signals that outrank local fast/knowledge heuristics."""

    pending_ask_user: bool = False
    pending_approval: bool = False
    pending_plan: bool = False
    pending_request_directory: bool = False
    durable_resume: bool = False
    unanswered_trailing_tool_calls: bool = False
    # Non-default selected persona (e.g. chain-lobster / sales lobsters).
    selected_persona_id: str | None = None
    is_default_persona: bool = True
    forced_skill_ids: tuple[str, ...] = ()
    default_skill_active: bool = False
    last_route: RequestRoute | None = None
    # Explicit product-control / stop signals already owned by engine.
    stop_requested: bool = False


@dataclass
class RequestRouter:
    """Stateful router (tracks last_route for continuation inheritance)."""

    config: Config
    classifier: ClassifierFn | None = None
    classifier_timeout_seconds: float = ROUTER_TIMEOUT_SECONDS
    _last_route: RequestRoute | None = field(default=None, init=False, repr=False)

    @property
    def last_route(self) -> RequestRoute | None:
        return self._last_route

    def remember_route(self, route: RequestRoute) -> None:
        self._last_route = route

    def route(
        self, text: str, *, context: RouterContext | None = None
    ) -> RouteDecision | None:
        """Return None when routing kill switch is OFF (legacy-inert)."""
        if not self.config.request_routing_enabled:
            return None
        ctx = context or RouterContext()
        if ctx.last_route is None and self._last_route is not None:
            ctx = replace(ctx, last_route=self._last_route)
        decision = _route_enabled(text, config=self.config, context=ctx, router=self)
        self._last_route = decision.route
        return decision


def route_request(
    text: str,
    *,
    config: Config,
    context: RouterContext | None = None,
    classifier: ClassifierFn | None = None,
    classifier_timeout_seconds: float = ROUTER_TIMEOUT_SECONDS,
) -> RouteDecision | None:
    """Stateless entry: None when request_routing_enabled is False."""
    if not config.request_routing_enabled:
        return None
    router = RequestRouter(
        config=config,
        classifier=classifier,
        classifier_timeout_seconds=classifier_timeout_seconds,
    )
    return router.route(text, context=context)


def decision_to_execution_profile(
    decision: RouteDecision, config: Config
) -> ExecutionProfile:
    """Step 33/35: wire hard ceiling + soft targets + optional VERIFIED tool subset.

    TurnToolPolicy remains on RouteDecision; projection consumes both when
    tool_projection_enabled is ON.
    """
    return make_execution_profile(
        decision.route,
        config,
        allowed_tool_names=decision.allowed_tool_names,
    )


def resolve_execution_profile(
    text: str,
    *,
    config: Config,
    context: RouterContext | None = None,
    classifier: ClassifierFn | None = None,
    classifier_timeout_seconds: float = ROUTER_TIMEOUT_SECONDS,
) -> tuple[RouteDecision, ExecutionProfile] | None:
    """When routing is ON, return (decision, profile). When OFF, None (legacy-inert).

    Does not mutate tool registries or provider-visible schemas.
    """
    decision = route_request(
        text,
        config=config,
        context=context,
        classifier=classifier,
        classifier_timeout_seconds=classifier_timeout_seconds,
    )
    if decision is None:
        return None
    return decision, decision_to_execution_profile(decision, config)


# --- guards & gates ---------------------------------------------------------


def _has_pending(ctx: RouterContext) -> bool:
    return bool(
        ctx.pending_ask_user
        or ctx.pending_approval
        or ctx.pending_plan
        or ctx.pending_request_directory
        or ctx.durable_resume
        or ctx.unanswered_trailing_tool_calls
    )


def _persona_or_skill_guard(ctx: RouterContext) -> bool:
    if ctx.forced_skill_ids:
        return True
    if ctx.default_skill_active:
        return True
    if ctx.selected_persona_id and not ctx.is_default_persona:
        return True
    return False


def _detect_tool_policy(text: str) -> TurnToolPolicy:
    t = text.strip()
    low = t.lower()
    no_tools = bool(
        re.search(
            r"(不用任何工具|不要使用任何工具|不要用任何工具|不使用工具|no tools|"
            r"without (any )?tools|don't use (any )?tools|do not use (any )?tools)",
            t,
            re.I,
        )
    )
    no_search = bool(
        re.search(
            r"(不要搜索|别搜索|不要搜网|不要搜索网络|no search|don't search|"
            r"do not search|without searching|不要上网搜)",
            t,
            re.I,
        )
    )
    no_net = bool(
        re.search(
            r"(不要联网|别联网|禁止联网|不联网|不要访问网络|no (external )?network|"
            r"don't (go )?online|do not (go )?online|offline only|without (the )?network|"
            r"without internet|no internet)",
            t,
            re.I,
        )
    )
    # "不要搜索网络" is search, not necessarily full network ban — already no_search.
    # Stronger "不要联网" sets no_external_network.
    if "不要搜索网络" in t and "不要联网" not in t:
        no_net = False
    # English "don't search the web" → no_search
    if re.search(r"don'?t search (the )?(web|internet|network)", low):
        no_search = True
    return TurnToolPolicy(
        no_tools=no_tools, no_search=no_search, no_external_network=no_net
    )


_PRODUCT_ACTION_PATTERNS = [
    # memory
    r"(记住|忘掉|忘记|保存偏好|remember (this|that|my)|forget (this|that)|save (my )?preference)",
    # schedule / wake
    r"(提醒我|定时|计划任务|明天.*提醒|self-?wake|schedule|remind me|set (a )?reminder)",
    # messaging
    r"(发给|发送给|发消息|发邮件给|send (this |it )?(to|an? email)|message .+|发给\s*\w+)",
    # connectors / MCP / CRM
    r"(连接|connector|mcp\b|hubspot|创建联系人|crm|创建任务)",
    # files / workspace
    r"(读取|打开|修改|写入|保存到|写进|写到).*(文件|file|\.md|\.py|\.csv|report|"
    r"pyproject|engine\.py)|"
    r"(read|write|edit|modify|save|open).*(file|\.md|\.py|\.csv|report|local)|"
    r"(读取|分析|总结).*(csv|本地|CSV)|"
    r"(分析\s*CSV|读取\s*pyproject|修改\s*engine)|"
    r"(本地文件|workspace|工作区)",
    # multi-step research deliverable (still AGENT, not silent VERIFIED)
    r"(查几家|整理表|整理成表|比较几家|筛选进口商)",
    # code / shell
    r"(运行测试|跑测试|run tests?|执行命令|shell|bash|修改\s*engine)",
    # skills
    r"((加载|运行|使用).*(skill|技能)|/skill|load_skill|用这个 skill|用指定 skill)",
    # ask / directory / approval style product controls
    r"(请求目录|request_directory|需要审批|ask_user)",
]


def _product_action_suspected(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    for pat in _PRODUCT_ACTION_PATTERNS:
        if re.search(pat, t, re.I):
            return True
    # Ambiguous short commands that must NOT become pure-answer.
    if re.fullmatch(
        r"(帮我处理一下这个|处理一下|继续做完|搞定这个|弄一下|"
        r"handle this|do this|fix it|take care of this)",
        t,
        re.I,
    ):
        return True
    return False


_GREETING_RE = re.compile(
    r"^(你好|您好|嗨|哈喽|hi|hello|hey|谢谢|thanks|thank you|好的|ok|okay|"
    r"明白|收到|再见|拜拜|bye|goodbye|morning|good morning|good night)[!！。.~…]*$",
    re.I,
)

_PURE_REWRITE_RE = re.compile(
    r"(润色|改写|翻译|译成|翻成|写一封邮件正文|写一封邮件(?!.*发)|"
    r"给我想几个标题|想几个标题|帮我润色|polish|rewrite|rephrase|"
    r"translate|summarize|摘要一下|总结一下下面|格式调整)",
    re.I,
)

_KNOWLEDGE_RE = re.compile(
    r"(什么是|为什么|有什么区别|解释一下|详细解释|芳香性|酯化反应|"
    r"sn1|sn2|什么叫|概念|原理|"
    r"what is|why (does|is|are)|difference between|explain)",
    re.I,
)

_CAS_NUMBER_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")

_VERIFIED_REQUIRED_RE = re.compile(
    r"(\bcas\b|cas号|cas\s*号|inchi|smiles|分子式|闪点|熔点|沸点|密度|蒸气压|"
    r"爆炸极限|危险分类|毒性|致癌|易燃|reach|tsca|危险化学品|运输分类|"
    r"禁限用|法规|vat\b|汇率|fx\b|价格|产能|今天|最新|当前|实时|"
    r"最近|目前|是否仍在运营|公司注册|"
    r"flash\s*point|melting\s*point|boiling\s*point|molecular\s*formula|"
    r"current (price|rate|status)|today'?s|regulation)",
    re.I,
)

_VERIFIED_PREFER_RE = re.compile(
    r"(分子量|精确|exact (value|number|mass)|precise)",
    re.I,
)

_DEEP_RE = re.compile(
    r"(深度研究|全面调研|尽职调查|尽调|完整行业报告|完整研究|形成行业报告|"
    r"市场研究报告|竞争格局报告|产业链|上下游|套利怎么做|"
    r"研究.{0,20}套利|套利.{0,20}(研究|策略|方法)|"
    r"多来源研究|交叉验证多个来源|systematic research|deep research|"
    r"due diligence|comprehensive (market )?report)",
    re.I,
)

_CONTINUATION_RE = re.compile(
    r"^(继续|接着|继续查|继续研究|再往下|再补几个|go on|continue|keep going)"
    r"(，|,|。|!|！| but| 但)?",
    re.I,
)


def _is_pure_answer_fast(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _GREETING_RE.match(t):
        return True
    # Pure rewrite/translate only when content appears supplied or task is generative-only.
    if _PURE_REWRITE_RE.search(t) and not _product_action_suspected(t):
        # "发给" already caught by product action; "写一封邮件正文" ok.
        if re.search(r"(发给|发送给|发邮件给|send .+ to)", t, re.I):
            return False
        return True
    return False


def _is_pure_answer_knowledge(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _product_action_suspected(t):
        return False
    if _VERIFIED_REQUIRED_RE.search(t):
        return False
    if _DEEP_RE.search(t):
        return False
    # Conceptual chemistry / stable knowledge — positive patterns.
    if _KNOWLEDGE_RE.search(t):
        # Prefer: "什么是苯" / aromaticity / SN1 vs SN2 — not identity lookup.
        if re.search(r"(cas|闪点|reach|价格|vat)", t, re.I):
            return False
        return True
    return False


def _verification_level(text: str) -> str:
    """Return none | prefer | required."""
    if _CAS_NUMBER_RE.search(text) or _VERIFIED_REQUIRED_RE.search(text):
        return "required"
    if _VERIFIED_PREFER_RE.search(text):
        return "prefer"
    return "none"


def _is_continuation(text: str) -> bool:
    t = text.strip()
    if _CONTINUATION_RE.match(t):
        return True
    # Short continuation tokens
    return bool(re.fullmatch(r"(继续|接着|continue|go on)([。.!！…]*)", t, re.I))


def _parse_classifier_token(raw: str) -> RequestRoute | None:
    token = (raw or "").strip().upper().replace("-", "_")
    # Allow trailing punctuation / first line only.
    first = re.split(r"[\s\n,.;]+", token, maxsplit=1)[0]
    return _ROUTE_TOKEN.get(first)


def _run_classifier(
    text: str,
    *,
    classifier: ClassifierFn | None,
    timeout: float,
) -> tuple[RequestRoute | None, int, str]:
    """Returns (route_or_None, calls, failure_reason). At most one call."""
    if classifier is None:
        return None, 0, "no_classifier"

    def _call() -> str:
        return classifier(text)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_call)
            raw = fut.result(timeout=timeout)
    except FuturesTimeout:
        return None, 1, "classifier_timeout"
    except Exception as exc:  # noqa: BLE001 — legacy-safe fallback
        return None, 1, f"classifier_error:{type(exc).__name__}"

    parsed = _parse_classifier_token(raw)
    if parsed is None:
        return None, 1, "classifier_parse_failure"
    return parsed, 1, ""


def _route_enabled(
    text: str,
    *,
    config: Config,
    context: RouterContext,
    router: RequestRouter,
) -> RouteDecision:
    policy = _detect_tool_policy(text)
    t = text.strip()

    # 1. Pending-state guard
    if _has_pending(context) or context.stop_requested:
        return RouteDecision(
            route=RequestRoute.AGENT,
            source="pending_state",
            reason="pending interaction / durable resume / stop outranks router",
            tool_policy=policy,
            allowed_tool_names=None,
        )

    # 2. Selected persona / forced skill guard
    if _persona_or_skill_guard(context):
        return RouteDecision(
            route=RequestRoute.AGENT,
            source="override",
            reason="selected persona or forced/default skill requires legacy-compatible tools",
            tool_policy=policy,
            allowed_tool_names=None,
        )

    # 3. Product action gate (before pure-answer)
    if _product_action_suspected(t):
        # Conflicting: no_tools + explicit file mutation still AGENT + policy preserved.
        return RouteDecision(
            route=RequestRoute.AGENT,
            source="product_action",
            reason="product action / workspace / memory / schedule / messaging detected",
            tool_policy=policy,
            allowed_tool_names=None,
        )

    # 4. Explicit tool/network policy already captured in `policy`.
    # 5. Continuation inheritance (after guards; before pure-answer for "继续")
    if _is_continuation(t) and context.last_route is not None:
        return RouteDecision(
            route=context.last_route,
            source="inherit",
            reason="continuation inherits prior route",
            tool_policy=policy,
            allowed_tool_names=None,
        )

    # 6. Pure-answer positive eligibility → FAST_CHAT
    if _is_pure_answer_fast(t):
        return RouteDecision(
            route=RequestRoute.FAST_CHAT,
            source="local",
            reason="positive pure-answer whitelist (greeting/rewrite/translate)",
            tool_policy=policy,
            allowed_tool_names=(),
            classifier_calls=0,
        )

    # 7. Deep research explicit intent
    if _DEEP_RE.search(t):
        return RouteDecision(
            route=RequestRoute.DEEP_RESEARCH,
            source="local",
            reason="explicit deep-research intent",
            tool_policy=policy,
            allowed_tool_names=None,
        )

    # 8. Chemical / current-fact risk gate
    vlevel = _verification_level(t)
    if vlevel in ("required", "prefer"):
        verified_tools = select_verified_tool_names(t, _VERIFIED_TOOL_UNIVERSE)
        return RouteDecision(
            route=RequestRoute.VERIFIED,
            source="risk",
            reason=(
                "chemical identity / safety / regulation / current fact requires verification"
                if vlevel == "required"
                else "exact property prefers verified lookup"
            ),
            tool_policy=policy,
            allowed_tool_names=verified_tools,
        )

    # 9. Pure-answer knowledge (stable conceptual)
    if _is_pure_answer_knowledge(t):
        # If user demanded no_tools / no_search, still KNOWLEDGE.
        return RouteDecision(
            route=RequestRoute.KNOWLEDGE,
            source="local",
            reason="stable pure-answer knowledge whitelist",
            tool_policy=policy,
            allowed_tool_names=(),
            classifier_calls=0,
        )

    # 10. Tiny classifier for remaining ambiguous cases
    route, calls, fail = _run_classifier(
        t,
        classifier=router.classifier,
        timeout=router.classifier_timeout_seconds,
    )
    if route is not None:
        # Classifier must not invent tools=None for uncertain product-like paths:
        # only FAST/KNOWLEDGE keep empty allowed tools when positively classified.
        allowed: tuple[str, ...] | None
        if route in (RequestRoute.FAST_CHAT, RequestRoute.KNOWLEDGE):
            allowed = ()
        elif route is RequestRoute.VERIFIED:
            allowed = select_verified_tool_names(t, _VERIFIED_TOOL_UNIVERSE)
        else:
            allowed = None
        return RouteDecision(
            route=route,
            source="classifier",
            reason="tiny classifier",
            tool_policy=policy,
            allowed_tool_names=allowed,
            classifier_calls=calls,
            confidence=0.7,
        )

    # 11. Legacy-safe fallback — NEVER default to KNOWLEDGE
    return RouteDecision(
        route=RequestRoute.AGENT,
        source="legacy_fallback",
        reason=fail or "uncertain; preserve legacy tool capability",
        tool_policy=policy,
        allowed_tool_names=None,
        classifier_calls=calls,
        confidence=0.0,
    )


def classifier_prompt() -> str:
    return _CLASSIFIER_PROMPT
