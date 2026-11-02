# task-portability

> 这是一个 **AI Skill**，用于把 AI 任务从具体工作台、模型、平台中解耦，让任务可移植、可迁移、可接续。
>
> This is an **AI Skill** that decouples AI tasks from specific workbenches, models, and platforms, making tasks portable, migratable, and resumable.

---

## 目录（Table of Contents）

- [中文说明](#中文说明-chinese)
  - [解决什么问题](#解决什么问题)
  - [核心产出](#核心产出)
  - [什么时候用](#什么时候用)
  - [怎么用](#怎么用)
  - [关键设计原则](#关键设计原则)
  - [文件结构](#文件结构)
- [English](#english)
  - [What Problem It Solves](#what-problem-it-solves)
  - [Core Output](#core-output)
  - [When to Use](#when-to-use)
  - [How to Use](#how-to-use)
  - [Key Design Principles](#key-design-principles)
  - [File Structure](#file-structure)

---

# 中文说明（Chinese）

把 AI 任务从具体工作台 / 模型 / 平台中**解耦**，将任务的完整状态固化成**自包含的可移植快照**，让任意 AI 或人读取一份文件即可无缝接手，迁移成本降到最低。

## 解决什么问题

AI 任务通常"活"在某一次对话、某一个工具、某一个模型里。一旦换环境、换模型、换平台，任务的上下文、进度、决策就丢了，迁移成本极高。

本 skill 把任务真正的资产——**上下文、进度、工件**——冻结成模型无关、平台无关的数据，让任务"搬得走、接得上"。

## 核心产出

每次快照生成一个**任务快照包**：

```
<task-slug>/
├── task-snapshot.md    # 人类可读 → 任意 AI 或人读这一份即可接手
├── task-snapshot.json  # 可编程 → 可校验、可转换、可追踪增量
└── artifacts/          # （可选）关键工件清单
```

- **Markdown** 保证"任何模型都能读"（模型无关的根基）
- **JSON** 保证"可校验、可转成其他格式"（平台无关、可迁移的根基）

## 什么时候用

| 场景 | 动作 |
|---|---|
| 开始一个可移植的任务 | 初始化快照 |
| 任务进行中要"打点"/换环境 | 增量快照 |
| 交接给别人 / 换模型 | 增量快照 + 详细交接备注 |
| 接手别人/别处的任务 | 读快照，按恢复指引接续 |

**任务开启前、任务过程中都可以用。**

## 怎么用

1. 对 AI 说：**"把这个任务快照一下 / 打包成可移植的"**，或 **"开始一个可迁移的任务"**。
2. AI 会在任务目录下生成 `.task-portability/<slug>/` 快照包。
3. 迁移时，把整个 `<slug>/` 目录 + 快照里记录的关键文件带走。
4. 新环境中，让任意 AI 读 `task-snapshot.md`，即可接手。

## 关键设计原则

1. **自包含** —— 接手者只读最新一份快照即可接手，不回看历史。
2. **双格式同步** —— Markdown 与 JSON 描述同一份状态，改一处同步另一处。
3. **绝对路径** —— 避免跨环境路径失效。
4. **关键决策必留理由** —— 决策 + 理由是任务里最易丢失、最有价值的资产。
5. **隐性知识必写下来** —— "口口相传才会知道"的东西，写进交接备注。

## 文件结构

```
task-portability/
├── SKILL.md               # skill 主体（方法论 + 工作流）
├── README.md              # 本说明
├── schema.json            # 快照 JSON 的校验 Schema
├── templates/
│   └── task-snapshot.md.tpl  # Markdown 快照模板
└── references/
    └── example-snapshot.md   # 示例快照（成品长什么样）
```

---

# English

Decouple AI tasks from any specific workbench, model, or platform by snapshotting a task's full state into a **self-contained, portable bundle**, so any AI or human can resume the task seamlessly by reading a single file — with minimal migration cost.

## What Problem It Solves

AI tasks typically "live" inside a particular conversation, tool, or model. Switch environments, models, or platforms, and the task's context, progress, and decisions are lost — making migration extremely costly.

This skill freezes a task's true assets — **context, progress, and artifacts** — into model-agnostic, platform-agnostic data, so tasks can be "carried over and picked up" anywhere.

## Core Output

Each snapshot produces a **task snapshot bundle**:

```
<task-slug>/
├── task-snapshot.md    # Human-readable → any AI or person can resume by reading this one file
├── task-snapshot.json  # Programmable → validatable, convertible, and diffable for incremental tracking
└── artifacts/          # (Optional) list of key artifacts
```

- **Markdown** ensures "any model can read it" (the foundation of model-agnosticism)
- **JSON** ensures "validatable and convertible to other formats" (the foundation of platform-agnosticism and portability)

## When to Use

| Scenario | Action |
|---|---|
| Start a portable task | Initialize a snapshot |
| Mid-task checkpoint / switch environment | Incremental snapshot |
| Hand off to someone / switch model | Incremental snapshot + detailed handoff notes |
| Resume someone else's task | Read the snapshot, follow the resume guide |

**Works both before a task starts and during a task.**

## How to Use

1. Tell the AI: **"Snapshot this task / package it as portable"**, or **"Start a migratable task"**.
2. The AI generates a `.task-portability/<slug>/` bundle in the task directory.
3. To migrate, take the whole `<slug>/` directory plus the key files recorded in the snapshot.
4. In the new environment, have any AI read `task-snapshot.md` to resume.

## Key Design Principles

1. **Self-contained** — a successor can resume by reading only the latest snapshot, without revisiting history.
2. **Dual-format sync** — Markdown and JSON describe the same state; change one and sync the other.
3. **Absolute paths** — avoid path breakage across environments.
4. **Decisions always carry their rationale** — decisions + reasons are the most easily lost, most valuable asset.
5. **Tacit knowledge must be written down** — things "only known by word of mouth" go into the handoff notes.

## File Structure

```
task-portability/
├── SKILL.md               # Skill body (methodology + workflow)
├── README.md              # This document
├── schema.json            # Validation schema for the snapshot JSON
├── templates/
│   └── task-snapshot.md.tpl  # Markdown snapshot template
└── references/
    └── example-snapshot.md   # Example snapshot (what the output looks like)
```
