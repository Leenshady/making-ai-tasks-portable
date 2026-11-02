---
name: task-portability
description: "Decouple AI tasks from any specific workbench, model, or platform by snapshotting a task's full state into a portable, self-contained bundle (Markdown + JSON). Lets any AI or human resume the task in any environment with minimal migration cost. Use when the user wants to make an AI task portable, migrate a task between environments, hand off a task to another model/tool, checkpoint a task before switching context, or freeze task state (goal, progress, decisions, TODOs, files, dependencies). Works both before a task starts (initialization) and during a task (incremental checkpoint)."
description_zh: "将 AI 任务从具体工作台/模型/平台中解耦，把任务完整状态固化成可移植的自包含快照（Markdown + JSON），让任意 AI 或人可在任意环境以最小迁移成本接续任务。"
description_en: "Decouple AI tasks from workbench/model/platform by snapshotting task state into portable bundles."
version: 1.0.0
author: "Leenshady"
display_name: "让 AI 任务可迁移"
display_name_en: "Make AI Tasks Portable"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
examples_zh:
  - "把这个任务快照一下"
  - "开始一个可迁移的任务"
  - "把这个任务交接给别人"
examples_en:
  - "Snapshot this task's current state"
  - "Start a portable task"
  - "Hand off this task to someone else"
---

# Task Portability — Make AI Tasks Migratable

Your job is to **detach an AI task's state from its execution environment** and freeze it into **model-agnostic, platform-agnostic, self-contained data**, so that any AI or human can resume the task by reading a single snapshot — removing the dependency on any specific workbench or model and minimizing migration cost.

## Core Idea

The true assets of an AI task are not "which tool it runs on", but three things:

1. **Context** — goals, constraints, background, key decisions
2. **Progress** — what is done, where it stands, what is next
3. **Artifacts** — which files were produced, what resources are depended on, environment requirements

Once these three are frozen into self-contained data, the task is no longer hostage to any single environment. The snapshot itself *is* the migratable task.

## Output: Task Snapshot Bundle

> Before generating a snapshot, read `@references/example-snapshot.md` for a complete example of a valid snapshot. For term definitions, read `@references/glossary.md`. Field names MUST match `schema.json` exactly.

Each snapshot produces two complementary files in one directory:

```
<task-slug>/
├── task-snapshot.md    # Human-readable: any AI or person can resume by reading this one file
├── task-snapshot.json  # Programmable: validatable, convertible, diffable
└── artifacts/          # (Optional) manifest of key artifacts
```

### Why two formats

- **Markdown** — zero-barrier. Any model, editor, or human can read one file and understand the full task. This is the foundation of model-agnosticism.
- **JSON** — structured. Can be validated, converted (e.g. to an A2A task card), or diffed for incremental tracking. This is the foundation of platform-agnosticism and portability.

Both describe the **same state**. Markdown is the presentation layer of JSON; JSON is the structural layer of Markdown. Change one, sync the other.

## Snapshot Content Specification

A valid snapshot MUST cover the following fields. **Field names MUST match `schema.json` exactly — do not rename or substitute synonyms** (e.g. never write "archive" for `snapshot`, "mirror" for `bundle`). This is what keeps snapshots consumable across models.

### 1. identity & meta
- `task_id`: unique identifier (format `task-YYYYMMDD-HHMM`, generated from current time)
- `title`: one-line task title
- `slug`: filesystem-safe short name (lowercase, hyphens)
- `created_at` / `updated_at`: ISO 8601 timestamps — **MUST be obtained via the `date` command, never calculated by hand**
- `status`: `initialized` | `in-progress` | `checkpointed` | `completed` | `abandoned`
- `schema_version`: snapshot format version

### 2. goal & constraints
- `goal`: the end result, written as a verifiable statement
- `success_criteria`: how to judge "done" (observable, testable)
- `constraints`: hard limits (tech stack, prohibitions, compliance, scope)
- `non_goals`: what is explicitly OUT of scope, to prevent the successor from drifting

### 3. context
- `background`: why this task exists, prior context
- `key_decisions`: decisions already made + their `reason` (the most easily lost, most valuable asset)
- `assumptions`: current assumptions, including which are unverified
- `terminology`: domain terms and conventions

### 4. progress & plan
- `completed`: done items (specific, verifiable)
- `in_progress`: current work and how far it has gone (as granular as possible)
- `next_steps`: concrete next actions, ordered by `priority`
- `blockers`: blockers, open questions, required inputs
- `risks`: potential risks and mitigations

### 5. artifacts & dependencies
- `files`: key files involved/produced — **absolute `path` + `description`**, do NOT copy file bodies
- `dependencies`: external dependencies (SDK, API keys, data sources, permissions) + `how_to_obtain`
- `environment`: runtime requirements (OS, runtime, versions)
- `commands`: key commands/operations (reproducible)

### 6. resume
- `how_to_resume`: the FIRST thing a successor should do, and where to continue from
- `contact`: how to reach the task owner on ambiguity (optional)
- `handoff_notes`: tacit knowledge that "only word of mouth would convey" — MUST be written down

## Two Entry Points (both MUST be supported)

### Entry A: before the task starts (initialization snapshot)
User says "start a portable task" or "make this task migratable". Only goal/constraints/background exist. Produce an **initial snapshot** with `status = initialized`; fill goal/constraints/background fully, leave the progress section empty but structurally complete.

### Entry B: during the task (incremental / checkpoint snapshot)
User says "snapshot current progress" / "package this task for migration" / "I want to switch environments". The task has substantial state. Produce an **incremental snapshot**, capturing:
- completed items and key decisions (most easily lost)
- remaining work and next steps
- file list and dependencies
- mark `updated_at` and increment the version/sequence

**Key principle: a snapshot is a freeze point, not a log.** Every snapshot MUST be a self-contained complete state. A successor reads only the latest one and needs nothing from history.

## Workflow

### Step 1 — Confirm task and scope
- Confirm via AskUserQuestion or direct ask: task goal, current phase (not started / in progress), whether migratable content already exists.
- If information is insufficient, ask first. Do NOT invent values.

### Step 2 — Collect state
- Extract from the current conversation, working directory, and existing files: goal, constraints, decisions, progress, files, dependencies.
- Read key files to verify state (do NOT write from memory).
- Get an accurate timestamp via the `date` command.

### Step 3 — Generate the bundle
- Determine `slug` and bundle directory (default `<cwd>/.task-portability/<slug>/`; use a user-specified path if given).
- Write JSON first (complete fields), then generate Markdown from the JSON (keep them identical).
- Ensure self-containment: reading the single Markdown file must be enough to resume.

### Step 4 — Self-check
Verify each:
- [ ] Is `goal` verifiable? Are `success_criteria` observable?
- [ ] Do `key_decisions` include their `reason`?
- [ ] Is `progress` specific enough that a successor can continue?
- [ ] Is `files` absolute `path` + `description`?
- [ ] Do `dependencies` include `how_to_obtain`?
- [ ] Is tacit knowledge written into `handoff_notes`?
- [ ] Are Markdown and JSON consistent?

### Step 5 — Deliver and explain
- Report the bundle location and the role of the two files.
- State that a successor only needs to read `task-snapshot.md`; use JSON for programmatic processing.
- Note: if the task is unfinished, re-snapshot at key milestones to keep the latest snapshot complete.

## Migration & Resume (successor's view)

When you are the successor receiving a bundle:
1. Read `how_to_resume` in `task-snapshot.md` first, and start from the right place.
2. Cross-check `completed` / `in_progress` / `next_steps` to locate your position.
3. Check `dependencies` and `environment` are satisfied; fill gaps first.
4. On ambiguity, read `handoff_notes` and `key_decisions`; if still unclear, use `contact`.
5. Continue from the first item in `next_steps`.

## Hard Rules

1. **Never hand-calculate timestamps** — always use the `date` command.
2. **Never write state from memory** — files, progress, and decisions must be verified before writing.
3. **Never write only Markdown or only JSON** — produce both, in sync.
4. **Never write a snapshot without `how_to_resume`** — a snapshot without a resume guide is useless.
5. **Snapshot must be self-contained** — a successor reads only the latest snapshot plus the files it points to; never require "go back to past conversation history".
6. **Use absolute paths** — relative paths break across environments, violating the portability goal.
7. **Do not copy large files** — `files` records `path` and `description` only, not file bodies (unless the user explicitly requests packaging).

## Scenario Quick Reference

| User intent | Your action |
|---|---|
| "Make this task migratable" / "start a portable task" | Initialization snapshot (Entry A) |
| "Snapshot current progress" / "checkpoint" | Incremental snapshot (Entry B) |
| "Switch environment / switch model" | Incremental snapshot + detailed resume guide |
| "Hand off to X" | Incremental snapshot + detailed `handoff_notes` and `key_decisions` |
| "Package the task to take away" | Incremental snapshot; zip/tar the bundle if requested |
| Received a bundle to resume | Follow the "Migration & Resume" flow |
