# ChemClaw Mermaid 失败补救 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mermaid 语法渲染失败时自动就地修一次（可见进度），失败保留「修复图表」；成功图不重绘。

**Architecture:** 纯函数替换 fence + `manager.repair_mermaid` 无工具 `provider.complete` + REST `POST .../mermaid-repair` + WS `message_updated`；`MermaidBlock` 分类失败并触发自动/手动修图。

**Tech Stack:** FastAPI、pytest、React/Vitest、现有 provider.complete、i18n。

**Spec:** `docs/superpowers/specs/2026-08-06-chemclaw-mermaid-repair-design.md`（D-074）

## Global Constraints

- 只在 `chemclaw-clean` worktree 工作。
- 仅 syntax 失败进修图；成功/超长/库加载失败不调模型。
- 不代发用户气泡；不占 `_running_sessions`。
- 产物 MD 预览无 repairContext 时不修图。
- 默认中文 i18n。

## File Structure

| 文件 | 职责 |
| --- | --- |
| `coworker/mermaid_repair.py` | fence 提取/替换、解析模型输出 |
| `tests/test_mermaid_repair.py` | 纯函数 + manager/API 测 |
| `coworker/server/manager.py` | `repair_mermaid` |
| `coworker/server/app.py` | REST 端点 |
| `coworker/engine.py` | ASSISTANT_MESSAGE 带 `ts` |
| `surfaces/gui/src/api.ts` | `repairMermaid` |
| `surfaces/gui/src/components/MermaidBlock.tsx` | 分类、自动1次、按钮、进度 |
| `surfaces/gui/src/components/Markdown.tsx` | 传 repairContext |
| `surfaces/gui/src/components/Transcript.tsx` | 助手消息传 context |
| `surfaces/gui/src/App.tsx` | message_updated + onRepair 更新 items；assistant ts |
| `surfaces/gui/src/i18n.tsx` | repairing / repair / repairFailed |
| `docs/chemclaw/README.md` | 状态 |

---

### Task 1: 纯函数 + manager + API

- [x] 实现 `mermaid_repair.py` 与单测
- [x] 实现 `manager.repair_mermaid` + `POST /v1/sessions/{id}/mermaid-repair`
- [x] ASSISTANT_MESSAGE payload 含 `ts`
- [x] pytest 通过

### Task 2: 前端补救 UX

- [x] api + MermaidBlock 失败分类与修图
- [x] Markdown/Transcript/App 接线
- [x] i18n
- [x] npm 单测通过

### Task 3: 文档

- [x] 更新 README 状态与回归记录
