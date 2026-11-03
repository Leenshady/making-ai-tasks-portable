# Making AI Tasks Portable

> 这是一个 **AI Skill 项目**，用于把 AI 任务从具体工作台、模型、平台中解耦，让任务可移植、可迁移、可接续。
>
> This is an **AI Skill project** that decouples AI tasks from specific workbenches, models, and platforms, making tasks portable, migratable, and resumable.

---

# 中文说明（Chinese）

> [English ↓](#english)

让 AI 任务从具体工作台 / 模型 / 平台中**解耦**，通过把任务完整状态固化成**自包含的可移植快照**，使任意 AI 或人读取一份文件即可无缝接手，迁移成本降到最低。

## 核心思路

一个 AI 任务的真正资产不是"它跑在哪个工具上"，而是三样东西：

1. **上下文**（Context）—— 目标、约束、背景、关键决策
2. **进度**（Progress）—— 做完了什么、做到哪一步、下一步是什么
3. **工件**（Artifacts）—— 产出了哪些文件、依赖哪些资源、环境要求

只要这三样被冻结成**模型无关、平台无关、自包含**的数据，任务就不再被任何单一环境绑架。

## 内容

| 目录/文件 | 说明 |
|---|---|
| `task-portability/` | AI Skill：任务可移植性的完整实现 |
| └ `SKILL.md` | skill 主体（方法论 + 工作流 + 硬性规则） |
| └ `schema.json` | 快照 JSON 的校验 Schema |
| └ `scripts/` | 辅助脚本（纯 Python 3 标准库，可选；`scaffold.py` 同时渲染 Markdown） |
| └ `references/` | 示例快照与术语表 |

## 快照产出

每次快照生成一个**任务快照包**：

```
<task-slug>/
├── task-snapshot.md    # 人类可读 → 任意 AI 或人读这一份即可接手
└── task-snapshot.json  # 可编程 → 可校验、可转换、可追踪增量
```

- **Markdown** 保证"任何模型都能读"（模型无关的根基）
- **JSON** 保证"可校验、可转成其他格式"（平台无关、可迁移的根基）
- **工件只记位置，不复制本体** —— 项目根目录、VCS 锚点（remote + branch + 已解析的 commit）、关键文件、依赖都记录在快照的 `artifacts` 小节里

## 安装 skill

支持 WorkBuddy、Claude Code（原生安装）、Cursor、GitHub Copilot 及任意 LLM（降级为规则/提示词）等多种工具。详见 [INSTALL.md](INSTALL.md)。

最快方式（WorkBuddy）：

```
cp -r task-portability ~/.workbuddy/skills/
```

之后即可使用（"把这个任务快照一下" / "开始一个可迁移的任务"）。

## 设计原则

1. **自包含** —— 接手者只读最新一份快照即可接手，不回看历史。
2. **双格式同步** —— Markdown 与 JSON 描述同一份状态，改一处同步另一处。
3. **绝对路径** —— 避免跨环境路径失效。
4. **关键决策必留理由** —— 决策 + 理由是任务里最易丢失、最有价值的资产。
5. **隐性知识必写下来** —— "口口相传才会知道"的东西，写进交接备注。
6. **工作区以仓库为准** —— 只记项目根目录与 `remote` + `branch` + 解析后的 commit 哈希；任何环境都能 clone 重建，而工作台的空间 / 项目 id 一出工具就失效。

---

# English

> [中文 ↑](#中文说明chinese)

Decouple AI tasks from any specific workbench, model, or platform by snapshotting a task's full state into a **self-contained, portable bundle**, so any AI or human can resume the task seamlessly by reading a single file — with minimal migration cost.

## Core Idea

The real assets of an AI task are not "which tool it runs on", but three things:

1. **Context** — goals, constraints, background, key decisions
2. **Progress** — what's done, where it stands, what's next
3. **Artifacts** — which files were produced, what resources are depended on, environment requirements

Once these three are frozen into **model-agnostic, platform-agnostic, self-contained** data, the task is no longer held hostage by any single environment.

## Contents

| Directory / File | Description |
|---|---|
| `task-portability/` | The AI Skill: complete implementation of task portability |
| └ `SKILL.md` | Skill body (methodology + workflow + hard rules) |
| └ `schema.json` | Validation schema for the snapshot JSON |
| └ `scripts/` | Helper scripts (Python 3 stdlib only, optional; `scaffold.py` renders the Markdown too) |
| └ `references/` | Example snapshot and glossary |

## Snapshot Output

Each snapshot produces a **task snapshot bundle**:

```
<task-slug>/
├── task-snapshot.md    # Human-readable → any AI or person can resume by reading this one file
└── task-snapshot.json  # Programmable → validatable, convertible, and diffable for incremental tracking
```

- **Markdown** ensures "any model can read it" (the foundation of model-agnosticism)
- **JSON** ensures "validatable and convertible to other formats" (the foundation of platform-agnosticism and portability)
- **Artifacts record locations, not bodies** — project root, VCS anchor (remote + branch + resolved commit), key files, and dependencies all live in the snapshot's `artifacts` section

## Installing the Skill

Supports WorkBuddy, Claude Code (native install), Cursor, GitHub Copilot, and any LLM (as rules/prompts). See [INSTALL.md](INSTALL.md).

Fastest way (WorkBuddy):

```
cp -r task-portability ~/.workbuddy/skills/
```

Then use it ("snapshot this task" / "start a migratable task").

## Design Principles

1. **Self-contained** — a successor can resume by reading only the latest snapshot, without revisiting history.
2. **Dual-format sync** — Markdown and JSON describe the same state; change one and sync the other.
3. **Absolute paths** — avoid path breakage across environments.
4. **Decisions always carry their rationale** — decisions + reasons are the most easily lost, most valuable asset.
5. **Tacit knowledge must be written down** — things "only known by word of mouth" go into the handoff notes.
6. **Workspace anchored to the repo** — record the project root plus `remote` + `branch` + the resolved commit hash: any environment can rebuild that with a clone, while a workbench's space / project id dies with the tool.
