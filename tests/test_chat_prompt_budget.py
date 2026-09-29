"""Offline requests through the real engine; no credentials or remote calls."""
import asyncio
from copy import deepcopy
from pathlib import Path

import pytest

from coworker.agent import build_engine, _INLINE_CHART_GUIDANCE
from coworker.agents import cowork_agent
from coworker.context_budget import estimate
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient
from coworker.skills import SkillLoader, skill_catalog_text
from coworker.tools.registry import ToolRegistry
from coworker.skills.base import skill_tools


class Recorder(ProviderClient):
    def complete(self, **kwargs):
        self.request = deepcopy(kwargs)
        return AssistantTurn(text="完成", finish_reason="stop")

    def capabilities(self, model):
        return ModelCapabilities()


@pytest.mark.parametrize("query", ["你好", "研究甲醇的现货和期货走势"])
def test_common_prompt_is_bounded_without_keyword_routing(tmp_path, query):
    provider = Recorder()
    bundled = Path(__file__).parents[1] / "coworker/skills/bundled"
    e = build_engine(agent=cowork_agent(), workspace=tmp_path, provider=provider,
                     skill_dirs=[bundled], user_rules="始终保留用户规则 TEST_RULE")
    async def run():
        return [event async for event in e.run(query)]
    try:
        events = asyncio.run(run())
        assert events[-1].data["status"] == "completed"
        req = provider.request
        names = {s["function"]["name"] for s in req["tools"]}
        assert {"web_search", "web_fetch", "search_tools", "load_tools", "search_skills",
                "load_skill", "get_chart_guidance"} <= names
        system = req["messages"][0]["content"]
        assert "TEST_RULE" in system
        assert _INLINE_CHART_GUIDANCE not in system
        context = e.context_provider()
        assert len(context) < 1500
        assert skill_catalog_text(SkillLoader([bundled])) not in context
        # Conservative local estimate, not claimed to equal the provider's tokenizer.
        assert estimate(req["messages"]) + estimate(req["tools"]) < 6500
        result = e.registry.execute("search_skills", {"query": "chem-spot-workflow"})
        assert any(s["name"] == "chem-spot-workflow" for s in result["skills"])
        assert "instructions" in e.registry.execute("load_skill", {"name": "chem-spot-workflow"})
        assert "from_tool" in e.registry.execute("get_chart_guidance", {})["instructions"]
    finally:
        e.executor.close()


def test_skill_discovery_paginates_and_load_refreshes_without_new_turn(tmp_path):
    for i in range(45):
        folder = tmp_path / f"skill-{i:02}"
        folder.mkdir()
        (folder / "SKILL.md").write_text(f"---\nname: skill-{i:02}\ndescription: 资料研究\n---\n旧版", encoding="utf-8")
    allowed = {f"skill-{i:02}" for i in range(45)}
    registry = ToolRegistry()
    registry.register_all(skill_tools(SkillLoader([tmp_path]), allowed=lambda: allowed))
    seen, offset = [], 0
    while offset is not None:
        page = registry.execute("search_skills", {"query": "资料研究", "offset": offset})
        assert len(page["skills"]) <= 8
        seen += [s["name"] for s in page["skills"]]
        offset = page["next_offset"]
    assert len(seen) == len(set(seen)) == 45
    md = tmp_path / "skill-44/SKILL.md"
    md.write_text(md.read_text(encoding="utf-8").replace("旧版", "新版"), encoding="utf-8")
    assert registry.execute("load_skill", {"name": "skill-44"})["instructions"] == "新版"
    md.unlink()
    assert "error" in registry.execute("load_skill", {"name": "skill-44"})
    allowed.remove("skill-43")
    assert "error" in registry.execute("load_skill", {"name": "skill-43"})
