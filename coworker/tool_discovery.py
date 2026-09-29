"""Bounded tool schemas over the live, permission-scoped registry.

Discovery changes context, never authorization. Tools added by MCP after engine
construction are immediately searchable; removed tools cannot survive in the cache.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock
import math
import re

from .context_budget import estimate
from .tool_policy import TurnToolPolicy, tool_allowed_under_policy


class ToolDiscovery:
    # Basic web access must not depend on discovering a tool or loading a skill.
    # _allowed still applies explicit user network/search restrictions.
    CORE = ("search_tools", "load_tools", "web_search", "web_fetch",
            "search_skills", "load_skill", "ask_user", "read_file", "get_chart_guidance")

    def __init__(self, registry, policy, budget):
        self.registry, self.policy, self.budget = registry, policy, budget
        self.loaded = OrderedDict()
        self.lock = RLock()
        self.installed = False

    def _allowed(self, name):
        return self.registry.get(name) is not None and tool_allowed_under_policy(
            name, self.policy() or TurnToolPolicy())

    def _install(self):
        if self.installed:
            return

        def search_tools(query: str = "", offset: int = 0, limit: int = 20) -> dict:
            """按名称或描述检索当前可用工具；空查询分页浏览。调用 load_tools 加载所需完整参数定义。"""
            return self.search(query, offset, limit)

        def load_tools(names: list[str]) -> dict:
            """按精确名称加载工具参数定义，供下一次模型调用使用。不会执行工具或授予权限。"""
            return self.load(names)

        self.registry.register(search_tools)
        self.registry.register(load_tools)
        self.installed = True

    def search(self, query="", offset=0, limit=20):
        query = query.casefold().strip()
        rows = []
        for name in sorted(self.registry.names()):
            if not self._allowed(name):
                continue
            desc = str(self.registry.get(name).schema["function"].get("description", ""))
            rows.append({"name": name, "description": desc[:320]})
        if query:
            rows = self._rank(query, rows)
        offset, limit = max(0, offset), max(1, min(50, limit))
        end = offset + limit
        return {"tools": rows[offset:end], "total": len(rows),
                "next_offset": end if end < len(rows) else None}

    @staticmethod
    def _rank(query, rows):
        """Lexical relevance, not a business router or permission filter.

        Split multiword names and Chinese fragments instead of requiring the
        entire user's sentence to appear verbatim in one description.
        """
        def terms(text):
            words = set(re.findall(r"[a-z0-9]+", text.casefold()))
            for run in re.findall(r"[\u4e00-\u9fff]+", text):
                words.update(run[i:i+2] for i in range(len(run)-1))
                words.update(run)
            return words
        wanted = terms(query)
        docs = [terms(row["name"] + " " + row["description"]) for row in rows]
        frequency = {word: sum(word in doc for doc in docs) for word in wanted}
        ranked = []
        for row, doc in zip(rows, docs):
            score = sum((.15 if len(word) == 1 else 1) * math.log(1 + len(rows)/(1+frequency[word]))
                        for word in wanted & doc)
            if query in (row["name"] + " " + row["description"]).casefold():
                score += 10
            if row["name"].casefold() == query:
                score += 100
            if score > 0:
                ranked.append((score, row))
        return [row for _, row in sorted(ranked, key=lambda x: (-x[0], x[1]["name"]))]

    def prime_mcp(self, query, limit=3):
        """Expose a few relevant live MCP definitions without a model discovery round."""
        candidates = [{"name": name, "description": str(self.registry.get(name).schema["function"].get("description", ""))[:320]}
                      for name in self.registry.names() if name.startswith("mcp__") and self._allowed(name)]
        ranked = self._rank(str(query)[:2000].casefold(), candidates)
        names = [row["name"] for row in ranked[:limit]]
        if names:
            self.load(names)
        return names

    def load(self, names):
        with self.lock:
            rejected = {}
            requested = list(dict.fromkeys(names))
            for name in requested:
                if not self._allowed(name):
                    rejected[name] = "工具未注册或受用户明确策略限制"
                    continue
                core_cost = sum(estimate(self.registry.get(n).schema) for n in self.CORE if self._allowed(n))
                if estimate(self.registry.get(name).schema) + core_cost > self.budget():
                    rejected[name] = "单个工具参数定义超过上下文预算，请提高模型窗口或缩小工具定义"
                    continue
                self.loaded.pop(name, None)
                self.loaded[name] = None
            visible = {s["function"]["name"] for s in self.schemas()}
            for name in requested:
                if name not in visible and name not in rejected:
                    rejected[name] = "本批工具超过预算，请拆分加载"
            return {"loaded": [n for n in requested if n in visible], "rejected": rejected}

    def schemas(self):
        with self.lock:
            available = [s for s in self.registry.schemas() if self._allowed(s["function"]["name"])]
            if not self.installed and len(available) <= 24 and estimate(available) <= self.budget():
                return available
            self._install()
            names = [n for n in self.CORE if self._allowed(n)]
            used = sum(estimate(self.registry.get(n).schema) for n in names)
            for name in reversed(self.loaded):
                if name in names or not self._allowed(name):
                    continue
                size = estimate(self.registry.get(name).schema)
                if used + size <= self.budget():
                    names.append(name)
                    used += size
            return [self.registry.get(name).schema for name in names]
