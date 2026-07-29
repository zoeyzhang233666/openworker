# ChemClaw 首条真实纵向链路 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不接入 SAG、不构建正式安装包的前提下，完成“默认中文的 ChemClaw 源码界面 → 检查并安装白毛股神 Serenity 样板包中的产业链层级测绘 Skill → 点击 Skill 新建对话并显示挂载 → 后续轮次持续读取最新有效 Skill → Mermaid 真实渲染、源码切换和导出”的第一条可用闭环，同时保护 OpenWorker 原有对话、MCP、权限、审批和定时任务能力。

**Architecture:** 保留现有 FastAPI、TurnEngine、PersonaRegistry、SkillLoader、React/Vite 和 WebSocket 会话协议。在后端增加一个边界清晰的 `capabilities` 模块，负责双语能力元数据、Serenity 包检查和原子安装；通过会话记录保存稳定 Skill ID，并在每轮动态上下文中重新解析当前有效内容。前端只增加轻量国际化上下文、真实 Skill 页面、挂载条和 Mermaid 组件，不重写现有应用壳层。

**Tech Stack:** Python 3.11、FastAPI、SQLite、pytest、React 18、TypeScript、Vite、Vitest、Playwright、Mermaid 11.16.0、现有 Tauri 2 桌面壳层。

**Plan status:** 等待用户批准，尚未授权修改业务代码。

## Global Constraints

- 只在 `D:\OpenWorker\openworker\.worktrees\chemclaw-design` 和分支 `design/chemclaw-foundation` 工作。
- 本计划只覆盖产品设计中的阶段 1。SAG、2D/3D 图谱、探索模式、知识导入、其余六个 Serenity Skills、通用 GitHub 安装、任意依赖脚本执行、Skill 编辑历史、正式 EXE 和发布更新通道均不在本计划内。
- `serenity-full-package` 必须识别出一个 Agent 和七个研究 Skills；本阶段只允许激活 `产业链层级测绘`。另外六个只能出现在检查报告中，不能伪装成已安装或可点击功能。
- 本阶段选择的 `产业链层级测绘` 是纯 Markdown Skill；检查器如果发现它新增了必需脚本、依赖或系统权限，必须拒绝安装并显示中文错误，不能跳过后继续宣称可用。
- 正常产品界面只显示 ChemClaw。`coworker` Python 包名、`COWORKER_STATE_DIR`、`openworker` 命令、WebSocket 子协议、数据库兼容字段和上游许可证署名暂不改名。
- 暂时停用上游自动更新入口，防止 ChemClaw 开发版下载并覆盖为 OpenWorker 发布包；等 ChemClaw 自有签名和发布端点准备好后单独设计恢复。
- 默认简体中文；英文切换只维护界面元数据和第一方文案，不复制 Skill 的可执行正文。
- 安装、挂载和 Mermaid 输入均视为不可信输入。Agent/Skill 只能组合已有工具，不能增加权限、写入秘密或绕过审批。
- 所有测试和开发运行使用 `D:\OpenWorker\.chemclaw-dev\state`，不得读写用户未来的稳定版状态目录。
- 每个任务独立执行、验证、提交。测试失败时停止当前任务，使用 `superpowers:systematic-debugging` 找到原因；不把失败带入下一任务。
- 不合并 `main`，不构建安装程序，不写真实 MCP 或外部服务。完成全部任务后先由用户在源码热更新模式验收。

## Public Contracts Fixed by This Plan

### Stable IDs

```text
Agent: serenity
Skill: serenity.industry-chain-mapping
```

显示名称不是 ID。中文名称可以修改，历史会话和 Agent 引用仍使用稳定 ID。

### Installed Skill metadata

每个由 ChemClaw 管理的 Skill 在 `SKILL.md` 同级保存 `chemclaw.skill.json`：

```json
{
  "schema_version": 1,
  "id": "serenity.industry-chain-mapping",
  "version": "1.0.0+0123456789ab",
  "name": {
    "zh-CN": "产业链层级测绘",
    "en-US": "Industry Chain Layer Mapping"
  },
  "description": {
    "zh-CN": "把一个主题拆成需求、系统、器件、工艺、设备材料和基础设施等层级。",
    "en-US": "Map a theme across demand, systems, components, processes, equipment, materials, and infrastructure."
  },
  "status": "ready",
  "agent_ids": ["serenity"],
  "source": {
    "kind": "local_directory",
    "package_id": "serenity",
    "fingerprint": "sha256:0123456789abcdef"
  }
}
```

`source` 不保存用户秘密。首阶段可以保存来源类型和指纹，但普通技能卡不显示本机绝对路径。

### REST contracts

`GET /v1/skills` 保持原端点并扩展返回值：

```json
{
  "skills": [
    {
      "id": "serenity.industry-chain-mapping",
      "version": "1.0.0+0123456789ab",
      "name": {
        "zh-CN": "产业链层级测绘",
        "en-US": "Industry Chain Layer Mapping"
      },
      "description": {
        "zh-CN": "把一个主题拆成需求、系统、器件、工艺、设备材料和基础设施等层级。",
        "en-US": "Map a theme across demand, systems, components, processes, equipment, materials, and infrastructure."
      },
      "status": "ready",
      "can_use": true,
      "agent_ids": ["serenity"],
      "source_kind": "local_directory"
    }
  ]
}
```

`POST /v1/capability-packages/inspect`：

```json
{
  "local_path": "C:\\Users\\EDY\\Desktop\\serenity-full-package"
}
```

成功响应必须包含 `package_id`、`fingerprint`、Agent、七个研究 Skills、当前可安装项、延后项、跳过项和中文/英文警告。检查过程只读，不执行任何包脚本。

`POST /v1/capability-packages/install`：

```json
{
  "local_path": "C:\\Users\\EDY\\Desktop\\serenity-full-package",
  "fingerprint": "sha256:0123456789abcdef",
  "selected_skill_ids": ["serenity.industry-chain-mapping"],
  "approved": true
}
```

安装前必须重新检查指纹。路径内容变化返回稳定错误码 `SOURCE_CHANGED`；选择阶段 1 之外的 Skill 返回 `PHASE_SCOPE`; 安装失败返回 `INSTALL_FAILED` 并保留上一有效版本。

### WebSocket and session contracts

新会话 URL 使用可重复的 `skill` 查询参数：

```text
/ws/session/session-123?workspace=D%3A%5COpenWorker&agent=serenity&skill=serenity.industry-chain-mapping
```

`ready` 事件增加：

```json
{
  "mounted_skills": [
    {
      "id": "serenity.industry-chain-mapping",
      "version": "1.0.0+0123456789ab",
      "name": {
        "zh-CN": "产业链层级测绘",
        "en-US": "Industry Chain Layer Mapping"
      },
      "status": "ready"
    }
  ]
}
```

SQLite `sessions` 表增加 JSON 文本列 `mounted_skills`；`SessionRecord.mounted_skills` 的内存类型为 `list[str]`。已存在数据库通过幂等 `ALTER TABLE` 迁移，旧记录读取为 `[]`。

---

## Task 1: Establish the reproducible execution and regression baseline

**Files:**

- Create: `docs/chemclaw/TESTING.md`
- Modify: `docs/chemclaw/README.md`

- [ ] **Step 1: Confirm the worktree is clean**

Run:

```powershell
git status --short --branch
git rev-parse --show-toplevel
```

Expected: branch is `design/chemclaw-foundation`, top level is the `chemclaw-design` Worktree, and there are no uncommitted business-code changes.

- [ ] **Step 2: Provision one persistent development toolchain for this active Worktree**

The dependency download requires the normal execution-time network approval. Run:

```powershell
$env:UV_CACHE_DIR='D:\OpenWorker\.chemclaw-dev\uv-cache'
$env:UV_PYTHON_INSTALL_DIR='D:\OpenWorker\.chemclaw-dev\uv-python'
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python '.venv\Scripts\python.exe' -e '.[dev]'
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
  winget install --id Rustlang.Rustup -e --source winget --accept-package-agreements --accept-source-agreements
  $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
  rustup default stable
}
Push-Location 'surfaces\gui'
npm.cmd install
npx.cmd playwright install chromium
Pop-Location
```

Installing Rust is a global, shared toolchain and requires the execution-time system-change approval; it is not repeated per Worktree. Expected: `.venv\Scripts\python.exe --version` reports Python 3.11, `pytest --version` succeeds through that interpreter, `cargo --version` succeeds, and `surfaces/gui/node_modules` exists. Shared uv/npm/Rust/browser caches are reused by later tasks; a new conversation does not reinstall them.

- [ ] **Step 3: Run the backend protection baseline**

Run:

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: exit code 0. Any failure is a baseline defect and blocks feature work until diagnosed.

- [ ] **Step 4: Run the frontend protection baseline**

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd test
npm.cmd run build
npm.cmd run e2e
cargo check --manifest-path 'src-tauri\Cargo.toml'
Pop-Location
```

Expected: all Vitest and Playwright tests pass, the TypeScript/Vite build exits 0, and the existing Tauri Rust shell passes `cargo check`.

- [ ] **Step 5: Record facts, not assumptions**

Create `docs/chemclaw/TESTING.md` with:

- exact Python, Node and npm versions;
- exact commands above;
- commit SHA tested;
- pass/fail counts copied from the command output;
- the persistent dev state and cache locations;
- rule that real MCP credentials are never added to this test state.

Update the environment section in `docs/chemclaw/README.md` to link this file.

- [ ] **Step 6: Commit the baseline**

```powershell
git add docs/chemclaw/TESTING.md docs/chemclaw/README.md
git commit -m "docs: record ChemClaw execution baseline"
```

**Checkpoint:** This is a good stopping point for the first implementation conversation. No product behavior has changed.

---

## Task 2: Add the ChemClaw product shell and lightweight i18n seam

**Files:**

- Create: `surfaces/gui/src/product.ts`
- Create: `surfaces/gui/src/i18n.tsx`
- Create: `surfaces/gui/src/i18n.test.tsx`
- Create: `surfaces/gui/e2e/chemclaw-shell.spec.ts`
- Modify: `surfaces/gui/src/main.tsx`
- Modify: `surfaces/gui/src/App.tsx`
- Modify: `surfaces/gui/src/components/Sidebar.tsx`
- Modify: `surfaces/gui/src/components/Composer.tsx`
- Modify: `surfaces/gui/src/components/SettingsView.tsx`
- Modify: `surfaces/gui/src/components/Onboarding.tsx`
- Modify: `surfaces/gui/src/components/UpdateBanner.tsx`
- Modify: `surfaces/gui/src/components/Sidebar.test.tsx`
- Modify: `surfaces/gui/e2e/fixtures.ts`
- Modify: `surfaces/gui/e2e/boot.spec.ts`
- Modify: `surfaces/gui/index.html`
- Modify: `surfaces/gui/src-tauri/tauri.conf.json`
- Modify: `surfaces/gui/src-tauri/src/lib.rs`
- Modify: `coworker/personas/registry.py`
- Modify: `tests/test_builtin_personas.py`
- Modify: `tests/test_persona_registry.py`

- [ ] **Step 1: Write failing locale and shell tests**

`i18n.test.tsx` must assert:

1. no saved locale gives `zh-CN`;
2. `t("nav.skills")` returns `技能`;
3. switching to `en-US` returns `Skills`;
4. the setting persists under `chemclaw.locale`;
5. `<html lang>` follows the active locale.

`chemclaw-shell.spec.ts` must assert:

1. the default boot/shell says `ChemClaw`, `新建对话`, `最近对话`;
2. the default visible page contains no `OpenWorker`;
3. Settings → General can switch to English without reload;
4. after switching, the shell says `New conversation` and `Recent`;
5. reloading preserves English.

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- src/i18n.test.tsx
npm.cmd run e2e -- chemclaw-shell.spec.ts
Pop-Location
```

Expected: FAIL because the provider, translation keys and ChemClaw shell do not exist.

- [ ] **Step 2: Add one source of product-copy truth**

`product.ts` must export:

```ts
export const PRODUCT_NAME = "ChemClaw";
export const PRODUCT_NAME_ZH = "芯化和云 ChemClaw";
export const CLOUD_CONNECTION_LABEL_ZH = "ChemClaw 云连接服务";
export const CLOUD_CONNECTION_LABEL_EN = "ChemClaw cloud connection service";
export const UPDATES_ENABLED = false;
```

The updater component must return `null` when `UPDATES_ENABLED` is false. Do not point ChemClaw at a made-up update endpoint.

- [ ] **Step 3: Implement the typed i18n context**

Use this public shape:

```ts
export type Locale = "zh-CN" | "en-US";

export interface I18nValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}

export function LocaleProvider({ children }: { children: React.ReactNode }): JSX.Element;
export function useI18n(): I18nValue;
export function localized(
  value: Record<Locale, string>,
  locale: Locale,
): string;
```

The `zh-CN` dictionary defines the key union; the English dictionary must satisfy the same keys at compile time. Wrap `<App />` in `LocaleProvider`.

- [ ] **Step 4: Translate the stage-1 shell, not the entire future product**

Move these first-party strings behind `t(...)`:

- boot and restore status;
- brand bar;
- new conversation, recent, pinned and empty-session labels;
- Skills navigation entry added in Task 6;
- composer placeholder, send, stop, attachment and mode labels;
- Settings heading, General heading and language selector;
- stage-1 install, mount and Mermaid strings.

Replace visible `OpenWorker` branding in onboarding, update notices and default persona display with ChemClaw copy. Preserve internal IDs, protocol headers, CLI names, cloud endpoint configuration and license text.

In `tauri.conf.json`, change visible `productName` and `publisher` to `ChemClaw`. In `src-tauri/src/lib.rs`, change the native window title, tray tooltip, open-menu label and fatal-error product name to ChemClaw. Retain the internal identifier, sidecar executable names and updater plugin configuration until the dedicated release milestone. Since `UPDATES_ENABLED` is false, the GUI must never call those upstream endpoints.

- [ ] **Step 5: Make the built-in default persona display as ChemClaw**

Change only the user-facing built-in name in `PersonaRegistry`; keep persona ID `cowork`. Update tests so the API returns `name: "ChemClaw"` while session routing still uses `agent: "cowork"`.

- [ ] **Step 6: Make the tests pass**

Run:

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
.\.venv\Scripts\python.exe -m pytest tests/test_builtin_personas.py tests/test_persona_registry.py -q
Push-Location 'surfaces\gui'
npm.cmd test -- src/i18n.test.tsx src/components/Sidebar.test.tsx
npm.cmd run e2e -- chemclaw-shell.spec.ts boot.spec.ts chat.spec.ts
npm.cmd run build
cargo check --manifest-path 'src-tauri\Cargo.toml'
Pop-Location
```

Expected: PASS. Existing WebSocket/session behavior remains unchanged and the native shell still compiles.

- [ ] **Step 7: Commit**

```powershell
git add -- coworker/personas/registry.py tests/test_builtin_personas.py tests/test_persona_registry.py surfaces/gui/src/product.ts surfaces/gui/src/i18n.tsx surfaces/gui/src/i18n.test.tsx surfaces/gui/src/main.tsx surfaces/gui/src/App.tsx surfaces/gui/src/components/Sidebar.tsx surfaces/gui/src/components/Composer.tsx surfaces/gui/src/components/SettingsView.tsx surfaces/gui/src/components/Onboarding.tsx surfaces/gui/src/components/UpdateBanner.tsx surfaces/gui/src/components/Sidebar.test.tsx surfaces/gui/e2e/fixtures.ts surfaces/gui/e2e/boot.spec.ts surfaces/gui/e2e/chemclaw-shell.spec.ts surfaces/gui/index.html surfaces/gui/src-tauri/tauri.conf.json surfaces/gui/src-tauri/src/lib.rs
git commit -m "feat: add ChemClaw bilingual product shell"
```

**Checkpoint:** User can run the source UI, see ChemClaw in Chinese by default, and switch the implemented shell to English. No Skill installation exists yet.

---

## Task 3: Introduce stable Skill metadata and the real capability catalog

**Files:**

- Create: `coworker/capabilities/__init__.py`
- Create: `coworker/capabilities/models.py`
- Create: `coworker/capabilities/catalog.py`
- Create: `tests/test_capability_catalog.py`
- Modify: `coworker/skills/base.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`
- Modify: `tests/test_skills.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing catalog tests**

Cover:

- a managed Skill reads stable ID, bilingual names, version, status and Agent references from `chemclaw.skill.json`;
- a legacy directory containing only `SKILL.md` still loads and receives a fallback ID equal to its directory name;
- `SkillLoader.get()` accepts both stable ID and historical display name;
- duplicate stable IDs inside one catalog root fail loudly;
- when multiple roots are intentionally supplied, the later workspace root keeps the existing override precedence over the global root;
- `GET /v1/skills` returns the expanded contract and does not expose absolute local paths.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_capability_catalog.py tests/test_skills.py -q
```

Expected: FAIL because `coworker.capabilities` and stable IDs do not exist.

- [ ] **Step 2: Add immutable capability value objects**

`models.py` must contain these core types:

```python
from dataclasses import dataclass, field
from typing import Literal

Locale = Literal["zh-CN", "en-US"]
CapabilityStatus = Literal["ready", "waiting_config", "disabled", "unavailable"]

@dataclass(frozen=True)
class LocalizedText:
    zh_cn: str
    en_us: str

    def to_dict(self) -> dict[str, str]:
        return {"zh-CN": self.zh_cn, "en-US": self.en_us}

@dataclass(frozen=True)
class SkillCard:
    id: str
    version: str
    name: LocalizedText
    description: LocalizedText
    status: CapabilityStatus
    can_use: bool
    agent_ids: tuple[str, ...] = field(default_factory=tuple)
    source_kind: str = "legacy"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name.to_dict(),
            "description": self.description.to_dict(),
            "status": self.status,
            "can_use": self.can_use,
            "agent_ids": list(self.agent_ids),
            "source_kind": self.source_kind,
        }
```

- [ ] **Step 3: Extend SkillLoader without breaking progressive disclosure**

Append metadata fields to `Skill` with defaults so existing callers remain valid:

```python
id: str = ""
version: str = "unversioned"
display_name_zh: str = ""
display_name_en: str = ""
description_zh: str = ""
description_en: str = ""
status: str = "ready"
agent_ids: list[str] = field(default_factory=list)
source_kind: str = "legacy"
```

Maintain `_skills_by_id` and `_skills_by_name`. Detect duplicate stable IDs while scanning one root, but preserve the existing ordered-root rule in which a later workspace root overrides a global Skill. Catalog injection remains name/description only; the richer UI catalog belongs to `CapabilityCatalog`. `load_skill` must accept either stable ID or display name and return the stable ID in its result.

- [ ] **Step 4: Implement the catalog seam**

`CapabilityCatalog` accepts Skill directories rather than reading global state internally:

```python
class CapabilityCatalog:
    def __init__(self, skill_dirs: list[Path]) -> None:
        self.skill_dirs = skill_dirs

    def list_skills(self) -> list[SkillCard]:
        loader = SkillLoader(self.skill_dirs)
        return [self._to_card(skill) for skill in loader.skills()]

    def get_skill(self, stable_id: str) -> Skill | None:
        return SkillLoader(self.skill_dirs).get(stable_id)
```

This keeps tests isolated and ensures later Worktrees can point at a dedicated state directory.

- [ ] **Step 5: Keep the existing endpoint and expand its result**

`SessionManager.list_skills()` must call `CapabilityCatalog([state_dir() / "skills"])`. Do not add a second competing list endpoint.

- [ ] **Step 6: Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_capability_catalog.py tests/test_skills.py tests/test_server.py -q
```

Expected: PASS, including the old progressive-disclosure tests.

- [ ] **Step 7: Commit**

```powershell
git add -- coworker/capabilities/__init__.py coworker/capabilities/models.py coworker/capabilities/catalog.py coworker/skills/base.py coworker/server/manager.py coworker/server/app.py tests/test_capability_catalog.py tests/test_skills.py tests/test_server.py
git commit -m "feat: add stable Skill capability catalog"
```

**Checkpoint:** The backend exposes a real, backward-compatible Skill catalog. There is no installer or page yet.

---

## Task 4: Inspect the Serenity Agent/Skill bundle without executing it

**Files:**

- Create: `coworker/capabilities/serenity.py`
- Create: `coworker/capabilities/inspection.py`
- Create: `tests/test_serenity_package.py`
- Modify: `coworker/capabilities/models.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write a hermetic Serenity fixture builder**

The test creates a temporary package containing `IDENTITY.md`, `SOUL.md`, `skills/<folder>/SKILL.md` for all seven exact Chinese names, and a `builtin-skills/computer-use-1.2.1/SKILL.md` Linux-only sample. Do not make tests depend on `C:\Users\EDY\Desktop`.

- [ ] **Step 2: Write failing inspection tests**

Assert:

- exact detection of Agent `serenity`, display name `白毛股神 Serenity`;
- exact detection of seven research Skills;
- stable mapping of `产业链层级测绘` to `serenity.industry-chain-mapping`;
- only that Skill is `installable_in_current_phase`;
- the other six are `deferred`, not installed;
- Linux-only `computer-use` is in inspection details but not in the normal catalog;
- the output lists scripts/dependencies/config requirements without executing anything;
- changing a used source file changes the SHA-256 fingerprint;
- a missing research Skill, a symlink escape or invalid UTF-8 returns a stable bilingual error.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_serenity_package.py -q
```

Expected: FAIL because inspection modules do not exist.

- [ ] **Step 3: Encode the seven stable mappings once**

`serenity.py` must define all seven mappings. The representative entry is:

```python
SERENITY_SKILLS = {
    "产业链层级测绘": {
        "id": "serenity.industry-chain-mapping",
        "name_en": "Industry Chain Layer Mapping",
        "description_zh": "把一个主题拆成需求、系统、器件、工艺、设备材料和基础设施等层级。",
        "description_en": (
            "Map a theme across demand, systems, components, processes, "
            "equipment, materials, and infrastructure."
        ),
        "phase": 1,
    },
    "候选优先级排序": {
        "id": "serenity.candidate-prioritization",
        "name_en": "Candidate Prioritization",
        "description_zh": "在同一主题下按产业链位置、稀缺性、证据质量、赔率和风险排序候选标的。",
        "description_en": (
            "Rank candidates by industry-chain position, scarcity, evidence "
            "quality, payoff, and risk."
        ),
        "phase": 2,
    },
    "叙事到系统变化": {
        "id": "serenity.narrative-to-system-change",
        "name_en": "Narrative to System Change",
        "description_zh": "把市场叙事翻译成可验证的技术、供需、成本、效率或约束变化。",
        "description_en": (
            "Translate market narratives into verifiable technical, supply-demand, "
            "cost, efficiency, or constraint changes."
        ),
        "phase": 2,
    },
    "研究对话推进": {
        "id": "serenity.research-dialogue",
        "name_en": "Research Dialogue",
        "description_zh": "把模糊主题逐步推进到系统变化、产业链位置、证据和证伪条件。",
        "description_en": (
            "Advance a vague theme toward system changes, industry-chain position, "
            "evidence, and falsification conditions."
        ),
        "phase": 2,
    },
    "稀缺环节识别": {
        "id": "serenity.scarcity-detection",
        "name_en": "Scarcity Detection",
        "description_zh": "识别供应商少、认证周期长、扩产难和替代难的关键约束环节。",
        "description_en": (
            "Identify constrained links with few suppliers, long qualification "
            "cycles, difficult expansion, and limited substitutes."
        ),
        "phase": 2,
    },
    "证伪条件压力测试": {
        "id": "serenity.falsification-stress-test",
        "name_en": "Falsification Stress Test",
        "description_zh": "为主题或公司逻辑建立反方框架和可跟踪的失效条件。",
        "description_en": (
            "Build a counter-case and trackable invalidation conditions for a "
            "theme or company thesis."
        ),
        "phase": 2,
    },
    "证据强弱分级": {
        "id": "serenity.evidence-grading",
        "name_en": "Evidence Grading",
        "description_zh": "区分强证据、中等证据和待验证线索，防止结论超过证据强度。",
        "description_en": (
            "Separate strong evidence, medium evidence, and unverified leads so "
            "conclusions do not exceed their support."
        ),
        "phase": 2,
    },
}
```

No UI code may duplicate this mapping.

- [ ] **Step 4: Add exact inspection result types**

Add these immutable models to `models.py`:

```python
from typing import Literal

Disposition = Literal["installable", "deferred", "skipped"]

@dataclass(frozen=True)
class AgentInspection:
    id: str
    name: LocalizedText
    description: LocalizedText

@dataclass(frozen=True)
class SkillInspection:
    id: str
    name: LocalizedText
    description: LocalizedText
    relative_path: str
    disposition: Disposition
    reason_code: str = ""

@dataclass(frozen=True)
class ComponentNotice:
    component: str
    reason_code: str
    message: LocalizedText

@dataclass(frozen=True)
class PackageInspection:
    package_id: str
    fingerprint: str
    agent: AgentInspection
    skills: tuple[SkillInspection, ...]
    deferred_components: tuple[ComponentNotice, ...]
    skipped_components: tuple[ComponentNotice, ...]
    requirements: tuple[ComponentNotice, ...]
    execution_steps: tuple[str, ...]
    warnings: tuple[LocalizedText, ...]

    def to_dict(self) -> dict:
        return package_inspection_to_dict(self)
```

`execution_steps` contains only commands that the current approved selection would execute. It is empty for the stage-1 representative Skill. Discovered scripts in deferred components belong in `requirements`/`deferred_components`, not in executed history.

- [ ] **Step 5: Implement a read-only inspector**

The inspector must:

1. resolve and validate the local root;
2. reject files that escape the root through symlinks;
3. read `IDENTITY.md`, `SOUL.md` and the seven `SKILL.md` files as UTF-8;
4. discover, but never execute, scripts and dependency declarations;
5. hash the exact files used to generate the Agent and selected Skill;
6. return serializable inspection/plan objects;
7. classify all non-stage-1 components as deferred or skipped with reason codes.

No generic plugin heuristics are added here; this is an explicit Serenity adapter behind a generic `PackageInspector` protocol.

- [ ] **Step 6: Add the inspect endpoint**

The manager owns one `PackageInspector`. The endpoint catches only declared capability errors and returns:

```json
{
  "ok": false,
  "code": "PACKAGE_INVALID",
  "error": {
    "zh-CN": "Serenity 能力包缺少“产业链层级测绘”。",
    "en-US": "The Serenity package is missing Industry Chain Layer Mapping."
  }
}
```

Unexpected exceptions are logged without source contents or secrets and return `INSPECTION_FAILED`.

- [ ] **Step 7: Verify against both fixture and the real local sample**

Run hermetic tests first:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_serenity_package.py tests/test_server.py -q
```

Expected: PASS.

The module must expose `inspect_local_package(Path) -> PackageInspection`. Then run:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from coworker.capabilities.inspection import inspect_local_package; r=inspect_local_package(Path(r'C:\Users\EDY\Desktop\serenity-full-package')); print(r.package_id, r.agent.id, len(r.skills), len(r.execution_steps))"
```

Expected output: `serenity serenity 7 0`. Do not save the absolute path or full package contents in Git.

- [ ] **Step 8: Commit**

```powershell
git add -- coworker/capabilities/models.py coworker/capabilities/serenity.py coworker/capabilities/inspection.py coworker/server/manager.py coworker/server/app.py tests/test_serenity_package.py tests/test_server.py
git commit -m "feat: inspect Serenity capability packages"
```

**Checkpoint:** ChemClaw can explain exactly what the sample package contains, but nothing has been installed or executed.

---

## Task 5: Stage, validate and atomically install the representative Skill and Agent

**Files:**

- Create: `coworker/capabilities/installer.py`
- Create: `tests/test_capability_install.py`
- Modify: `coworker/capabilities/models.py`
- Modify: `coworker/personas/manifest.py`
- Modify: `coworker/personas/registry.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`
- Modify: `tests/test_persona_manifest.py`
- Modify: `tests/test_persona_registry.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing lifecycle tests**

Use temporary state and cover:

- install creates `skills/serenity.industry-chain-mapping/SKILL.md`;
- `chemclaw.skill.json` matches the fixed schema;
- the installed Skill includes the ChemClaw Mermaid output contract;
- generated persona ID is `serenity`, name is `白毛股神 Serenity`, and `skills` references the stable Skill ID rather than copying it;
- install lands ready/enabled only after validation;
- same fingerprint is idempotent;
- changed source with stale fingerprint returns `SOURCE_CHANGED`;
- selecting any of the other six returns `PHASE_SCOPE`;
- injected copy/validation/persona failure restores the previous valid Skill and Agent;
- staging directories are removed on success and failure;
- no source script or dependency command is executed.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_capability_install.py -q
```

Expected: FAIL because `CapabilityInstaller` does not exist.

- [ ] **Step 2: Make Persona skill references available at runtime**

Keep `PersonaManifest.skills` as stable IDs and expose them through a read-only registry helper:

```python
def skill_ids(self, persona_id: str) -> list[str]:
    entry = self._entries.get(persona_id)
    if entry is None or entry.manifest is None:
        return []
    return list(entry.manifest.skills)
```

This method only returns references; it grants no tools or permissions.

- [ ] **Step 3: Fix the installer result contract**

Add to `models.py`:

```python
@dataclass(frozen=True)
class InstallResult:
    package_id: str
    fingerprint: str
    agent_id: str
    installed_skills: tuple[SkillCard, ...]
    already_current: bool

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "fingerprint": self.fingerprint,
            "agent_id": self.agent_id,
            "installed_skills": [
                skill.to_dict() for skill in self.installed_skills
            ],
            "already_current": self.already_current,
        }
```

- [ ] **Step 4: Generate the stage-1 Serenity persona**

The generated manifest frontmatter is:

```yaml
---
id: serenity
name: 白毛股神 Serenity
icon: chart
tagline: 先拆系统与瓶颈，再谈公司与证据
description: 基于产业链层级、稀缺环节、证据链和证伪条件推进研究。
family: knowledge
default_permission_mode: interactive
skills:
  - serenity.industry-chain-mapping
---
```

The body combines the executable identity/rules derived from `IDENTITY.md` and `SOUL.md`, plus an instruction to follow referenced mounted Skills. It must not copy all seven Skill bodies into the Agent.

- [ ] **Step 5: Append the installed Skill output contract**

The staged copy of `SKILL.md`, not the user’s source package, receives:

```markdown
## ChemClaw 输出约定

- 先给出分层结论，再解释每一层的关键约束。
- 当用户需要产业链图时，输出一个 fenced `mermaid` flowchart。
- Mermaid 节点文字使用引号；图后补充证据、假设和待验证项。
- 不把即时生成的 Mermaid 当作 ChemClaw 阶段五的权威标准产业链图。
```

- [ ] **Step 6: Implement stage/validate/activate/rollback**

Use this public signature:

```python
def install_serenity(
    self,
    *,
    local_path: Path,
    expected_fingerprint: str,
    selected_skill_ids: list[str],
    approved: bool,
) -> InstallResult:
```

It must follow this exact order:

1. re-inspect and compare fingerprint;
2. verify `approved is True` and the selected ID list is exactly the stage-1 allowlist;
3. create staging under the managed state filesystem;
4. copy the selected directory without following symlinks;
5. write metadata and generated persona;
6. parse the staged Skill and persona with production parsers;
7. preserve current active Skill/persona as rollback candidates;
8. replace the Skill directory atomically;
9. install and enable the validated persona;
10. re-read the active catalog and assert both references resolve;
11. remove staging/rollback copies only after success;
12. on any failure, restore previous active versions and return `INSTALL_FAILED`.

Never use `shell=True`. This stage has no dependency command to run.

- [ ] **Step 7: Add the install endpoint and structured errors**

The endpoint only accepts the fixed REST contract. A successful response returns the installed Agent summary, Skill card and `already_current` boolean. It never returns prompt bodies, source file contents or absolute installed paths.

- [ ] **Step 8: Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_capability_install.py tests/test_serenity_package.py tests/test_persona_manifest.py tests/test_persona_registry.py tests/test_server.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add -- coworker/capabilities/models.py coworker/capabilities/installer.py coworker/personas/manifest.py coworker/personas/registry.py coworker/server/manager.py coworker/server/app.py tests/test_capability_install.py tests/test_persona_manifest.py tests/test_persona_registry.py tests/test_server.py
git commit -m "feat: install Serenity representative capability atomically"
```

**Checkpoint:** The backend can safely install and activate the sample Agent plus one real Skill. There is still no normal-user Skill page.

---

## Task 6: Build the real bilingual Skill page and install confirmation flow

**Files:**

- Create: `surfaces/gui/src/capabilities/types.ts`
- Create: `surfaces/gui/src/components/SkillsView.tsx`
- Create: `surfaces/gui/src/components/SkillsView.test.tsx`
- Modify: `surfaces/gui/src/api.ts`
- Modify: `surfaces/gui/src/App.tsx`
- Modify: `surfaces/gui/src/components/Sidebar.tsx`
- Modify: `surfaces/gui/src/i18n.tsx`
- Modify: `surfaces/gui/e2e/fixtures.ts`
- Create: `surfaces/gui/e2e/skills-page.spec.ts`

- [ ] **Step 1: Define frontend contracts exactly once**

`capabilities/types.ts` mirrors the REST contracts:

```ts
import type { Locale } from "../i18n";

export type LocalizedText = Record<Locale, string>;
export type SkillStatus = "ready" | "waiting_config" | "disabled" | "unavailable";

export interface SkillCard {
  id: string;
  version: string;
  name: LocalizedText;
  description: LocalizedText;
  status: SkillStatus;
  can_use: boolean;
  agent_ids: string[];
  source_kind: string;
}
```

Add typed `getSkills`, `inspectCapabilityPackage` and `installCapabilityPackage` functions to the existing authenticated `api.ts`; do not create an unauthenticated duplicate fetch wrapper.

- [ ] **Step 2: Write failing component and E2E tests**

Cover:

- empty state has a real local-path inspection form;
- inspect preview shows one Agent, all seven research Skills, only one marked for this phase, and deferred/skipped details;
- install requires an explicit confirmation click;
- API error code is rendered in the active language;
- success reloads the real catalog and shows one ready card;
- `使用` is rendered only when `can_use` is true;
- incompatible/deferred components never appear as normal Skill cards;
- English switch changes labels without refetching or duplicating Skill bodies.

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- src/components/SkillsView.test.tsx
npm.cmd run e2e -- skills-page.spec.ts
Pop-Location
```

Expected: FAIL because the page and API client do not exist.

- [ ] **Step 3: Add a first-class Skills surface**

Extend the `surface` union with `"skills"`. Add a sidebar entry with `data-testid="nav-skills"` and route it to `<SkillsView />`. Do not add future Knowledge Graph/Data Foundation buttons.

`SkillsView` receives one callback:

```ts
onUseSkill: (skill: SkillCard) => void;
```

It does not know how sessions are implemented.

- [ ] **Step 4: Implement the inspect/confirm/install state machine**

Use explicit states:

```ts
type InstallPhase =
  | { kind: "idle" }
  | { kind: "inspecting" }
  | { kind: "preview"; inspection: PackageInspection }
  | { kind: "installing"; inspection: PackageInspection }
  | { kind: "error"; code: string; message: LocalizedText };
```

The install POST uses the fingerprint returned by preview and the fixed selected Skill ID. If the source changed, return to preview after a fresh inspection; never retry silently.

- [ ] **Step 5: Verify**

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- src/components/SkillsView.test.tsx src/i18n.test.tsx
npm.cmd run e2e -- skills-page.spec.ts chemclaw-shell.spec.ts
npm.cmd run build
Pop-Location
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- surfaces/gui/src/capabilities/types.ts surfaces/gui/src/components/SkillsView.tsx surfaces/gui/src/components/SkillsView.test.tsx surfaces/gui/src/api.ts surfaces/gui/src/App.tsx surfaces/gui/src/components/Sidebar.tsx surfaces/gui/src/i18n.tsx surfaces/gui/e2e/fixtures.ts surfaces/gui/e2e/skills-page.spec.ts
git commit -m "feat: add real ChemClaw Skills page"
```

**Checkpoint:** A non-programmer can inspect and install the representative capability from a path and see an honest ready card. The `使用` callback is present but session mounting is implemented next.

---

## Task 7: Persist visible session mounts and resolve the latest valid Skill every turn

**Files:**

- Create: `coworker/skills/mounts.py`
- Create: `tests/test_skill_mounts.py`
- Modify: `coworker/sessions.py`
- Modify: `coworker/conversations.py`
- Modify: `coworker/agent.py`
- Modify: `coworker/server/manager.py`
- Modify: `coworker/server/app.py`
- Modify: `tests/test_session_persona.py`
- Modify: `tests/test_skills.py`
- Modify: `tests/test_server.py`
- Create: `surfaces/gui/src/components/MountedSkillsBar.tsx`
- Create: `surfaces/gui/src/components/MountedSkillsBar.test.tsx`
- Modify: `surfaces/gui/src/types.ts`
- Modify: `surfaces/gui/src/api.ts`
- Modify: `surfaces/gui/src/App.tsx`
- Modify: `surfaces/gui/src/components/SkillsView.tsx`
- Modify: `surfaces/gui/e2e/fixtures.ts`
- Create: `surfaces/gui/e2e/skill-mount.spec.ts`

- [ ] **Step 1: Write failing persistence and runtime tests**

Cover:

- new and migrated `SessionRecord` values default to `[]`;
- SQLite save/load/list round-trip stable Skill IDs;
- a new WebSocket query accepts repeated `skill` parameters;
- reconnect uses stored mounts rather than client guesses;
- Agent default references and explicit mounts are de-duplicated in order;
- an unknown explicit Skill on a brand-new session returns a structured error;
- ready event and session list expose mount summaries;
- mounted instructions appear in `engine.context_provider()`;
- editing the active installed `SKILL.md` from marker `version one` to `version two` changes the next `context_provider()` result without rebuilding the engine;
- mounted Skills do not add tools or alter permission mode.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_skill_mounts.py tests/test_session_persona.py tests/test_skills.py -q
```

Expected: FAIL because mount persistence and resolution do not exist.

- [ ] **Step 2: Add the idempotent SQLite migration**

Add `mounted_skills TEXT` to the create schema and migration list. Serialize it as a JSON string list. Malformed legacy JSON reads as `[]` and never crashes session listing.

- [ ] **Step 3: Implement dynamic mount resolution**

`mounts.py` exposes:

```python
@dataclass(frozen=True)
class MountedSkill:
    id: str
    version: str
    name_zh: str
    name_en: str
    status: str
    instructions: str
    resources_path: str

def resolve_mounted_skills(
    skill_dirs: list[Path],
    stable_ids: list[str],
) -> list[MountedSkill]:
    loader = SkillLoader(skill_dirs)
    return [resolve_one(loader, stable_id) for stable_id in dedupe(stable_ids)]

def render_mounted_skill_context(
    skill_dirs: list[Path],
    stable_ids: list[str],
) -> str:
    mounted = resolve_mounted_skills(skill_dirs, stable_ids)
    return "\n\n".join(
        f"<mounted-skill id=\"{item.id}\" version=\"{item.version}\">\n"
        f"{item.instructions}\n"
        "</mounted-skill>"
        for item in mounted
        if item.status == "ready"
    )
```

The resolver recreates `SkillLoader` on every call. This is the stage-1 implementation of “next turn uses the latest active content.” It does not reload mid-turn.

- [ ] **Step 4: Merge Agent and session references at the manager boundary**

Extend `SessionManager.get_engine` with `mounted_skill_ids: Optional[list[str]]`.

- Existing record: use `record.mounted_skills`.
- New record: use requested IDs.
- In both cases: prepend `self.personas.skill_ids(agent_name)` and de-duplicate.
- Pass the final IDs to `build_engine`.
- Save them from `engine.mounted_skill_ids`.

`build_engine` adds the rendered mount block inside the existing dynamic `context_provider`; it keeps the ordinary progressive-disclosure catalog and `load_skill` tool unchanged.

- [ ] **Step 5: Extend the WebSocket and ready event**

Read mounts with:

```python
mounted_skill_ids = [
    value.strip()
    for value in ws.query_params.getlist("skill")
    if value.strip()
]
```

Return summaries in `ready`. Do not return full instructions to the browser.

- [ ] **Step 6: Write failing frontend mount tests**

Cover:

- `Session` URL contains one `skill` query per ID;
- clicking `使用` starts a fresh `serenity` session with the representative ID;
- ready data renders a visible Chinese/English mount chip;
- selecting an old conversation clears pending request state, then uses server-ready mounts;
- sending multiple turns keeps the chip;
- unavailable mount status is visible and does not claim the Skill ran.

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- src/components/MountedSkillsBar.test.tsx
npm.cmd run e2e -- skill-mount.spec.ts
Pop-Location
```

Expected: FAIL before UI wiring.

- [ ] **Step 7: Wire the frontend without coupling SkillsView to WebSocket details**

`App.startSkillSession(skill)` chooses `skill.agent_ids[0] || "cowork"`, clears the transcript, stores pending stable IDs, creates a new session ID and returns to the session surface. `Session` receives an options object:

```ts
interface SessionOptions {
  mountedSkillIds?: string[];
}
```

`MountedSkillsBar` renders the authoritative summaries from `ready`, above the transcript and below the session facts. Do not infer mounted state from the last clicked card after `ready` arrives.

- [ ] **Step 8: Verify backend and frontend**

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
.\.venv\Scripts\python.exe -m pytest tests/test_skill_mounts.py tests/test_session_persona.py tests/test_skills.py tests/test_server.py tests/test_permissions_risk.py -q
Push-Location 'surfaces\gui'
npm.cmd test -- src/components/MountedSkillsBar.test.tsx src/components/SkillsView.test.tsx
npm.cmd run e2e -- skill-mount.spec.ts chat.spec.ts approval-card.spec.ts
npm.cmd run build
Pop-Location
```

Expected: PASS. Permissions regression proves a mounted Skill remains instruction/context, not authority.

- [ ] **Step 9: Commit**

```powershell
git add -- coworker/skills/mounts.py coworker/sessions.py coworker/conversations.py coworker/agent.py coworker/server/manager.py coworker/server/app.py tests/test_skill_mounts.py tests/test_session_persona.py tests/test_skills.py tests/test_server.py surfaces/gui/src/components/MountedSkillsBar.tsx surfaces/gui/src/components/MountedSkillsBar.test.tsx surfaces/gui/src/types.ts surfaces/gui/src/api.ts surfaces/gui/src/App.tsx surfaces/gui/src/components/SkillsView.tsx surfaces/gui/e2e/fixtures.ts surfaces/gui/e2e/skill-mount.spec.ts
git commit -m "feat: persist and display session Skill mounts"
```

**Checkpoint:** Clicking the installed Skill now creates a real Serenity conversation, visibly mounts it, persists it and reloads current content on later turns.

---

## Task 8: Render Mermaid safely with source view and SVG/PNG export

**Files:**

- Create: `surfaces/gui/src/components/MermaidBlock.tsx`
- Create: `surfaces/gui/src/components/MermaidBlock.test.tsx`
- Create: `surfaces/gui/src/exports.ts`
- Modify: `surfaces/gui/src/components/Markdown.tsx`
- Modify: `surfaces/gui/src/components/Markdown.test.tsx`
- Modify: `surfaces/gui/src/styles.css`
- Modify: `surfaces/gui/package.json`
- Modify: `surfaces/gui/package-lock.json`
- Modify: `surfaces/gui/e2e/fixtures.ts`
- Create: `surfaces/gui/e2e/mermaid.spec.ts`

- [ ] **Step 1: Pin the official Mermaid dependency**

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd install mermaid@11.16.0 --save
Pop-Location
```

Expected: `package.json` and lockfile record exactly `11.16.0`.

- [ ] **Step 2: Write failing renderer tests**

Mock Mermaid in Vitest and cover:

- fenced `mermaid` block renders an SVG container;
- ordinary fenced code remains ordinary code;
- default view is diagram;
- Diagram/Source toggle preserves exact source;
- parse/render failure shows a localized error and source rather than blanking the message;
- SVG and PNG buttons call export helpers with safe filenames;
- changing locale changes controls without rerendering the diagram source;
- artifact links still behave exactly as before.

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- src/components/MermaidBlock.test.tsx src/components/Markdown.test.tsx
Pop-Location
```

Expected: FAIL because MermaidBlock does not exist.

- [ ] **Step 3: Implement lazy, strict rendering**

Initialize Mermaid once with:

```ts
mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
  maxTextSize: 50_000,
  suppressErrorRendering: true,
  theme: "neutral",
});
```

Use a monotonic render ID and cancel stale effects. Limit source length before parsing. Insert only Mermaid’s returned SVG into a component-owned element; never execute links or scripts from diagram source.

- [ ] **Step 4: Integrate at the Markdown seam**

Override the ReactMarkdown `pre` renderer, detect a single child whose class is `language-mermaid`, and pass its exact text to `MermaidBlock`. Preserve existing `artifact:` links and all non-Mermaid code blocks.

- [ ] **Step 5: Implement exports**

- SVG: download the already rendered SVG string as `image/svg+xml;charset=utf-8`.
- PNG: load that SVG through an object URL into an `Image`, draw to a bounded canvas at device-pixel ratio, export `image/png`, then revoke every object URL.
- Reject canvas dimensions above the defined memory limit and show a localized error.
- Filenames use `chemclaw-diagram-YYYYMMDD-HHmmss`.

- [ ] **Step 6: Add a real browser E2E path**

The fake WebSocket returns a fenced Mermaid flowchart for the message `画产业链图`. Assert:

- an SVG is visible;
- Chinese controls are visible;
- Source shows the original flowchart text;
- returning to Diagram restores SVG;
- malformed Mermaid shows the localized fallback;
- both export buttons are enabled after a successful render.

Run:

```powershell
Push-Location 'surfaces\gui'
npm.cmd test -- src/components/MermaidBlock.test.tsx src/components/Markdown.test.tsx
npm.cmd run e2e -- mermaid.spec.ts chat.spec.ts
npm.cmd run build
Pop-Location
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- surfaces/gui/src/components/MermaidBlock.tsx surfaces/gui/src/components/MermaidBlock.test.tsx surfaces/gui/src/exports.ts surfaces/gui/src/components/Markdown.tsx surfaces/gui/src/components/Markdown.test.tsx surfaces/gui/src/styles.css surfaces/gui/package.json surfaces/gui/package-lock.json surfaces/gui/e2e/fixtures.ts surfaces/gui/e2e/mermaid.spec.ts
git commit -m "feat: render and export Mermaid diagrams"
```

**Checkpoint:** The mounted Skill can produce a real diagram with safe fallback and export. This diagram is conversational output, not the future authoritative chemical industry-chain asset.

---

## Task 9: Run the complete vertical slice and close the stage-1 gate

**Files:**

- Create: `surfaces/gui/e2e/skill-vertical-slice.spec.ts`
- Modify: `surfaces/gui/e2e/fixtures.ts`
- Modify: `docs/chemclaw/README.md`
- Modify: `docs/chemclaw/TESTING.md`
- Modify: this plan by checking completed boxes and recording the final commit

- [ ] **Step 1: Write the end-to-end acceptance specification**

The single browser flow must:

1. boot as Chinese ChemClaw;
2. open Skills;
3. enter the local Serenity package path;
4. inspect and show one Agent plus seven research Skills;
5. confirm that only `产业链层级测绘` will install;
6. install and show its ready card;
7. click `使用`;
8. arrive at a fresh `serenity` conversation with a visible mount chip;
9. send a natural-language industry-chain request;
10. receive and render Mermaid;
11. switch source/diagram and expose SVG/PNG exports;
12. send a second message and retain the mount;
13. switch to English and retain the same stable IDs/session.

Run before completing the fixture:

```powershell
Push-Location 'surfaces\gui'
npm.cmd run e2e -- skill-vertical-slice.spec.ts
Pop-Location
```

Expected: FAIL until the fixture models the full inspect/install/catalog/ready sequence.

- [ ] **Step 2: Complete the hermetic fixture state machine**

The fixture must mutate in-memory catalog state only after a successful install POST, reflect mount IDs from the WebSocket URL in `ready`, and emit a Mermaid assistant message. It must not read the real desktop package or state directory.

- [ ] **Step 3: Run all protection suites**

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
.\.venv\Scripts\python.exe -m pytest -q
Push-Location 'surfaces\gui'
npm.cmd test
npm.cmd run build
npm.cmd run e2e
Pop-Location
```

Expected: every command exits 0. Record exact counts and durations in `docs/chemclaw/TESTING.md`.

- [ ] **Step 4: Run the real local-source smoke path without external writes**

Start the FastAPI backend and Vite frontend with:

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
$env:UV_CACHE_DIR='D:\OpenWorker\.chemclaw-dev\uv-cache'
$env:UV_PYTHON_INSTALL_DIR='D:\OpenWorker\.chemclaw-dev\uv-python'
.\.venv\Scripts\python.exe -m coworker.server.run
```

In a second terminal:

```powershell
$env:COWORKER_STATE_DIR='D:\OpenWorker\.chemclaw-dev\state'
Push-Location 'surfaces\gui'
npm.cmd run dev
```

Manually perform the twelve Chinese UI checks from Step 1 using `C:\Users\EDY\Desktop\serenity-full-package`. Use a configured model only if the user chooses; otherwise verify installation, mount visibility and a fixture/static Mermaid message without spending model tokens. Do not call real MCP writes.

- [ ] **Step 5: Review scope and security**

Confirm:

- no SAG code or data was copied;
- only one research Skill is active;
- no package script/dependency command ran;
- failed install tests preserve previous active content;
- mounted Skill did not alter registry tools or permission mode;
- the default UI contains no visible OpenWorker branding;
- upstream license files remain;
- updater UI is disabled;
- no real credentials, absolute source paths or package bodies entered Git.

- [ ] **Step 6: Update project control documents**

Set README status to “阶段 1 已实现，等待用户源码验收” only if every required automated command passed. If a command could not run, record it as not run and keep the gate open.

- [ ] **Step 7: Commit the acceptance slice**

```powershell
git add -- surfaces/gui/e2e/fixtures.ts surfaces/gui/e2e/skill-vertical-slice.spec.ts docs/chemclaw/README.md docs/chemclaw/TESTING.md docs/superpowers/plans/2026-07-29-chemclaw-first-vertical-slice.md
git commit -m "test: verify ChemClaw first vertical slice"
git status --short --branch
```

Expected: clean Worktree after commit.

**Final checkpoint:** Stop for user acceptance. Do not merge `main` or start stage 2 without explicit user approval.

---

## Cross-conversation execution map

To control Token use, use one Codex conversation per checkpoint unless a task remains small:

1. Task 1 — environment and baseline.
2. Task 2 — ChemClaw/i18n shell.
3. Task 3 — stable Skill catalog.
4. Task 4 — Serenity inspection.
5. Task 5 — atomic representative install.
6. Task 6 — real Skills page.
7. Task 7 — session mount and latest-version resolution.
8. Task 8 — Mermaid.
9. Task 9 — full acceptance.

Every new conversation starts with:

> 继续 ChemClaw 阶段 1。请先阅读 AGENTS.md、项目控制台、已批准规格和 `docs/superpowers/plans/2026-07-29-chemclaw-first-vertical-slice.md`，汇报当前未完成任务。只执行计划中的 Task N，测试通过并形成小提交后停止，不要提前做后续 Task。

Replace `N` with the chosen task number. A completed checkbox and Git commit, rather than chat memory, determine where the next conversation resumes.
