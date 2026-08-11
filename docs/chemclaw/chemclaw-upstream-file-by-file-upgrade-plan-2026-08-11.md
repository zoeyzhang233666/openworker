# ChemClaw 上游逐文件升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 `zoeyzhang233666/openworker:chemclaw-clean` 为唯一目标基线，选择性吸收 `andrewyng/openworker` 自共同基线 `01b6f83` 之后最有价值的更新，在不覆盖 ChemClaw 化工业务能力、i18n、长任务交付、Mermaid、compaction、persona/skills 等定制的前提下，完成安全、交互、Memory 和工程质量升级。

**Architecture:** 不整体 merge upstream，不 cherry-pick 上游 merge commit。低冲突更新采用叶子 commit 或文件级 backport；高冲突更新按函数/数据契约手工移植。`ask_user` 按“schema → Inbox 持久化 → engine/server → GUI”链路升级；Memory 按“store/index → settings/runtime → REST → GUI/Undo → CLI/TUI”分阶段升级，每阶段独立可测、独立提交。

**Tech Stack:** Python 3.10+、FastAPI、SQLite、aisuite tools、React + TypeScript、Tauri、Vitest、Playwright、pytest。

## Global Constraints

- 目标分支始终是 `chemclaw-clean`；不要以 fork 的 `main` 作为实现基线。
- 上游共同基线：`01b6f83b3927e02912dda84bb392942c13ca70d1`（OpenAI Responses API 合并点）。
- 本计划参考的上游最新 `main`：`9702c86c7f90425d93fb2de877833ead2f446686`（2026-08-08）。
- 不整体 merge `andrewyng/openworker:main`。
- 不 cherry-pick PR #471、#472 的 merge commit；它们会覆盖 ChemClaw 高冲突文件。
- `coworker/agent.py`、`coworker/server/manager.py`、`coworker/server/app.py`、`surfaces/gui/src/App.tsx`、`SettingsView.tsx`、`Transcript.tsx`、`InboxItemCard.tsx` 一律局部移植，禁止整文件替换。
- 保留 ChemClaw 默认模型和 provider 定制，包括 `apihub-cn:deepseek-v4-flash`。
- 保留 ChemClaw 化工领域工具、Persona、Skills、Leads、Huagongshe、Customs、Quote、Tender、Trade、VAT、FX、Wiki 等注册与行为。
- 保留 ChemClaw `_LONG_TASK_GUIDANCE`、`_DIAGRAM_GUIDANCE`、`_CLARIFY_POINTER`、artifact 链接交付规范。
- 保留 ChemClaw compaction 持久化与 `engine.compaction_settings` live wiring。
- GUI 新文案必须接入 ChemClaw `useI18n()`；不要把 upstream 英文硬编码原样搬进产品 UI。
- 旧 `ask_user` 单问题、字符串 options、历史 Inbox JSON 必须继续可用。
- Memory “关闭”语义：停止新增/修改/删除长期记忆；已存在的记忆仍可读取、仍注入当前新会话。运行中的会话写开关即时生效。
- Memory 的“已知事实”和 User Rules 在会话创建时固定；修改/删除对新会话生效，不应让运行中的会话知识静默漂移。
- 所有数据库升级必须原位兼容已有 `coworker.db`；禁止要求用户删库重建。
- Python 版本声明继续保持 `>=3.10`，通过 `tomli` fallback 修复 3.10，而不是抬高版本下限。

---

## 0. 上游来源与优先级

| 优先级 | 上游来源 | 叶子 commit / 合并 | 内容 | ChemClaw 策略 |
|---|---|---|---|---|
| P0 | PR #415 | `18ac388162080c5144ce4fda19e1381c76a5691c` | DNS rebinding / SSRF pinning | 优先 backport；基本可直接移植 |
| P0 | PR #416 | `abb7eef86351ce37fc4e496f6fce6d5fe53d05eb` | Python 3.10 `tomllib` fallback | 手工两处小改 |
| P1 | PR #419 | `17e27ce98afc9409676a77bb31212ac9a3a9e437` | GUI CI TypeScript typecheck | 直接移植 |
| P1 | PR #471 | merge `be7c250...` / feature `70cd1fa...` | rich/grouped `ask_user` | 按数据链手工移植 |
| P1/P2 | PR #472 | merge `41d4c54...` / core `ef59b0f...` | Memory V1/2 增强 | 分 4 阶段移植 |
| P3 | PR #417 | `6356aa6cd0108e2d417afd0c35a19bd34456d2dc` | GUI README stale paths | 直接移植 |

上游参考：

- PR #415: https://github.com/andrewyng/openworker/pull/415
- PR #416: https://github.com/andrewyng/openworker/pull/416
- PR #417: https://github.com/andrewyng/openworker/pull/417
- PR #419: https://github.com/andrewyng/openworker/pull/419
- PR #471: https://github.com/andrewyng/openworker/pull/471
- PR #472: https://github.com/andrewyng/openworker/pull/472
- ChemClaw 目标分支: https://github.com/zoeyzhang233666/openworker/tree/chemclaw-clean

---

## 1. 操作方式图例

- **Direct**：ChemClaw 该文件基本没有领域定制，可以按 upstream patch 直接移植；仍需跑测试。
- **Manual-Low**：只改少量行，手工插入，避免覆盖 ChemClaw 默认值/依赖。
- **Manual-High**：ChemClaw 已深度定制；只搬函数/字段/事件，不替换文件。
- **Create-Adapt**：upstream 新文件可作为结构参考，但必须适配 ChemClaw i18n/产品语义。
- **Optional**：不影响核心能力，可在主升级完成后补齐。

---

## 2. 逐文件总览 / 冲突矩阵

### 2.1 P0 / 工程基础

| 文件 | 来源 | 模式 | 冲突 | 应合入内容 | ChemClaw 必须保留 |
|---|---|---:|---:|---|---|
| `coworker/web/guard.py` | #415 | Direct | 低 | `_vet()`、`_pinned()`、每跳 IP pin、Host/SNI、logical URL | 已有 CGNAT/private/metadata 防护 |
| `coworker/web/fetch.py` | #415 | Direct | 低 | `resp.extensions["logical_url"]` | 现有 web fetch 截断/解析行为 |
| `tests/test_url_address_guard.py` | #415 | Direct | 低 | pin/rebinding/IPv6/Host/SNI/logical URL tests | 现有 SSRF tests |
| `coworker/config.py` | #416 | Manual-Low | 中 | `tomllib` → `tomli` fallback | ChemClaw 默认模型、config 字段 |
| `pyproject.toml` | #416 | Manual-Low | 中 | 条件依赖 `tomli>=2` | ChemClaw `openpyxl`、uncertainty 等依赖 |
| `.github/workflows/ci.yml` | #419 | Direct | 低 | `npx tsc --noEmit` | 现有 pytest/Vitest/Playwright jobs |
| `surfaces/gui/README.md` | #417 | Direct | 低 | 去掉旧 `platform/` 路径 | ChemClaw 若有品牌文案则保留 |
| `surfaces/gui/src-tauri/src/lib.rs` | #417 | Direct | 极低 | 仅 dev fallback 注释 | 运行逻辑不改 |

### 2.2 `ask_user` 升级

| 文件 | 来源 | 模式 | 冲突 | 应合入内容 | ChemClaw 必须保留 |
|---|---|---:|---:|---|---|
| `coworker/tools/ask.py` | #471 | Direct | 低 | rich options、grouped questions、helpers、显式 schema | tool metadata 风格 |
| `coworker/inbox.py` | #471 | Direct | 低 | `header`、`questions`、rich option persistence | 旧 JSON 兼容 |
| `coworker/interactions.py` | #471 | Direct | 低 | rich option label；grouped 不生成 channel buttons | 现有 channel 编码协议 |
| `coworker/engine.py` | #471 | Manual-Low | 中 | grouped-only 问题合法；`answer`/`answers` 状态 | ChemClaw compaction/outbound/interrupt 行为 |
| `coworker/server/manager.py` | #471 | Manual-High | 高 | `question_item_fields()` / `answer_result()` | persona/skills/connectors/compaction/chem runtime |
| `coworker/server/app.py` | #471 | Manual-High | 高 | live `question_asker` 的 header/questions + result shape | ChemClaw Mermaid/API/WS 扩展 |
| `surfaces/gui/src/types.ts` | #471 | Manual-Low | 中 | `QuestionOption`、`GroupedQuestion` | 现有 Item/Event 类型 |
| `surfaces/gui/src/api.ts` | #471 | Manual-Low | 中 | InboxItem rich/grouped 类型 | ChemClaw 既有 API clients |
| `surfaces/gui/src/components/InboxItemCard.tsx` | #471 | Manual-High | 高 | QuestionCard/stepper/preview | `useI18n`、approval UI、SaveSkillPreview、task grant |
| `surfaces/gui/src/App.tsx` | #471 | Manual-High | 高 | live question event 传 header/questions | compaction、message_updated、ChemClaw switch cases |
| `surfaces/gui/src/i18n.tsx` | Chem adaptation | Manual-High | 中 | rich/grouped ask 文案 keys | 现有 zh-CN/en-US 体系 |
| `tests/test_ask_user_upgrades.py` | #471 | Direct-Adapt | 低 | backend contract tests | 使用 ChemClaw agent fixture 时适配 |
| `surfaces/gui/e2e/ask-upgrades.spec.ts` | #471 | Adapt | 中 | rich + stepper E2E | localized 文案，用 testid 降低脆弱性 |

### 2.3 Memory 升级

| 文件 | 来源 | 模式 | 冲突 | 应合入内容 | ChemClaw 必须保留 |
|---|---|---:|---:|---|---|
| `coworker/memory/base.py` | #472 | Direct | 低 | summary、index mode、delete_all interface | 现有 Scope 值 |
| `coworker/memory/sqlite_store.py` | #472 | Direct | 低 | summary column 原位 migration、delete_all | 现有 DB path/table |
| `coworker/memory/tools.py` | #472 | Direct | 低 | `memory_read`、summary、live saving gate、notifier | aisuite metadata |
| `coworker/memory/settings.py` | #472 | Create-Adapt | 低 | enabled + user_rules store | 修正注释为最终真实语义 |
| `coworker/memory/__init__.py` | #472 | Direct | 低 | export 新 API | 现有 exports |
| `coworker/agent.py` | #472 | Manual-High | 极高 | Memory guidance、rules、render index、live write switch | 所有 ChemClaw 工具与 guidance |
| `coworker/server/manager.py` | #472 | Manual-High | 极高 | settings store、engine wiring、notifier、CRUD/settings methods | 所有 ChemClaw manager 子系统 |
| `coworker/server/app.py` | #472 | Manual-High | 高 | Memory REST CRUD/settings | ChemClaw 自定义路由 |
| `coworker/cli.py` | #472 | Manual-Low | 低 | MemorySettingsStore wiring | ChemClaw CLI 参数 |
| `coworker/tui/app.py` | #472 | Manual-Low | 低 | memory_off/user_rules pass-through | TUI 现有行为 |
| `surfaces/gui/src/api.ts` | #472 | Manual-Low | 中 | memory client + MEMORY_CHANGED | 现有 API helper |
| `surfaces/gui/src/components/MemorySection.tsx` | #472 | Create-Adapt | 中 | toggle/list/edit/delete/rules UI | 全部接 i18n；ChemClaw 产品语言 |
| `surfaces/gui/src/components/SettingsView.tsx` | #472 | Manual-High | 高 | Memory tab | Compaction、Voice、Profile、Skills、flags、i18n |
| `surfaces/gui/src/types.ts` | #472 | Manual-Low | 中 | `memory_saved` event + memory Item | ask_user 新类型、现有事件 |
| `surfaces/gui/src/App.tsx` | #472 | Manual-High | 极高 | memory_saved → transcript；Undo | ChemClaw 自定义事件 switch |
| `surfaces/gui/src/components/Transcript.tsx` | #472 | Manual-High | 高 | inline memory notice + Undo | Mermaid repair、turn grouping、i18n |
| `surfaces/gui/src/components/Transcript.test.tsx` | #472 | Adapt | 低 | save/update/undo rendering tests | 现有 tests |
| `tests/test_memory.py` | #472 | Direct-Adapt | 中 | migration/index/tools/runtime tests | ChemClaw fixtures |
| `tests/test_memory_api.py` | #472 | Create-Adapt | 中 | REST/settings/live-switch tests | ChemClaw manager fixture |

---

# Implementation Tasks

## Task 0: 建立隔离升级分支与基线测试

**Files:** 无代码修改。

**Interfaces:**
- Consumes: `chemclaw-clean` 当前 HEAD。
- Produces: 一个干净、可回滚的升级分支和基线测试结果。

- [ ] **Step 1: 从 `chemclaw-clean` 建升级分支**

```bash
git checkout chemclaw-clean
git status --short
git checkout -b chore/upstream-backport-2026-08-11
```

要求 `git status --short` 在切分支前为空；若不为空，先自行提交或 stash 当前工作，不要把无关改动混入升级。

- [ ] **Step 2: 配置 upstream remote**

```bash
git remote get-url upstream || git remote add upstream https://github.com/andrewyng/openworker.git
git fetch upstream main
```

验证共同基线：

```bash
git merge-base HEAD upstream/main
git show -s --oneline 01b6f83b3927e02912dda84bb392942c13ca70d1
```

预期：merge-base 应对应 `01b6f83...` 或能解释为 ChemClaw 已提前吸收的等价提交；若不同，后续仍按文件契约移植，不改为整体 merge。

- [ ] **Step 3: 跑 Python 基线**

```bash
pytest tests -q
```

记录失败项；只有“升级前已经失败”的项可以作为后续已知基线，不得用它掩盖新增回归。

- [ ] **Step 4: 跑 GUI 基线**

```bash
cd surfaces/gui
npm ci
npx tsc --noEmit
npm test
cd ../..
```

如果当前 `npx tsc --noEmit` 已失败，先记录现有错误；Task 3 加 CI 前必须清零。

---

## Task 1: P0 — 关闭 `web_fetch` DNS rebinding 窗口

**Upstream:** PR #415 / commit `18ac388162080c5144ce4fda19e1381c76a5691c`

**Files:**
- Modify: `coworker/web/guard.py`
- Modify: `coworker/web/fetch.py`
- Modify: `tests/test_url_address_guard.py`

**Interfaces:**
- Produces: `get_checked(client, logical_url)` 每一跳连接到已审查 IP，而不是让 client 二次 DNS resolve。
- Produces: 最终响应 `resp.extensions["logical_url"]`，供 `web_fetch` 展示域名 URL。

### `coworker/web/guard.py`

**合入范围：整套搬，不可只搬一半。**

- [ ] **Step 1: 把原 URL 校验拆成 `_vet()`**

保留 ChemClaw 现有 `_blocked_reason()`，包括 loopback、private、link-local、CGNAT、multicast、reserved 等规则。把 DNS 解析后的允许地址返回为 pin：

```python
def _vet(url: str) -> tuple[Optional[str], Optional[str]]:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return "url must start with http:// or https://", None
    host = parts.hostname
    if not host:
        return "url has no host", None

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        reason = _blocked_reason(literal)
        return (f"refusing to fetch {host}: {reason}" if reason else None), None

    try:
        infos = socket.getaddrinfo(
            host,
            parts.port or (443 if parts.scheme == "https" else 80),
            proto=socket.IPPROTO_TCP,
        )
    except OSError as exc:
        return f"could not resolve {host}: {exc}", None

    pin: Optional[str] = None
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None:
            ip = mapped
        reason = _blocked_reason(ip)
        if reason:
            return f"refusing to fetch {host} ({ip}): {reason}", None
        if pin is None:
            pin = raw
    return None, pin


def check_url(url: str) -> Optional[str]:
    return _vet(url)[0]
```

**冲突处理：** ChemClaw 当前已有 CGNAT/Tailscale 范围防护，必须保留；不要退回 upstream 更早版本的地址规则。

- [ ] **Step 2: 新增 `_pinned()`**

imports 改为：

```python
from urllib.parse import urljoin, urlsplit, urlunsplit
```

新增：

```python
def _pinned(url: str, ip: str) -> tuple[str, dict, dict]:
    parts = urlsplit(url)
    host = parts.hostname
    addr = f"[{ip}]" if ":" in ip else ip
    userinfo, _, _ = parts.netloc.rpartition("@")
    netloc = (f"{userinfo}@" if userinfo else "") + addr
    host_header = host
    if parts.port is not None:
        netloc += f":{parts.port}"
        host_header += f":{parts.port}"
    request_url = urlunsplit(
        (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
    )
    extensions = {"sni_hostname": host} if parts.scheme == "https" else {}
    return request_url, {"Host": host_header}, extensions
```

**不能省略：** HTTPS `sni_hostname`。只改 URL 到 IP 而不保留 SNI 会导致证书校验对 IP 进行，正常站点 TLS 失败。

- [ ] **Step 3: 改 `get_checked()` 为每跳 pin**

核心逻辑必须是：

```python
reason, pin = _vet(seen)
if reason:
    raise PermissionError(reason)

if pin is None:
    resp = client.get(seen)
else:
    request_url, headers, extensions = _pinned(seen, pin)
    resp = client.get(request_url, headers=headers, extensions=extensions)

if resp.status_code not in (301, 302, 303, 307, 308):
    ext = getattr(resp, "extensions", None)
    if isinstance(ext, dict):
        ext["logical_url"] = seen
    return resp

location = resp.headers.get("location")
if not location:
    return resp
seen = urljoin(seen, location)
```

**冲突处理：** redirect 必须相对“逻辑 URL”解析，禁止改成 `resp.url.join(location)`；此时 `resp.url` 已是 pin 后的 IP URL，会让相对 redirect 丢掉原 hostname。

- [ ] **Step 4: `coworker/web/fetch.py` 使用 logical URL**

将最终 URL 获取改为：

```python
final_url = resp.extensions.get("logical_url", url)
```

不要返回 `str(resp.url)`，否则模型/用户会看到内部 pin 的 IP。

- [ ] **Step 5: 加完整回归测试**

`tests/test_url_address_guard.py` 至少覆盖：

1. hostname 连接目标是第一次 vetted IP；
2. Host header 保持原 hostname；
3. HTTPS SNI 保持原 hostname；
4. DNS 第二次答案翻到 `127.0.0.1` 也不会被请求；
5. 显式 port 在 URL 和 Host 中保留；
6. IPv6 pin 使用 `[...]`；
7. literal-IP URL 不重写；
8. redirect 后 `logical_url` 仍是域名 URL；
9. 既有 loopback/private/CGNAT tests 继续通过。

Run:

```bash
pytest tests/test_url_address_guard.py -q
```

- [ ] **Step 6: 提交**

```bash
git add coworker/web/guard.py coworker/web/fetch.py tests/test_url_address_guard.py
git commit -m "security: pin web fetch connections against DNS rebinding"
```

---

## Task 2: P0 — 修复 Python 3.10 `tomllib` 导入

**Upstream:** PR #416 / commit `abb7eef86351ce37fc4e496f6fce6d5fe53d05eb`

**Files:**
- Modify: `coworker/config.py`
- Modify: `pyproject.toml`

**Conflict:** 两个文件均有 ChemClaw 定制，因此手工改，不整文件 cherry-pick。

- [ ] **Step 1: `coworker/config.py` 只替换 import**

把：

```python
import tomllib
```

替换为：

```python
try:
    import tomllib  # stdlib since 3.11
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]
```

**保留：** `Config.model = "apihub-cn:deepseek-v4-flash"` 以及 ChemClaw 所有 config 字段。

- [ ] **Step 2: `pyproject.toml` 只追加条件依赖**

在 `[project].dependencies` 中加入：

```toml
"tomli>=2; python_version < '3.11'",
```

**保留：** `openpyxl>=3.1`、Windows `tzdata`、`uncertainty` optional dependencies 以及所有 ChemClaw additions。

- [ ] **Step 3: Python 3.12/当前环境回归**

```bash
pytest tests/test_config.py -q
python -c "from coworker.config import load_config; print('config import ok')"
```

- [ ] **Step 4: Python 3.10 smoke（CI 或本机有 3.10 时）**

```bash
python3.10 -c "from coworker.config import load_config; print('py310 config import ok')"
```

如果项目 CI 只有 3.12，建议后续单独加一个最小 3.10 import job；本任务不要求扩大 CI matrix。

- [ ] **Step 5: 提交**

```bash
git add coworker/config.py pyproject.toml
git commit -m "fix: support Python 3.10 tomllib fallback"
```

---

## Task 3: P1/P3 — GUI Typecheck CI + stale docs

**Upstream:** PR #419、#417。

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `surfaces/gui/README.md`
- Modify: `surfaces/gui/src-tauri/src/lib.rs`（注释）

- [ ] **Step 1: CI 增加 Typecheck**

在 `gui-unit` 的 `npm ci` 后、Unit tests 前插入：

```yaml
- name: Typecheck
  working-directory: surfaces/gui
  run: npx tsc --noEmit
```

Run locally:

```bash
cd surfaces/gui
npx tsc --noEmit
npm test
cd ../..
```

- [ ] **Step 2: 修 README 旧 `platform/` 路径**

明确改成 repo root：

```bash
bash packaging/setup_dev_env.sh
./.venv/bin/openworker-server --cwd /path/to/your/project --port 8765
cd surfaces/gui
npm install
npm run dev
npm run tauri dev
```

删除以下旧路径：

- `platform/packaging/setup_dev_env.sh`
- `cd platform`
- `platform/.venv`
- `platform/surfaces/gui`

- [ ] **Step 3: Rust 注释同步**

只把 `server_bin()` 的 dev fallback 注释从 `platform/.venv` 改为 repo-root `.venv`；不要改函数逻辑。

- [ ] **Step 4: 提交（可拆两次）**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: typecheck ChemClaw GUI"

git add surfaces/gui/README.md surfaces/gui/src-tauri/src/lib.rs
git commit -m "docs: fix GUI development paths"
```

---

## Task 4: P1 — `ask_user` 2.0 后端数据契约

**Upstream:** PR #471。

**Files:**
- Modify: `coworker/tools/ask.py`
- Modify: `coworker/inbox.py`
- Modify: `coworker/interactions.py`
- Modify: `coworker/engine.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`
- Create/Adapt: `tests/test_ask_user_upgrades.py`

### 4.1 `coworker/tools/ask.py` — 可以以 upstream 文件为主

- [ ] **Step 1: 支持 rich option**

Option schema 必须兼容两种格式：

```python
"staging"
```

或：

```python
{
    "label": "staging",
    "description": "Use the staging environment",
    "recommended": True,
    "preview": "ENV=staging",
}
```

对象仅强制 `label`；其余字段 optional。

- [ ] **Step 2: 支持最多 4 个 grouped questions**

定义：

```python
MAX_GROUPED_QUESTIONS = 4
```

`ask_user` 签名变为：

```python
def ask_user(
    question: str = "",
    options: list | None = None,
    allow_text: bool = True,
    multi: bool = False,
    header: str = "",
    questions: list | None = None,
) -> dict:
    ...
```

显式 schema 通过：

```python
wrapped = tool(...)
wrapped.__coworker_schema__ = _ASK_SCHEMA
return wrapped
```

- [ ] **Step 3: 移植四个 helper**

必须有：

```python
normalize_option(opt) -> dict
option_label(opt) -> str
normalize_questions(raw) -> list[dict]
question_item_fields(args: dict) -> dict | None
answer_result(item_questions: list, resolution: str | None) -> dict
```

行为契约：

- 单问题：`{"answer": "..."}`
- grouped：`{"answers": {"Header": "..."}}`
- grouped resolution 在 Inbox 内以 JSON string 持久化。
- grouped 若从纯文本 channel 得到一个 bare string，归到第一题的 `header`，没有 header 时用 question text。
- plain string options 保持原样，保证旧 UI/旧 session 兼容。

### 4.2 `coworker/inbox.py` — 扩展字段，不做破坏性迁移

- [ ] **Step 4: 扩展 `InboxItem`**

把：

```python
options: list[str] = field(default_factory=list)
```

改为：

```python
options: list = field(default_factory=list)
header: str = ""
questions: list[dict] = field(default_factory=list)
```

`add()` 与 `add_question()` 增加 `header` / `questions` 参数并持久化。

**兼容要求：** 旧 JSON 没有 `header/questions` 时 dataclass defaults 必须自然加载；禁止强制迁移旧 Inbox 文件。

### 4.3 `coworker/interactions.py` — channel 降级策略

- [ ] **Step 5: rich options button 使用 label**

```python
from .tools.ask import option_label
```

单问题 rich options：按钮 label 和 resolution 都使用 `option_label(opt)`。

Grouped question：

```python
if item.kind == KIND_QUESTION and getattr(item, "questions", None):
    return []
```

原因：一个 Slack/Telegram button row 无法回答多步问题，应该降级为文本 + “到 app 中完成”的现有 mirror 逻辑。

### 4.4 `coworker/engine.py` — 只改 `_handle_ask_user`

**禁止整文件替换。** ChemClaw 的 engine 已含 compaction、interrupt、outbound 逻辑。

- [ ] **Step 6: grouped-only call 也视为有效问题**

在：

```python
question = str(args.get("question", "")).strip()
```

之后加入：

```python
if not question:
    for entry in args.get("questions") or []:
        if isinstance(entry, dict) and str(entry.get("question", "")).strip():
            question = str(entry["question"]).strip()
            break
```

- [ ] **Step 7: success status 同时认 `answers`**

把：

```python
status = "ok" if result.get("answer") else "denied"
```

改成：

```python
status = "ok" if (result.get("answer") or result.get("answers")) else "denied"
```

其它 `_interruptible()`、audit、message append、TOOL_FINISHED 一律保持 ChemClaw 当前实现。

### 4.5 `coworker/server/manager.py` — 只改 `inbox_question_asker`

- [ ] **Step 8: 用 canonical helper 生成 Inbox fields**

在 `inbox_question_asker(...).ask(...)` 内：

```python
from ..tools.ask import answer_result, question_item_fields

fields = question_item_fields(args)
if fields is None:
    return {"answer": "", "error": "no question"}
```

创建 item：

```python
item = self.inbox.add_question(
    session_id,
    inbox=inbox_name,
    tool_call_id=tool_call_id,
    **fields,
)
```

Durable resume：

```python
if item.state != "pending":
    return answer_result(item.questions, item.resolution)
```

等待回答后：

```python
answer = await self.inbox.wait(item.id)
return answer_result(item.questions, answer)
```

**冲突处理：** 不动 manager 其它 routing、persona、skill、connector、compaction 代码。

### 4.6 `coworker/server/app.py` — live attended question

- [ ] **Step 9: WebSocket live `question_asker` 使用同一 canonical helper**

```python
from ..tools.ask import answer_result, question_item_fields

fields = question_item_fields(args)
if fields is None:
    return {"answer": "", "error": "no question"}
```

`add_question()` 使用 `**fields`；发给 GUI 的 `question_requested` data 加：

```python
"header": item.header,
"questions": item.questions,
```

返回：

```python
return answer_result(item.questions, await manager.inbox.wait(item.id))
```

### 4.7 后端测试

- [ ] **Step 10: 移植/适配 `tests/test_ask_user_upgrades.py`**

必须覆盖：

- schema string-or-object union；
- max grouped = 4；
- blank grouped entries 丢弃；
- rich option canonicalization；
- old string option pass-through；
- first grouped question 同步到 legacy title/options；
- `answer_result` 单/多 shape；
- old persisted InboxItem 默认 `header=""`, `questions=[]`；
- rich channel button 用 label；
- grouped channel 无 buttons；
- manager full round trip 最终 tool message 是 `{"answers": ...}`。

Run:

```bash
pytest tests/test_ask_user_upgrades.py -q
pytest tests/test_durable_resume.py -q
```

- [ ] **Step 11: 提交**

```bash
git add coworker/tools/ask.py coworker/inbox.py coworker/interactions.py \
  coworker/engine.py coworker/server/manager.py coworker/server/app.py \
  tests/test_ask_user_upgrades.py
git commit -m "feat: add rich grouped ask_user backend"
```

---

## Task 5: P1 — `ask_user` 2.0 GUI + ChemClaw i18n

**Files:**
- Modify: `surfaces/gui/src/types.ts`
- Modify: `surfaces/gui/src/api.ts`
- Modify: `surfaces/gui/src/components/InboxItemCard.tsx`
- Modify: `surfaces/gui/src/App.tsx`
- Modify: `surfaces/gui/src/i18n.tsx`
- Create/Adapt: `surfaces/gui/e2e/ask-upgrades.spec.ts`

### 5.1 `types.ts`

- [ ] **Step 1: 新增 rich/grouped 类型**

```ts
export type QuestionOption =
  | string
  | {
      label: string;
      description?: string;
      recommended?: boolean;
      preview?: string;
    };

export interface GroupedQuestion {
  question: string;
  header?: string;
  options?: QuestionOption[];
  allow_text?: boolean;
  multi?: boolean;
}
```

Question Item 改为：

```ts
{
  kind: "question";
  question: string;
  options?: QuestionOption[];
  allow_text?: boolean;
  multi?: boolean;
  header?: string;
  questions?: GroupedQuestion[];
  resolved?: string;
}
```

### 5.2 `api.ts`

- [ ] **Step 2: InboxItem 同步字段**

Import `QuestionOption`, `GroupedQuestion`，把 `options?: string[]` 改为 `QuestionOption[]`，增加：

```ts
header?: string;
questions?: GroupedQuestion[];
```

### 5.3 `InboxItemCard.tsx` — 高冲突，只抽取 question renderer

**当前 ChemClaw 文件已有：** `useI18n`、humanized approvals、`SaveSkillPreview`、standing task grants、directory/plan actions。全部保留。

- [ ] **Step 3: 新增 option normalization，不替换 approval 部分**

从 upstream 移植：

- `NormOption`
- `normOption()`
- `QSpec`
- `specsFor()`
- `QuestionBlock`
- `QuestionCard`

保留原 `InboxItemCard` 容器、approval/directory/plan 分支。

- [ ] **Step 4: rich option UI 行为**

实现契约：

- 纯 string options 仍渲染现有 pills；
- 有 description/preview 时升级为 full-width row；
- 任一 option 有 preview 时右侧显示 monospace preview pane；
- hover/focus 切换 preview；
- single-select 点击立刻 resolve；
- multi-select 选择后点击 Send；
- `recommended` 显示 tag；
- grouped questions 以 stepper 展示；
- 最后一步 resolve 为 `JSON.stringify(answerMap)`；
- back button 允许回上一步重新选择。

- [ ] **Step 5: 不把 upstream 英文硬编码带进来**

`QuestionBlock` / `QuestionCard` 内调用 `useI18n()` 或由父组件传 `t`。建议新增这些 key：

```text
ask.recommended
ask.previous
ask.question
ask.progress
ask.typeOwn
ask.yourAnswer
```

建议 zh-CN：

```text
ask.recommended = 推荐
ask.previous = 上一个问题
ask.question = 问题
ask.progress = 第 {current}/{total} 个
ask.typeOwn = 或输入自己的答案…
ask.yourAnswer = 请输入答案…
```

建议 en-US：

```text
ask.recommended = Recommended
ask.previous = Previous question
ask.question = Question
ask.progress = {current} of {total}
ask.typeOwn = Or type your own answer…
ask.yourAnswer = Your answer…
```

复用已有 `Send` 翻译，不重复建 key。

### 5.4 `App.tsx`

- [ ] **Step 6: live event 透传 grouped metadata**

现有：

```ts
case "question_requested":
```

仅增加：

```ts
header: d.header || "",
questions: d.questions || [],
```

同样，在把 pending Inbox question 转成 `InboxItemCard` props 的位置加 `header/questions`。

**冲突处理：** 不重排 ChemClaw event switch；`compacting`、`compacted`、`message_updated`、artifact/browser refresh 等现有 case 保持原位。

### 5.5 E2E

- [ ] **Step 7: 适配 upstream Playwright tests**

测试两个场景：

1. rich options：description + Recommended + preview hover + label resolution；
2. grouped：2-step stepper + back + 最终 JSON answer map。

ChemClaw 已 i18n，断言优先使用：

```ts
page.getByTestId("question-preview")
page.getByTestId("question-stepper")
```

不要只依赖英文 `Recommended` / `Previous question`。

Run:

```bash
cd surfaces/gui
npx tsc --noEmit
npm test
npx playwright test e2e/ask-upgrades.spec.ts
cd ../..
```

- [ ] **Step 8: 提交**

```bash
git add surfaces/gui/src/types.ts surfaces/gui/src/api.ts \
  surfaces/gui/src/components/InboxItemCard.tsx surfaces/gui/src/App.tsx \
  surfaces/gui/src/i18n.tsx surfaces/gui/e2e/ask-upgrades.spec.ts
git commit -m "feat: add rich grouped ask_user UI"
```

---

## Task 6: P1 — Memory Core：summary、index mode、`memory_read`

**Upstream:** PR #472。

**Files:**
- Modify: `coworker/memory/base.py`
- Modify: `coworker/memory/sqlite_store.py`
- Modify: `coworker/memory/tools.py`
- Modify: `coworker/memory/__init__.py`
- Modify/Adapt: `tests/test_memory.py`

此阶段**不动 GUI，不动 agent.py 高冲突部分**；先让存储和工具层稳定。

### 6.1 `memory/base.py`

- [ ] **Step 1: `MemoryItem` 增加 summary**

```python
summary: Optional[str] = None
```

`MemoryStore.add()` 增加 `summary`；`update()` 改成：

```python
def update(
    self,
    item_id: int,
    content: str,
    *,
    summary: Optional[str] = None,
) -> Optional[MemoryItem]: ...
```

增加：

```python
def delete_all(self, *, scope: Optional[Scope] = None) -> int: ...
```

- [ ] **Step 2: 加 index rendering**

常量：

```python
INDEX_THRESHOLD_CHARS = 8_000
INDEX_FULL_NEWEST = 10
```

行为：

- Full rendering `<= 8000 chars`：和现在一致；
- 超过阈值：最新 10 条保留全文，旧条目只显示 summary；
- 没 summary 的旧 row 用 content 第一行截到约 80 chars；
- index block 末尾明确提示 agent 先 `memory_read([#id])` 再依据摘要行动。

函数：

```python
format_memory_index(...)
render_memory_block(...)
```

### 6.2 `memory/sqlite_store.py`

- [ ] **Step 3: 原位 schema migration**

`CREATE TABLE memories` 加：

```sql
summary TEXT
```

初始化时检查：

```python
cols = {
    row["name"]
    for row in self._conn.execute("PRAGMA table_info(memories)").fetchall()
}
if "summary" not in cols:
    self._conn.execute("ALTER TABLE memories ADD COLUMN summary TEXT")
```

**关键约束：** 不 migrate 老 content，不重建表，不丢数据。

- [ ] **Step 4: add/update/read 支持 summary**

`add()` INSERT summary；`_row_to_item()` 读 summary。

`update()` 语义：

- `summary is None`：只更新 content，保留旧 summary；
- `summary is not None`：同时更新 content + summary。

增加 `delete_all(scope=None)`，返回删除行数。

### 6.3 `memory/tools.py`

- [ ] **Step 5: 扩展 factory 接口**

```python
def memory_tools(
    store: MemoryStore,
    *,
    workspace: Optional[str],
    on_saved: Optional[Callable[[MemoryItem, Optional[str]], None]] = None,
    saving_enabled: Optional[Callable[[], bool]] = None,
) -> list:
```

- [ ] **Step 6: `remember` 支持 summary**

```python
def remember(content: str, summary: str = "", scope: str = "workspace") -> dict:
```

- `summary.strip() or None`
- `global` 不带 workspace
- `session` scope 强制退回 `workspace`
- unknown scope 也退回 workspace。

- [ ] **Step 7: 增加 `memory_read`**

```python
def memory_read(memory_ids: list[int]) -> dict:
```

结果：

```json
{
  "memories": [
    {"id": 1, "scope": "global", "content": "full body"}
  ],
  "missing": [999]
}
```

`missing` 只有非空时才需要出现。

- [ ] **Step 8: live saving gate**

`remember`、`memory_update`、`memory_forget` 每次执行都检查：

```python
saving_enabled is not None and not saving_enabled()
```

关闭时返回明确 error，不做 DB mutation。`memory_read` 永远可读。

- [ ] **Step 9: notifier**

新增/更新成功后 best-effort 调 `on_saved(item, previous)`；callback 异常必须吞掉，不能回滚已成功的 memory write。

`memory_update` 在写前读取 existing content，把 previous 传给 notifier，为 GUI Undo 提供恢复文本。

### 6.4 `memory/__init__.py`

- [ ] **Step 10: export 新 API**

至少 export：

```text
INDEX_THRESHOLD_CHARS
MemoryItem
MemoryStore
Scope
format_memories
format_memory_index
render_memory_block
SQLiteMemoryStore
memory_tools
```

MemorySettingsStore 在 Task 7 再加入。

### 6.5 Unit tests

- [ ] **Step 11: 加核心测试**

`tests/test_memory.py` 至少包括：

- legacy DB 自动获得 summary column；
- old row summary=None；
- new summary round-trip；
- update summary 与 content-only update 语义；
- delete_all(scope)；
- 8000 threshold 前 full、后 index；
- newest 10 full；
- legacy row index fallback；
- `memory_read` + missing ids；
- saving gate 运行时开/关双向切换；
- update notifier 带 previous；
- callback failure 不影响 save。

Run:

```bash
pytest tests/test_memory.py -q
```

- [ ] **Step 12: 提交**

```bash
git add coworker/memory/base.py coworker/memory/sqlite_store.py \
  coworker/memory/tools.py coworker/memory/__init__.py tests/test_memory.py
git commit -m "feat: add indexed persistent memory core"
```

---

## Task 7: P1/P2 — Memory Settings、Agent Runtime 与 REST API

**Files:**
- Create: `coworker/memory/settings.py`
- Modify: `coworker/memory/__init__.py`
- Modify: `coworker/agent.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`
- Create/Adapt: `tests/test_memory_api.py`
- Modify/Adapt: `tests/test_memory.py`

### 7.1 `memory/settings.py`

- [ ] **Step 1: 新建 settings store**

实现：

```python
MAX_USER_RULES_CHARS = 20_000
```

`MemorySettingsStore(path)`：

- JSON file；
- thread lock；
- corrupt/missing file → defaults；
- `enabled` default True；
- `user_rules` default empty；
- `set(enabled=None, user_rules=None)` partial update；
- rules 截断到 20,000 chars；
- `snapshot()`。

`format_user_rules()` 必须说明用户规则优先于 learned memories。

**修正 upstream 注释歧义：** 文件 docstring 不要写“off means no memory tools / no memories block”。ChemClaw 采用 upstream 最终运行时行为：off = stop learning/writes，已有记忆仍可用，工具保留但写操作拒绝，以支持 mid-session switch。

### 7.2 `memory/__init__.py`

- [ ] **Step 2: export settings**

```python
from .settings import MemorySettingsStore, format_user_rules
```

加入 `__all__`。

### 7.3 `coworker/agent.py` — 极高冲突，按锚点插入

**禁止用 upstream `agent.py` 覆盖当前文件。** 当前 ChemClaw 已有大量化工工具 imports + `_LONG_TASK_GUIDANCE` + `_DIAGRAM_GUIDANCE` + `_CLARIFY_POINTER`。

- [ ] **Step 3: 仅扩展 memory imports**

从：

```python
from .memory import MemoryStore, Scope, format_memories, memory_tools
```

改成包含：

```python
from .memory import (
    MemoryStore,
    Scope,
    format_user_rules,
    memory_tools,
    render_memory_block,
)
```

不要删除任何 ChemClaw imports。

- [ ] **Step 4: 更新 `_MEMORY_GUIDANCE`，但不碰其他 guidance**

指导原则应包含：

1. global = 用户跨项目事实；workspace = 当前项目；
2. save conservatively；
3. 明确“记住”请求必须保存；
4. health/finance/relationships/beliefs 等敏感信息 silent save 前先问；
5. 每个 memory 带 <=15 words summary；
6. save 后用户可见地简短说明；
7. 已有 memory 优先 update，不 duplicate；
8. 不保存 repo 自己能重推导的内容；
9. 日期用绝对日期；
10. 使用 memory 前检查容易过时的 file/URL 是否仍存在。

- [ ] **Step 5: 新增 `_MEMORY_OFF_NOTICE`**

语义必须明确：

- 已保存事实仍可用；
- 当前会话新信息可临时记住，但不会跨会话保存；
- 不得假装 “saved/remembered” 成功；
- 用户可在 Settings ▸ Memory 重新开启。

- [ ] **Step 6: 扩展 `build_engine` 参数，不删除 ChemClaw 参数**

在 `memory_store` 附近新增：

```python
on_memory_saved: Optional[Any] = None,
user_rules: Optional[Any] = None,
memory_off: bool = False,
memory_saving_enabled: Optional[Any] = None,
```

保留现有 `subscription_store`、`channel_buffer`、`skill_filter`、`default_skill_ids` 等参数。

- [ ] **Step 7: User Rules 在 memory block 之前注入**

```python
rules_block = format_user_rules(
    (user_rules() if callable(user_rules) else user_rules) or ""
)
if rules_block:
    instructions = f"{instructions}\n\n{rules_block}"
```

这段发生在 engine build 时，因此 user rules 对当前 session stable。

- [ ] **Step 8: 写开关是 live callable**

```python
def _saving_enabled() -> bool:
    if memory_saving_enabled is not None:
        return bool(memory_saving_enabled())
    return not memory_off
```

Memory tools 始终注册：

```python
registry.register_all(
    memory_tools(
        memory_store,
        workspace=str(ws) if ws else None,
        on_saved=on_memory_saved,
        saving_enabled=_saving_enabled,
    )
)
```

- [ ] **Step 9: memory prompt 用 `render_memory_block`**

替换：

```python
block = format_memories(remembered)
```

为：

```python
block = render_memory_block(remembered)
```

- [ ] **Step 10: context provider 动态注入 off notice**

在 ChemClaw 当前 `context_provider()` 中，保留 plan/discuss/roots 等逻辑，仅增加：

```python
if memory_store is not None and not _saving_enabled():
    parts.append(_MEMORY_OFF_NOTICE)
```

### 7.4 `coworker/server/manager.py` — 极高冲突，局部插入

- [ ] **Step 11: constructor 初始化 settings store**

Import：

```python
from ..memory import MemorySettingsStore, MemoryStore, Scope, SQLiteMemoryStore
```

在：

```python
self.memory_store = SQLiteMemoryStore(base / "coworker.db")
```

后加入：

```python
self.memory_settings = MemorySettingsStore(base / "memory-settings.json")
```

- [ ] **Step 12: `get_engine()` build call 增加 Memory wiring**

当前 ChemClaw `build_engine(...)` call 中，保留所有现有参数，只在 `memory_store` 附近插入：

```python
memory_store=self.memory_store,
memory_off=not self.memory_settings.enabled,
memory_saving_enabled=lambda: self.memory_settings.enabled,
user_rules=lambda: self.memory_settings.user_rules,
on_memory_saved=self._memory_saved_notifier(session_id),
```

**特别保留：** build 后的：

```python
if record is not None and record.compaction:
    ...
engine.compaction_settings = self.compaction_settings
```

不要让 Memory patch 覆盖 ChemClaw compaction wiring。

- [ ] **Step 13: `_build_task_engine()` 同样接 Memory**

Scheduled/automation engine 也传同样四项，避免后台任务和前台会话行为不一致。

- [ ] **Step 14: 增加 `_memory_saved_notifier(session_id)`**

广播：

```python
{
    "type": "memory_saved",
    "data": {
        "id": item.id,
        "scope": item.scope.value,
        "summary": item.summary or "",
        "content": item.content,
        "previous": previous or "",
    },
}
```

要求 best-effort；无 event loop、socket 已断时不影响保存。

- [ ] **Step 15: 扩展现有 memory methods，不另建第二套 store**

`list_memory()` 每行返回：

```python
{
    "id": m.id,
    "scope": m.scope.value,
    "content": m.content,
    "summary": m.summary or "",
    "created_at": m.created_at or "",
}
```

`add_memory()`：trim content，空内容返回 `{ok: False, error: "content required"}`。

新增：

```python
update_memory(item_id, content)
delete_memory(item_id)
delete_all_memory()
get_memory_settings()
set_memory_settings(enabled=None, user_rules=None)
```

用户从 Memory screen 手工编辑 content 时，建议：

```python
self.memory_store.update(item_id, content, summary="")
```

避免旧 summary 与新正文冲突。

### 7.5 `coworker/server/app.py` — Memory routes

- [ ] **Step 16: 扩展 `/v1/memory`**

保留当前 GET；POST body 先规范：

```python
body = body or {}
return manager.add_memory(
    str(body.get("content", "")),
    str(body.get("scope", "workspace")),
)
```

- [ ] **Step 17: settings route 必须写在 `/{item_id}` 前**

```python
@app.get("/v1/memory/settings")
def memory_settings() -> dict[str, Any]:
    return manager.get_memory_settings()

@app.put("/v1/memory/settings")
def memory_settings_put(body: dict) -> dict[str, Any]:
    body = body or {}
    return manager.set_memory_settings(
        enabled=bool(body["enabled"]) if "enabled" in body else None,
        user_rules=str(body["user_rules"]) if "user_rules" in body else None,
    )
```

然后：

```python
@app.patch("/v1/memory/{item_id}")
...
@app.delete("/v1/memory/{item_id}")
...
@app.delete("/v1/memory")
...
```

### 7.6 Backend acceptance tests

- [ ] **Step 18: 创建/适配 `tests/test_memory_api.py`**

至少覆盖：

1. add/list/patch/delete；
2. empty add/edit 拒绝；
3. unknown id 拒绝；
4. delete-all；
5. GET/PUT settings partial update；
6. `/settings` 不被 `{item_id}` route 吃掉；
7. user_rules clamp 20k；
8. saving off：运行中的 engine 写立即拒绝；
9. saving off：已有 memory 仍注入；
10. saving on again：同一个 running engine 可恢复写；
11. user rules 出现在 memory 之前；
12. agent `remember(summary=...)` 后 REST list 能看到同一条。

Run:

```bash
pytest tests/test_memory.py tests/test_memory_api.py -q
pytest tests/test_server.py -q
```

- [ ] **Step 19: 提交**

```bash
git add coworker/memory/settings.py coworker/memory/__init__.py coworker/agent.py \
  coworker/server/manager.py coworker/server/app.py \
  tests/test_memory.py tests/test_memory_api.py
git commit -m "feat: add memory settings and server runtime"
```

---

## Task 8: P2 — Memory GUI、Settings 页面、可撤销保存提示

**Files:**
- Modify: `surfaces/gui/src/api.ts`
- Create-Adapt: `surfaces/gui/src/components/MemorySection.tsx`
- Modify: `surfaces/gui/src/components/SettingsView.tsx`
- Modify: `surfaces/gui/src/types.ts`
- Modify: `surfaces/gui/src/App.tsx`
- Modify: `surfaces/gui/src/components/Transcript.tsx`
- Modify: `surfaces/gui/src/components/Transcript.test.tsx`
- Modify: `surfaces/gui/src/i18n.tsx`

### 8.1 `api.ts`

- [ ] **Step 1: 新增 Memory DTO/client**

```ts
export interface MemoryEntry {
  id: number;
  scope: string;
  content: string;
  summary: string;
  created_at: string;
}

export interface MemorySettings {
  enabled: boolean;
  user_rules: string;
}
```

Functions：

```ts
getMemory()
updateMemory(id, content)
deleteMemory(id)
deleteAllMemory()
getMemorySettings()
setMemorySettings(patch)
```

事件：

```ts
export const MEMORY_CHANGED = "coworker:memory-changed";
export function announceMemoryChanged() {
  window.dispatchEvent(new CustomEvent(MEMORY_CHANGED));
}
```

### 8.2 `MemorySection.tsx` — 新建但必须 ChemClaw 化

- [ ] **Step 2: 从 upstream 结构创建页面，不复制英文文案**

页面包含三个 card：

1. “记住新的长期偏好”开关；
2. “已记住的内容”列表：edit/delete/forget all；
3. “你的长期指令” textarea。

数据更新后监听：

```ts
window.addEventListener(MEMORY_CHANGED, refresh)
window.addEventListener("focus", refresh)
```

卸载时移除 listeners。

- [ ] **Step 3: 全部使用 `useI18n()`**

建议新增 keys：

```text
memory.title
memory.subtitle
memory.rememberNew
memory.rememberHelp
memory.enabledMessage
memory.disabledMessage
memory.learnedTitle
memory.learnedHelp
memory.forgetAll
memory.empty
memory.userRulesTitle
memory.userRulesHelp
memory.userRulesPlaceholder
memory.save
memory.savedForNewChats
memory.loading
memory.fix
memory.delete
memory.cancel
memory.confirmDeleteAll
memory.deleteAllDone
memory.toastSaved
memory.toastUpdated
memory.toastUndo
memory.toastForgotten
memory.toastRestored
```

中文产品语义建议强调：

- 关闭后“不再保存新的长期记忆”，已有内容仍会用于新对话，直到用户删除；
- 编辑/删除影响新对话；已经打开的对话保留启动时知识；
- User Rules 是用户主动设置，优先于 agent 自动学到的 memory。

### 8.3 `SettingsView.tsx` — 只加一个 tab

当前文件已经包含 Compaction、Voice、Profile、Skills、产品 flags 和 i18n。

- [ ] **Step 4: SetTab 加 `memory`**

```ts
type SetTab =
  | "appearance"
  | "models"
  | "skills"
  | "voice"
  | "memory"
  | "personas";
```

Import `MemorySection`，SET_TABS 增 Memory 行；icon 可用现有 `archive`（确认 Icon 类型支持后再使用）。渲染分支：

```tsx
) : tab === "memory" ? (
  <MemorySection />
```

不要改 persona flag/filter、CompactionCard 或 Voice 页面逻辑。

### 8.4 `types.ts`

- [ ] **Step 5: 增加 event/item**

EventType 加：

```ts
| "memory_saved"
```

Item union 加：

```ts
| {
    kind: "memory";
    id: number;
    text: string;
    previous?: string;
    undone?: boolean;
  }
```

### 8.5 `App.tsx` — event + Undo

- [ ] **Step 6: import memory API helpers**

加入：

```ts
announceMemoryChanged,
deleteMemory,
updateMemory,
```

Settings tab union 同步增加 `memory`。

- [ ] **Step 7: 只在 event switch 增 `memory_saved` case**

```ts
case "memory_saved":
  setItems((p) => [
    ...p,
    {
      kind: "memory",
      id: Number(d.id),
      text: String(d.summary || d.content || ""),
      ...(d.previous ? { previous: String(d.previous) } : {}),
    },
  ]);
  announceMemoryChanged();
  break;
```

保留所有 ChemClaw 其它 cases。

- [ ] **Step 8: 新增 Undo handler**

```ts
const undoMemorySave = async (id: number, previous?: string) => {
  if (previous) await updateMemory(id, previous).catch(() => {});
  else await deleteMemory(id).catch(() => {});
  announceMemoryChanged();
  setItems((p) =>
    p.map((it) =>
      it.kind === "memory" && it.id === id ? { ...it, undone: true } : it,
    ),
  );
};
```

传给 Transcript：

```tsx
onUndoMemory={(id, previous) => void undoMemorySave(id, previous)}
```

### 8.6 `Transcript.tsx` — 高冲突，增一个 case

当前 ChemClaw Transcript 有 Mermaid repair、turn grouping、ClampedUserText、i18n。全部保留。

- [ ] **Step 9: Props 增 `onUndoMemory`**

```ts
onUndoMemory?: (id: number, previous?: string) => void;
```

- [ ] **Step 10: switch 增 `case "memory"`**

渲染 persistent inline notice；行为：

- new save：显示“我会记住 …” + Undo；
- update：显示“我更新了记忆 …” + Undo；
- undone new：显示“已忘记”；
- undone update：显示“已恢复之前内容”；
- Undo 后不再展示 Undo button。

文案全部使用 `t(...)`，不要 upstream 英文硬编码。

### 8.7 GUI unit tests

- [ ] **Step 11: Transcript tests**

测试：

1. new save → `onUndoMemory(id, undefined)`；
2. update → `onUndoMemory(id, previous)`；
3. `undone=true` → 不再有 Undo；
4. localized UI 可以用 testid + callback 断言，不依赖英文句子。

Run:

```bash
cd surfaces/gui
npx tsc --noEmit
npm test
cd ../..
```

- [ ] **Step 12: 提交**

```bash
git add surfaces/gui/src/api.ts surfaces/gui/src/components/MemorySection.tsx \
  surfaces/gui/src/components/SettingsView.tsx surfaces/gui/src/types.ts \
  surfaces/gui/src/App.tsx surfaces/gui/src/components/Transcript.tsx \
  surfaces/gui/src/components/Transcript.test.tsx surfaces/gui/src/i18n.tsx
git commit -m "feat: add memory screen and undo notices"
```

---

## Task 9: P2 — CLI / TUI Memory parity

**Files:**
- Modify: `coworker/cli.py`
- Modify: `coworker/tui/app.py`

Desktop GUI 是 ChemClaw 主面，本任务可在 Memory GUI 后做，但建议补齐，避免 CLI/TUI 与桌面语义分叉。

- [ ] **Step 1: CLI 读同一个 `memory-settings.json`**

```python
from .memory import MemorySettingsStore, SQLiteMemoryStore
```

在 state dir：

```python
memory_settings = MemorySettingsStore(data_dir / "memory-settings.json")
memory_store = SQLiteMemoryStore(data_dir / "coworker.db")
```

创建 TUI/app 时传：

```python
memory_off=not memory_settings.enabled,
user_rules=memory_settings.user_rules,
```

- [ ] **Step 2: TUI pass-through**

`__init__` 加：

```python
memory_off: bool = False,
user_rules: str = "",
```

保存到实例，并在 `build_engine()` 时传入。

TUI 本阶段不用做 live settings toggle；它读取启动时 snapshot 即可。

- [ ] **Step 3: smoke**

```bash
python -m coworker.cli --help
pytest tests/test_memory.py -q
```

- [ ] **Step 4: 提交**

```bash
git add coworker/cli.py coworker/tui/app.py
git commit -m "feat: wire memory settings into CLI and TUI"
```

---

# 10. ChemClaw 高冲突文件逐个合并规则

## `coworker/agent.py`

**风险：极高。**

必须保留：

- `.chem`, `.entity`, `.leads`, `.quote`, `.tender`, `.customs`, `.trade`, `.vat`, `.fx`, `.wiki`, `.huagongshe` imports / tool factories；
- ChemClaw long-task guidance；
- artifact markdown/html delivery 规范；
- Mermaid semantic edge label 规范；
- clarification/process-skill 指针；
- skill live filtering；
- connector/messaging/subscription wiring；
- `apihub-cn:deepseek-v4-flash` 默认 model。

只允许改：Memory imports、`_MEMORY_GUIDANCE`、新增 `_MEMORY_OFF_NOTICE`、`build_engine` memory 参数、rules block、memory tools registration、`render_memory_block`、context provider memory-off branch。

**禁止：** 从 upstream `agent.py` 整段复制 `build_engine()`。

## `coworker/server/manager.py`

**风险：极高。**

必须保留：

- session scratch/multi-root；
- persona install/enable/connection；
- skills install/filter；
- connectors/subscriptions/channel；
- mention sessions；
- audit；
- automation/self-wake；
- Mermaid repair；
- compaction state + live settings；
- ChemClaw read models/API backing methods。

只允许局部改：constructor memory settings、两个 engine build call 的 memory args、`inbox_question_asker`、memory notifier、memory CRUD/settings methods。

## `coworker/server/app.py`

**风险：高。**

保留：ChemClaw `/mermaid-repair`、connectors、MCP、sessions/artifacts、WS 自定义逻辑。

只改：Memory routes、attended `question_asker` data/result。

## `surfaces/gui/src/App.tsx`

**风险：极高。**

保留：

- background-delivered turn/source logic；
- streaming/reasoning；
- `message_updated`；
- `compacting`/`compacted`；
- artifact/browser refresh；
- ChemClaw settings surface；
- i18n。

只加：question `header/questions`、memory_saved case、Undo handler、Memory settings tab union。

## `InboxItemCard.tsx`

**风险：高。**

保留：

- `useI18n()`；
- `humanizeApprovalTitle()`；
- `ApprovalCard` helpers；
- `SaveSkillPreview`；
- `Allow every time` task rule；
- directory/plan branches。

只重构 `item.kind === "question"` 分支为 `QuestionCard`。

## `SettingsView.tsx`

**风险：高。**

保留：CompactionCard、Voice、Profile、updates、product flags、Skills/Personas、i18n。只加 Memory tab + MemorySection。

## `Transcript.tsx`

**风险：高。**

保留：TurnGroup、Mermaid repair、Markdown、thinking、ClampedUserText、tool humanization。只增 memory item 分支与 callback prop。

---

# 11. 推荐提交顺序

严格建议以下独立 commits，方便 bisect / revert：

1. `security: pin web fetch connections against DNS rebinding`
2. `fix: support Python 3.10 tomllib fallback`
3. `ci: typecheck ChemClaw GUI`
4. `docs: fix GUI development paths`
5. `feat: add rich grouped ask_user backend`
6. `feat: add rich grouped ask_user UI`
7. `feat: add indexed persistent memory core`
8. `feat: add memory settings and server runtime`
9. `feat: add memory screen and undo notices`
10. `feat: wire memory settings into CLI and TUI`

不要把 10 组压成一个大 commit。

---

# 12. 全量 Verification Matrix

## Python

```bash
pytest tests/test_url_address_guard.py -q
pytest tests/test_config.py -q
pytest tests/test_ask_user_upgrades.py -q
pytest tests/test_memory.py tests/test_memory_api.py -q
pytest tests/test_durable_resume.py -q
pytest tests -q
```

验收：

- DNS rebinding test 明确验证第二次 DNS answer 不影响 connect target；
- Python 3.10 import 可运行；
- old ask_user tests 不退化；
- old Inbox persisted data 能加载；
- legacy memory DB 不丢数据；
- memory index threshold 生效；
- live memory toggle 双向切换；
- manager durable resume + grouped questions 正常；
- ChemClaw compaction tests 全绿。

## GUI

```bash
cd surfaces/gui
npx tsc --noEmit
npm test
npx playwright test e2e/ask-upgrades.spec.ts
npx playwright test
npm run build
cd ../..
```

验收：

- TypeScript 0 errors；
- Rich Ask 纯 string 仍是旧 pills；
- description/recommended/preview 正常；
- grouped stepper 正常；
- zh-CN/en-US 不出现未翻译 key；
- Memory Settings 能 list/edit/delete/delete-all；
- Memory save notice 可 Undo；
- ChemClaw Skills、Personas、Voice、Models/Compaction settings 未丢；
- Mermaid repair UI 未回归。

## Manual Smoke

1. 新建 ChemClaw 对话，执行一个需要 2-3 个澄清字段的任务，确认 agent 可一次调用 grouped `ask_user`。
2. 用 rich options 返回推荐方案 + preview，确认 GUI hover/focus preview。
3. `remember` 一条偏好，确认 transcript 出现可撤销提示。
4. Settings ▸ Memory 能看到同一条。
5. 点 Undo，确认 DB/列表同步消失；如果是 update，确认恢复 previous，而不是删除整个 row。
6. 关闭“记住新内容”，同一运行中 session 再调用 `remember` 应明确失败；已有记忆仍在 context 中。
7. 再开启开关，不新建 session，再调用 `remember` 应恢复成功。
8. 写入 >8k chars 等价量的 memories，开新 session，确认 system prompt 使用 index + `memory_read`，而不是全量全文。
9. `web_fetch` 普通 HTTPS 域名仍成功，返回的 final_url 是域名，不是 pinned IP。
10. 旧 ChemClaw 化工工具（chemical identity、entity、quote、customs、huagongshe 等）至少各做一个 registry/smoke，确认没有因 `agent.py` merge 丢注册。

---

# 13. 不要做的事情

- 不要 `git merge upstream/main`。
- 不要 cherry-pick `be7c250...`（#471 merge）或 `41d4c54...`（#472 merge）到 ChemClaw。
- 不要用 upstream `agent.py`、`manager.py`、`App.tsx` 整文件覆盖 ChemClaw。
- 不要为了 Memory Settings 新建第二个 memory SQLite 数据库。
- 不要把 memory off 解释成“清空/忽略已有记忆”。
- 不要在关闭 memory 时把 tools 从 registry 移除；否则运行中的 session 重新打开开关仍无法恢复保存。
- 不要让 User Rules 每 turn 动态变化；它们是 session-start knowledge。
- 不要让 memory index 中的 summary 直接作为事实执行；必须引导 agent `memory_read` full body。
- 不要只做 DNS `check_url` 而不做 connection pin；那无法关闭 rebinding 窗口。
- 不要 pin HTTPS IP 后省略 SNI；会破坏证书校验。
- 不要用 pinned `resp.url` 解析相对 redirect；必须基于 logical URL。
- 不要把 upstream Memory/Ask 的英文 UI 字符串原样写入 ChemClaw；统一接 i18n。
- 不要删除 ChemClaw `openpyxl`、uncertainty、provider、自定义 model 依赖/默认值。
- 不要把新增 tests 改成只断言“HTTP 200”；必须断言核心数据/状态契约。

---

# 14. 完成定义（Definition of Done）

全部满足才算升级完成：

- [ ] P0 DNS rebinding pinning 已上线并有回归测试。
- [ ] Python 3.10 声明与实际 import 行为一致。
- [ ] GUI CI 强制 `tsc --noEmit`。
- [ ] GUI README 不再引用不存在的 `platform/`。
- [ ] `ask_user` 支持 rich options、preview、recommended、最多 4 个 grouped questions。
- [ ] 旧单问题 `ask_user` / string options / persisted Inbox 完全兼容。
- [ ] Memory 有 summary、index mode、`memory_read`、legacy DB migration。
- [ ] Memory 开关对运行中 session 的写入即时生效，并可双向切换。
- [ ] 已有 memory 在关闭保存时仍可被新 session 使用。
- [ ] User Rules 有 20k server-side clamp，且优先于 learned memory。
- [ ] Memory REST CRUD/settings 完整。
- [ ] Memory Settings GUI 可看、改、删、全删、开关、编辑 rules。
- [ ] Agent save/update 在 transcript 有可撤销提示；update Undo 恢复 previous。
- [ ] GUI 新文案全部进入 ChemClaw i18n。
- [ ] `agent.py` 所有 ChemClaw 化工工具和 guidance 保留。
- [ ] `manager.py` 的 compaction/persona/skills/connectors/automation 定制保留。
- [ ] `App.tsx` / `Transcript.tsx` 的 ChemClaw Mermaid/compaction/streaming 行为无回归。
- [ ] `pytest tests -q` 通过（排除有明确升级前证据的既有失败）。
- [ ] `npx tsc --noEmit`、`npm test`、`npx playwright test`、`npm run build` 通过。

---

# 15. 推荐给 Codex / Claude Code 的执行入口

把本文件交给实现 agent 后，第一条执行指令建议写成：

> 从 `chemclaw-clean` 新建隔离分支，严格按本计划 Task 0 → Task 9 顺序执行。高冲突文件只做局部移植，不用 upstream 整文件覆盖；每个 Task 先补/移植对应测试，再实现，再跑该 Task 的验证命令，再单独提交。任何冲突优先保留 ChemClaw 现有化工工具、i18n、compaction、Mermaid、persona/skills/connector 定制，并只移植本计划列出的 upstream 数据契约和函数行为。

