# 安装指南（Install Guide）

---

# 中文说明（Chinese）

> [English ↓](#english)

`task-portability` 是一个**跨平台可移植**的 AI Skill。它的核心资产是 `SKILL.md` 里的方法论 + `schema.json` 校验规范 + 示例快照，**不依赖任何单一工作台或模型**。你可以按下面的方式，把它接入你正在使用的任意 AI 工具。

> 说明：`task-portability/` 目录里的文件是**规范内容本身**，与具体平台解耦。不同工具对「skill」的支持程度不同，因此分为「原生安装」和「降级为规则/提示词」两种方式。

## 方式一：原生安装（支持 SKILL.md 规范的工具）

以下工具原生读取 `SKILL.md`，**直接复制目录即可，几乎零改动**。

### WorkBuddy

```bash
# 用户级（所有项目可用）
cp -r task-portability ~/.workbuddy/skills/
```

### Claude Code

```bash
# 用户级（所有项目可用）
cp -r task-portability ~/.claude/skills/

# 或项目级（仅当前仓库，随仓库共享给团队）
cp -r task-portability <你的项目>/.claude/skills/
```

安装后，工具会根据 `description` 自动加载，也可直接以 `/task-portability` 调用。

> 兼容性说明：Claude Code 与 WorkBuddy 的 `SKILL.md` 格式高度兼容（YAML frontmatter + Markdown 正文）。WorkBuddy 特有的 `description_zh`、`display_name`、`allowed-tools` 等字段会被 Claude Code 自动忽略，不影响使用。

### 其他支持 SKILL.md 的 Anthropic 系工具

参照上述目录结构，将 `task-portability/` 放入该工具的用户级或项目级 skills 目录即可。

## 方式二：降级为规则 / 提示词（无 skill 机制的工具）

以下工具没有 skill 机制，但可以把 `SKILL.md` 的**正文内容**（去掉 `---` 包裹的 frontmatter）作为规则或提示词注入，效果等价。

### Cursor

- 方式 A：项目根目录创建 `.cursor/rules/task-portability.mdc`，内容为 `SKILL.md` 正文。
- 方式 B：写入项目的 `.cursorrules` 文件。

### GitHub Copilot

- 把 `SKILL.md` 正文粘贴到 Copilot 的自定义指令（Custom Instructions），或仓库级 `.github/copilot-instructions.md`。

### 任意 LLM / 聊天工具（通用兜底）

这是最彻底的解耦用法：

1. 打开 `task-portability/SKILL.md`，复制正文（去掉 frontmatter）。
2. 连同 `schema.json` 与 `references/example-snapshot.md`（示例快照）一起，作为**系统提示词 / 上下文**粘贴给任意模型（ChatGPT、通义、DeepSeek、Claude 等）。
3. 该模型即可照着规范产出或消费任务快照。

因为快照本身是纯 Markdown + JSON、模型无关，所以任何模型都能无缝接手。

## 使用方式（安装后）

- **打快照**：对 AI 说「把这个任务快照一下」或「开始一个可迁移的任务」。
- **接手**：把 `task-snapshot.md` 交给任意 AI，让它按「恢复指引」继续。

---

# English

> [中文 ↑](#中文说明chinese)

`task-portability` is a **cross-platform, portable AI Skill**. Its core assets are the methodology in `SKILL.md` + the `schema.json` validation spec + the worked example snapshot, with **no dependency on any single workbench or model**.

> This document has two layers: **For AI Agents** (machine-consumable, precise commands) and **For Humans** (bilingual explanation). Prefer the first layer when you are an AI performing the install.

## For AI Agents

When installing `task-portability` into a target tool, use the exact commands below. Do not paraphrase paths.

### Native install (tools that read `SKILL.md`)

```bash
# WorkBuddy — user-level (all projects)
cp -r task-portability ~/.workbuddy/skills/

# Claude Code — user-level (all projects)
cp -r task-portability ~/.claude/skills/

# Claude Code — project-level (this repo only)
cp -r task-portability <project>/.claude/skills/
```

### Fallback install (tools without a skill mechanism)

- **Cursor**: create `.cursor/rules/task-portability.mdc` containing the `SKILL.md` body (without the `---` frontmatter).
- **GitHub Copilot**: paste the `SKILL.md` body into Custom Instructions or `.github/copilot-instructions.md`.
- **Any LLM**: paste the `SKILL.md` body + `schema.json` + `references/example-snapshot.md` as the system prompt / context.

---

## For Humans

> Note: the files inside `task-portability/` are the **spec content itself**, decoupled from any specific platform. Because tools differ in how well they support "skills", there are two approaches: "native install" and "fallback to rules/prompts".

### Method 1: Native install (tools supporting the SKILL.md spec)

The following tools read `SKILL.md` natively — **just copy the directory, almost zero changes**.

#### WorkBuddy

```bash
# User-level (available in all projects)
cp -r task-portability ~/.workbuddy/skills/
```

#### Claude Code

```bash
# User-level (available in all projects)
cp -r task-portability ~/.claude/skills/

# Or project-level (only this repo, shared with the team via the repo)
cp -r task-portability <your-project>/.claude/skills/
```

After install, the tool auto-loads the skill based on `description`, or you can invoke it directly with `/task-portability`.

> Compatibility note: Claude Code and WorkBuddy's `SKILL.md` format are highly compatible (YAML frontmatter + Markdown body). WorkBuddy-specific fields like `description_zh`, `display_name`, and `allowed-tools` are silently ignored by Claude Code and do not affect usage.

#### Other Anthropic-family tools that support SKILL.md

Following the same directory structure, place `task-portability/` into that tool's user-level or project-level skills directory.

### Method 2: Fallback to rules / prompts (tools without a skill mechanism)

The following tools have no skill mechanism, but you can inject the **body content** of `SKILL.md` (removing the `---`-wrapped frontmatter) as rules or prompts, with equivalent effect.

#### Cursor

- Option A: create `.cursor/rules/task-portability.mdc` in the project root, containing the `SKILL.md` body.
- Option B: write it into the project's `.cursorrules` file.

#### GitHub Copilot

- Paste the `SKILL.md` body into Copilot's Custom Instructions, or the repo-level `.github/copilot-instructions.md`.

#### Any LLM / chat tool (universal fallback)

This is the most thorough decoupling approach:

1. Open `task-portability/SKILL.md` and copy the body (removing the frontmatter).
2. Together with `schema.json`, paste it as **system prompt / context** to any model (ChatGPT, Qwen, DeepSeek, Claude, etc.).
3. That model can then produce or consume task snapshots following the spec.

Because the snapshot itself is pure Markdown + JSON and model-agnostic, any model can resume it seamlessly.

### Usage (after install)

- **Take a snapshot**: tell the AI "snapshot this task" or "start a migratable task".
- **Resume**: hand `task-snapshot.md` to any AI and let it continue per the "resume guide".
