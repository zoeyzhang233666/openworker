"""HARD STOP D — Router semantics matrix (no Step 34 tool projection)."""

from __future__ import annotations

import time

import pytest

from coworker.config import Config
from coworker.execution_profile import RequestRoute
from coworker.request_router import (
    ROUTER_TIMEOUT_SECONDS,
    RequestRouter,
    RouterContext,
    decision_to_execution_profile,
    route_request,
)


def _on(**kwargs) -> Config:
    return Config(request_routing_enabled=True, **kwargs)


def _off() -> Config:
    return Config(request_routing_enabled=False)


def test_built_in_request_routing_default_is_on():
    """Section 65 Step 56: built-in default is candidate ON; explicit OFF stays inert."""
    assert Config().request_routing_enabled is True
    assert route_request("你好", config=_off()) is None
    d = route_request("你好", config=Config())
    assert d is not None
    assert d.route is RequestRoute.FAST_CHAT
    assert d.classifier_calls == 0


def test_routing_off_does_not_attach_profile_semantics():
    assert route_request("什么是苯？", config=_off()) is None


# --- FAST_CHAT --------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["你好", "您好", "hi", "hello", "谢谢", "thanks", "好的"],
)
def test_fast_chat_greetings(text):
    d = route_request(text, config=_on())
    assert d is not None
    assert d.route is RequestRoute.FAST_CHAT
    assert d.classifier_calls == 0
    assert d.allowed_tool_names == ()


def test_fast_chat_rewrite_and_email_body():
    d = route_request("帮我润色这句话：今天开会很顺利", config=_on())
    assert d is not None
    assert d.route is RequestRoute.FAST_CHAT
    assert d.classifier_calls == 0

    d2 = route_request("写一封邮件正文，说明交货延迟", config=_on())
    assert d2 is not None
    assert d2.route is RequestRoute.FAST_CHAT


# --- KNOWLEDGE --------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "什么是苯？",
        "解释一下芳香性。",
        "SN1 和 SN2 有什么区别？",
        "详细解释一下苯为什么具有芳香性。",
    ],
)
def test_knowledge_stable_concepts(text):
    d = route_request(text, config=_on())
    assert d is not None
    assert d.route is RequestRoute.KNOWLEDGE
    assert d.route is not RequestRoute.DEEP_RESEARCH
    assert d.allowed_tool_names == ()


# --- VERIFIED ---------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "苯的 CAS 是多少？",
        "100-42-5 是什么物质？",
        "苯的闪点是多少？",
        "REACH 对这个物质有什么限制？",
        "这个 VAT 是否有效？",
        "今天苯价格是多少？",
    ],
)
def test_verified_risk_gate(text):
    d = route_request(text, config=_on())
    assert d is not None
    assert d.route is RequestRoute.VERIFIED
    assert d.source == "risk"


# --- AGENT product / workspace ---------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "读取 pyproject.toml",
        "修改 engine.py",
        "运行测试",
        "分析 CSV",
        "查几家供应商并整理表",
    ],
)
def test_agent_workspace_execution(text):
    d = route_request(text, config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT


@pytest.mark.parametrize(
    "text",
    [
        "记住我以后喜欢简短回答",
        "明天上午 9 点提醒我联系 BASF",
        "把这个结果发给 Jack",
        "用这个 skill 处理",
        "加载 chem-xxx skill",
        "连接 CRM 并创建任务",
    ],
)
def test_agent_product_action_gate(text):
    d = route_request(text, config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.route not in (RequestRoute.FAST_CHAT, RequestRoute.KNOWLEDGE)


# --- DEEP -------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "深度研究全球苯产业链，并交叉验证多个来源",
        "完整研究特种化学品市场并形成行业报告",
        "做 BASF 中国业务尽调",
    ],
)
def test_deep_research(text):
    d = route_request(text, config=_on())
    assert d is not None
    assert d.route is RequestRoute.DEEP_RESEARCH


# --- Tool policies (semantics only) ----------------------------------------


def test_explicit_no_tools_knowledge():
    d = route_request(
        "不用任何工具，只根据已有知识解释苯的芳香性",
        config=_on(),
    )
    assert d is not None
    assert d.route is RequestRoute.KNOWLEDGE
    assert d.tool_policy.no_tools is True


def test_explicit_no_search_keeps_local_file_action():
    d = route_request("不要搜索网络，读取本地 CSV 并总结", config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.tool_policy.no_search is True
    assert d.tool_policy.no_tools is False


def test_no_external_network_plus_local_file():
    d = route_request("不要联网，修改本地 report.md", config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.tool_policy.no_external_network is True
    assert d.tool_policy.no_tools is False
    # Semantics: local file tools remain eligible under helper (not projected here).
    from coworker.tool_policy import filter_tool_names

    kept = filter_tool_names(
        ["read_file", "write_file", "web_search", "lookup_chemical_identity"],
        d.tool_policy,
    )
    assert "read_file" in kept and "write_file" in kept
    assert "web_search" not in kept


def test_conflicting_no_tools_with_file_mutation():
    d = route_request("不用任何工具，把本地文件改掉", config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.tool_policy.no_tools is True


# --- Follow-up inheritance --------------------------------------------------


def test_continuation_inherits_deep_then_thanks_is_fast():
    cfg = _on()
    router = RequestRouter(config=cfg)
    d1 = router.route("深度研究全球 PA66 市场")
    assert d1 is not None and d1.route is RequestRoute.DEEP_RESEARCH

    d2 = router.route("继续")
    assert d2 is not None and d2.route is RequestRoute.DEEP_RESEARCH
    assert d2.source == "inherit"

    d3 = router.route("谢谢")
    assert d3 is not None and d3.route is RequestRoute.FAST_CHAT


def test_continuation_with_new_network_policy():
    cfg = _on()
    router = RequestRouter(config=cfg)
    router.route("深度研究全球 PA66 市场")
    d = router.route("继续，但不要联网")
    assert d is not None
    assert d.route is RequestRoute.DEEP_RESEARCH
    assert d.tool_policy.no_external_network is True


def test_continuation_inherits_agent():
    cfg = _on()
    router = RequestRouter(config=cfg)
    router.route("读取 pyproject.toml 并分析")
    d = router.route("继续查")
    assert d is not None
    assert d.route is RequestRoute.AGENT


# --- Pending / persona / skill ---------------------------------------------


def test_pending_ask_user_short_answer_not_fast_chat():
    d = route_request(
        "A",
        config=_on(),
        context=RouterContext(pending_ask_user=True),
    )
    assert d is not None
    assert d.route is not RequestRoute.FAST_CHAT
    assert d.source == "pending_state"


def test_durable_resume_outranks_router():
    d = route_request(
        "继续",
        config=_on(),
        context=RouterContext(durable_resume=True, last_route=RequestRoute.DEEP_RESEARCH),
    )
    assert d is not None
    assert d.source == "pending_state"
    assert d.route is RequestRoute.AGENT


def test_selected_persona_forces_agent():
    d = route_request(
        "你好",
        config=_on(),
        context=RouterContext(
            selected_persona_id="chain-lobster",
            is_default_persona=False,
        ),
    )
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.source == "override"


def test_forced_skill_forces_agent():
    d = route_request(
        "翻译下面内容：hello",
        config=_on(),
        context=RouterContext(forced_skill_ids=("chem-price-daily",)),
    )
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.source == "override"


# --- Uncertain / classifier -------------------------------------------------


def test_ambiguous_short_command_not_silent_fast_path():
    d = route_request("帮我处理一下这个", config=_on(), classifier=None)
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.route is not RequestRoute.KNOWLEDGE
    assert d.allowed_tool_names is None


def test_unknown_product_like_verb_not_pure_answer():
    d = route_request("继续做完", config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.source in {"product_action", "legacy_fallback"}


def test_classifier_success_used_when_ambiguous():
    def clf(_text: str) -> str:
        return "AGENT"

    # A vague research-ish ask that doesn't hit local gates hard.
    d = route_request(
        "分析一下 BASF 在中国未来的机会",
        config=_on(),
        classifier=clf,
    )
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.source == "classifier"
    assert d.classifier_calls == 1


def test_classifier_timeout_legacy_safe_not_knowledge():
    def slow(_text: str) -> str:
        time.sleep(0.3)
        return "KNOWLEDGE"

    d = route_request(
        "分析一下 BASF 在中国未来的机会",
        config=_on(),
        classifier=slow,
        classifier_timeout_seconds=0.05,
    )
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.source == "legacy_fallback"
    assert d.route is not RequestRoute.KNOWLEDGE
    assert d.classifier_calls == 1


def test_classifier_failure_never_defaults_knowledge():
    def boom(_text: str) -> str:
        raise RuntimeError("provider down")

    d = route_request(
        "分析一下 BASF 在中国未来的机会",
        config=_on(),
        classifier=boom,
    )
    assert d is not None
    assert d.source == "legacy_fallback"
    assert d.route is RequestRoute.AGENT


def test_router_timeout_constant():
    assert ROUTER_TIMEOUT_SECONDS == 5.0


# --- Step 33 ExecutionProfile wiring ----------------------------------------


from coworker.request_router import resolve_execution_profile


def test_resolve_execution_profile_off_is_none():
    assert resolve_execution_profile("你好", config=_off()) is None


def test_resolve_execution_profile_on_returns_pair():
    pair = resolve_execution_profile("你好", config=_on())
    assert pair is not None
    decision, profile = pair
    assert decision.route is RequestRoute.FAST_CHAT
    assert profile.max_iterations == 1
    assert profile.tools_enabled is False


def test_decision_wires_execution_profile_ceilings_and_soft_targets():
    cfg = _on()
    fast = route_request("你好", config=cfg)
    assert fast is not None
    pf = decision_to_execution_profile(fast, cfg)
    assert pf.route is RequestRoute.FAST_CHAT
    assert pf.max_iterations == 1
    assert pf.tools_enabled is False
    assert pf.target_iterations is None
    assert pf.reasoning_mode == "off"

    know = route_request("什么是苯？", config=cfg)
    assert know is not None
    pk = decision_to_execution_profile(know, cfg)
    assert pk.route is RequestRoute.KNOWLEDGE
    assert pk.max_iterations == 1
    assert pk.tools_enabled is False

    ver = route_request("苯的 CAS 是多少？", config=cfg)
    assert ver is not None
    pv = decision_to_execution_profile(ver, cfg)
    assert pv.route is RequestRoute.VERIFIED
    assert pv.max_iterations == 6
    assert pv.tools_enabled is True

    agent = route_request("记住我喜欢简短回答", config=cfg)
    assert agent is not None
    pa = decision_to_execution_profile(agent, cfg)
    assert pa.route is RequestRoute.AGENT
    assert pa.max_iterations == 150
    assert pa.target_iterations == 32
    assert pa.tools_enabled is True
    assert pa.allowed_tool_names is None  # AGENT keeps full legacy set

    deep = route_request("深度研究全球苯产业链，并交叉验证多个来源", config=cfg)
    assert deep is not None
    pd = decision_to_execution_profile(deep, cfg)
    assert pd.route is RequestRoute.DEEP_RESEARCH
    assert pd.max_iterations == 150
    assert pd.target_iterations == 50


def test_verified_sets_targeted_allowed_tools():
    d = route_request("苯的 CAS 是多少？", config=_on())
    assert d is not None
    assert d.route is RequestRoute.VERIFIED
    assert d.allowed_tool_names == ("lookup_chemical_identity",)
    profile = decision_to_execution_profile(d, _on())
    assert profile.allowed_tool_names == ("lookup_chemical_identity",)


def test_routing_on_agent_keeps_full_allowed_none():
    """AGENT/DEEP keep allowed_tool_names=None (conservative full legacy)."""
    d = route_request("读取本地文件并总结", config=_on())
    assert d is not None
    assert d.route is RequestRoute.AGENT
    assert d.allowed_tool_names is None
    profile = decision_to_execution_profile(d, _on())
    assert profile.allowed_tool_names is None
