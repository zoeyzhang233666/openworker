# Mermaid Hover Chrome Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inline Mermaid blends with answer text until hover/focus-within; errors always show chrome.

**Architecture:** Pure CSS chrome toggle via transparent border + `visibility: hidden` toolbar placeholder; `is-error` class from MermaidBlock for persistent error chrome.

**Tech Stack:** React, CSS, Vitest / Testing Library.

**Plan status:** 已于 2026-08-03 获用户批准；按 Task 执行。

---

### Task 1: Spec / README

- [x] Write `docs/superpowers/specs/2026-08-03-chemclaw-mermaid-hover-chrome-design.md`
- [x] Update `docs/chemclaw/README.md` status line

### Task 2: CSS + TSX + tests

- [x] Update `.mermaid-block` / `.mermaid-block-toolbar` hover/focus-within/is-error rules in `surfaces/gui/src/styles.css`
- [x] Add `is-error` class on MermaidBlock root when `error || exportError`
- [x] Extend `MermaidBlock.test.tsx`; run `npm test -- --run src/components/MermaidBlock.test.tsx`（13 passed）
