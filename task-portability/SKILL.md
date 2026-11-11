---
name: task-portability
description: "Decouple AI tasks from any specific workbench, model, or platform by snapshotting a task's full state into a portable, self-contained bundle (Markdown + JSON). Lets any AI or human resume the task in any environment with minimal migration cost. Use when the user wants to make an AI task portable, migrate a task between environments, hand off a task to another model/tool, checkpoint a task before switching context, or freeze task state (goal, progress, decisions, TODOs, files, dependencies). Also compresses a session log or long AI conversation into conclusions - dropping narration, tool output and duplicate findings - before it travels. Works both before a task starts (initialization) and during a task (incremental checkpoint)."
description_zh: "将 AI 任务从具体工作台/模型/平台中解耦，把任务完整状态固化成可移植的自包含快照（Markdown + JSON），让任意 AI 或人可在任意环境以最小迁移成本接续任务；迁移前先压缩 AI 日志，去掉过程性内容、保留结论并去重。"
description_en: "Decouple AI tasks from workbench/model/platform by snapshotting task state into portable bundles, compressing the session log into conclusions first."
version: 1.4.0
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

### What does NOT belong in a snapshot

A snapshot records **task facts**, not **tool facts**. Keep the line hard:

| Kind | Example | Rebuildable elsewhere? | In the snapshot? |
|---|---|---|---|
| Workbench workspace | an app's "space" / "project" id, a cloud-doc folder | No — it dies with the tool | ❌ Never |
| Task workspace | project root, repo + branch + commit | Yes — clone and check out | ✅ Required once `files` exist |
| Runtime | OS, runtime version | N/A — install it | ✅ `environment` |

Recording a workbench identity makes the snapshot *depend* on that workbench, which is the exact failure this skill exists to remove. Adapter knowledge — "how to install or trigger this skill in tool X" — belongs in `INSTALL.md`, never in the snapshot format. **One neutral format for all tools beats N optimized variants**, because N variants must each be kept in sync and each one re-couples the data to a vendor.

## Output: Task Snapshot Bundle

> Before generating a snapshot, read `@references/example-snapshot.md` for a complete example of a valid snapshot, with `@references/example-snapshot.json` as its structured counterpart. For term definitions, read `@references/glossary.md`. Field names MUST match `schema.json` exactly. Both example files are validated by `scripts/validate.py`, so they never drift from this contract.

Each snapshot produces two complementary files in one directory:

```
<task-slug>/
├── task-snapshot.md    # Human-readable: any AI or person can resume by reading this one file
└── task-snapshot.json  # Programmable: validatable, convertible, diffable
```

Never copy artifact bodies into the bundle. The project root, VCS anchor (remote + branch + resolved commit), key files, dependencies, and deliberate exclusions all live in the snapshot's `artifacts` section as paths plus descriptions.

### Why two formats

- **Markdown** — zero-barrier. Any model, editor, or human can read one file and understand the full task. This is the foundation of model-agnosticism.
- **JSON** — structured. Can be validated, converted (e.g. to an A2A task card), or diffed for incremental tracking. This is the foundation of platform-agnosticism and portability.

Both describe the **same state**. Markdown is the presentation layer of JSON; JSON is the structural layer of Markdown. Change one, sync the other.

## Compressing the AI Log

The raw material of a migration is a conversation: turns, tool calls, retries, terminal output. Most of it is process. Carrying the process into the snapshot defeats the purpose — the successor pays for the narration and still has to dig the conclusion out of it, in the one file that was supposed to save them the trip.

Compress **before** writing a field. Three passes, in this order:

1. **Drop process** — intent ("let me read ct.js first"), step numbering, timestamps, speaker labels, tool-call chatter, retries that ended exactly where they started, restated instructions, pleasantries.
2. **Keep conclusions** — decisions and their reasons, findings and their evidence, constraints discovered the hard way, failures that changed the plan, verified facts (file, line, value, error text, name).
3. **Merge duplicates** — the same conclusion reached twice, or restated after a retry, becomes one entry: keep the wording that carries more precision, and fold in any reason the other one carried.

| Raw log | Verdict | Why |
|---|---|---|
| "Let me read `ct.js` first." | Drop | Intent, not state. `in_progress` at most |
| "Reading `ct.js`…" + 200 lines of file dump | Drop | Activity plus tool output; the successor can open the file |
| "`ct.js` intercepts at line 218 via `chrome.downloads.download`; `bg.js` never sees the URL." | Keep → `findings` | A verified fact with evidence |
| "Tried filtering in `bg.js`; MV3 `declarativeNetRequest` cannot see response headers, so the filter cannot live there." | Keep → `findings` | A failed attempt that changed the plan |
| "Ran the tests again, same result." | Drop | No new information; it neither confirms nor rules out anything |
| "Now I'll add the guard." | Drop | Intent |
| "The tests pass, so the change is safe." | Verify first | A claim, not a fact — record it only if you actually ran them |

Rules of thumb:

1. **One entry, one conclusion**, with the evidence that makes it checkable (file + line, value, error text, command).
2. **If a sentence carries no noun-level fact** — no file, name, number, value, or error string — it is narration. Drop it.
3. **Keep the failure that taught you something; drop the retry that did not.**
4. **Never paste tool output, diffs, or stack traces.** Quote the single line that decides the question; the successor can reproduce the rest.
5. **Timestamps, step numbers, and speaker labels are not content.** The only time a snapshot records is `identity.updated_at`.
6. **Deduplicate by meaning, not wording.** If two entries would lead the successor to the same action, keep one.
7. **Write for action, not for memory.** The successor needs to continue the task, not to re-live the session.
8. **Compress each field for its reader.** `findings` = outcome + evidence; `completed` = what is now true; `key_decisions` = choice + reason; `handoff_notes` = what a colleague would say out loud. `context.background` gets the same filter: it explains the task, it is not a transcript of how the task was explained.

With a long log, run `scripts/distill.py <log-file>` first: it quotes candidate conclusions verbatim with their line numbers and prints a drop tally, so you review a short list instead of re-reading a long file. It never summarizes — you still choose what belongs and write the final wording.

**Budget.** An entry over ~600 characters is almost always pasted output (`--strict` rejects it). If the whole `progress` section is longer than `goal` + `context` combined, you are still carrying a log.

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

Every entry here is a conclusion, not a log line: no narration, no pasted output, no second copy of something already stated (see *Compressing the AI Log*).

- `completed`: done items (specific, verifiable)
- `in_progress`: current work and how far it has gone (as granular as possible)
- `findings`: what the work so far actually **revealed** — state the outcome, not the activity. A diff result, a failed attempt, a discovered constraint, a partial result that changes the plan.
  - WRONG: "diffing the first 60 pages" (that is an activity, already covered by `in_progress`)
  - RIGHT: "diff of the first 60 pages shows no text changes; 2 pages reference images over 2 MB, which are out of scope"
  - Why this field exists: without it a successor cannot tell whether the current work passed, failed, or is still unknown, and will redo it.
- `next_steps`: concrete next actions, ordered by `priority`
- `blockers`: blockers, open questions, required inputs
- `risks`: potential risks and mitigations

### 5. artifacts & dependencies
- `workspace`: where the task physically lives. Platform-neutral by design — **record the task's project root and VCS anchor, never a workbench-specific "space" or "project" id**.
  - `root`: absolute path of the project root, in the platform's native form (POSIX or Windows drive letter). This anchors every `files[].path`; without it a successor sees `/workspace/app/src/x.js` and has to guess where `/workspace/app` ends and the task begins.
  - `vcs`: `type` + `remote` + `branch` + `commit` + `toplevel`. `remote` + `branch` + `commit` is the single most portable description of a code workspace, because any environment can rebuild it with a clone. Record the **resolved commit hash**, never a moving ref (`HEAD`, `main`, `latest`) — those point at different content later.
  - `vcs.toplevel`: the repository top level, i.e. what a clone produces. It differs from `root` when the task works inside a subdirectory (a monorepo package, for example); without it a successor clones the repo but cannot tell where to `cd`.
  - `vcs.dirty` + `vcs.uncommitted`: whether the tree was dirty, and what exactly was uncommitted. When `dirty` is `true`, the commit alone does **not** reproduce the code state, and **a fresh clone will never contain that work** — so `uncommitted` is mandatory. If you cannot describe it in one line, commit or stash first, then snapshot.
  - `excluded`: paths deliberately left out, each with `path` + `reason`. Without it, a short `files` list reads as "the task is small" instead of "I must rebuild these".
- `files`: key files involved/produced — **absolute `path` + `description`**, do NOT copy file bodies
- `dependencies`: external dependencies (SDK, API keys, data sources, permissions) + `how_to_obtain`
- `environment`: runtime requirements (OS, runtime, versions)
- `commands`: key commands/operations (reproducible)

### 6. resume
- `how_to_resume`: the FIRST thing a successor should do, and where to continue from
- `contact`: how to reach the task owner on ambiguity (optional)
- `handoff_notes`: tacit knowledge that "only word of mouth would convey" — MUST be written down

## Snapshot Format Changelog

Two version numbers move independently. `schema_version` (and the `const` in `schema.json`) is the **snapshot format**: bump it only when the data contract changes, because every existing bundle must then be migrated. `version` in the frontmatter is the **skill release**: bump it for methodology, rules, and validator changes. This skill is `1.4.0` and still writes format `1.3.0`.

| Version | Change |
|---|---|
| `1.3.0` | **Closed the object contract.** Every object in `schema.json` now sets `additionalProperties: false`, so a field name the schema does not define is rejected instead of silently kept — this is what makes "no synonyms" enforceable rather than advisory. A bundle written at `1.2.0` that carries custom keys must drop them (or move term-like data under `context.terminology`) and bump `schema_version`, otherwise `validate.py` rejects it. |
| `1.2.0` | Added `artifacts.workspace` — `root`, `vcs` (`type`, `remote`, `branch`, `commit`, `dirty`), `excluded`. A bundle written at `1.1.0` or earlier must add the field (or be regenerated with `scaffold.py`) and bump `schema_version`, otherwise `validate.py` rejects it. |
| `1.1.0` | Added `progress.findings`. A bundle written at `1.0.0` must add the field and bump `schema_version`, otherwise `validate.py` rejects it. |
| `1.0.0` | Initial format. |

## Two Entry Points (both MUST be supported)

### Entry A: before the task starts (initialization snapshot)
User says "start a portable task" or "make this task migratable". Only goal/constraints/background exist. Produce an **initial snapshot** with `status = initialized`; fill goal/constraints/background fully, leave the progress section empty but structurally complete.

### Entry B: during the task (incremental / checkpoint snapshot)
User says "snapshot current progress" / "package this task for migration" / "I want to switch environments". The task has substantial state. Produce an **incremental snapshot**, capturing:
- completed items and key decisions (most easily lost)
- findings: what the work has revealed so far — results, failures, surprises (without these the successor repeats your work)
- remaining work and next steps
- file list and dependencies
- mark `updated_at` and increment the version/sequence

**Key principle: a snapshot is a freeze point, not a log.** Every snapshot MUST be a self-contained complete state, containing conclusions rather than the process that produced them (see *Compressing the AI Log*). A successor reads only the latest one and needs nothing from history.

## Workflow

### Step 1 — Confirm task and scope
- Confirm via AskUserQuestion or direct ask: task goal, current phase (not started / in progress), whether migratable content already exists.
- If information is insufficient, ask first. Do NOT invent values.

### Step 2 — Collect state
- Extract from the current conversation, working directory, and existing files: goal, constraints, decisions, progress, files, dependencies.
- If the task arrives with a session log or transcript, distill it first (see *Compressing the AI Log*): drop the process, keep the conclusions, merge duplicates. With a large log, `scripts/distill.py <log>` returns the candidate list with line numbers.
- Record the workspace from the environment, not from memory: the project root, and — when it is a repository — the resolved commit, branch, remote, and whether the tree is dirty.
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
- [ ] Does `findings` record outcomes (diff results, failed attempts, surprises), not activities?
- [ ] Is every `progress` entry a conclusion rather than narration — no "let me…", no timestamps, no tool output?
- [ ] Are duplicated conclusions merged into one entry, with the more precise wording kept?
- [ ] Is any entry over ~600 characters or does `progress` outweigh `goal` + `context` (still a log)?
- [ ] Is `files` absolute `path` + `description`?
- [ ] Is `workspace.root` recorded as an absolute path, and is every `files[].path` inside it?
- [ ] If a repository is involved, are `commit` (a hash, not `HEAD` or a branch) and `dirty` recorded?
- [ ] Are deliberately omitted paths listed in `workspace.excluded` with a reason?
- [ ] Do `dependencies` include `how_to_obtain`?
- [ ] Is tacit knowledge written into `handoff_notes`?
- [ ] Are Markdown and JSON consistent?

### Step 5 — Deliver and explain
- Report the bundle location and the role of the two files.
- State that a successor only needs to read `task-snapshot.md`; use JSON for programmatic processing.
- Note: if the task is unfinished, re-snapshot at key milestones to keep the latest snapshot complete.

## Helper Scripts (optional)

`scripts/` contains optional accelerators written in **Python 3 standard library only** — no `pip install`, works on Windows/macOS/Linux. They enforce the rules above mechanically. **The snapshot itself never depends on them**: without Python, a successor still resumes from `task-snapshot.md` alone.

| Script | Command | Purpose |
|---|---|---|
| `validate.py` | `python3 scripts/validate.py <bundle-dir> [--strict]` | Validate JSON against `schema.json`, check Markdown sync; `--strict` also rejects unfinished skeletons and log residue |
| `distill.py` | `python3 scripts/distill.py <log-file> [--max N] [--out FILE]` | Filter a session log into candidate conclusions with line numbers, plus a drop tally — a filter, never a summarizer |
| `scaffold.py` | `python3 scripts/scaffold.py --title "T" --goal "G" [--workspace-root DIR]` | Create a bundle skeleton with auto timestamps, `task_id`, and the detected workspace root + VCS anchor |
| `bundle.py` | `python3 scripts/bundle.py <bundle-dir> [-o out.zip]` | Package a bundle for migration (top-level dir preserved) |
| `resume.py` | `python3 scripts/resume.py <bundle-dir>` | Print a compact resume briefing for a successor |

Rules for using them:

1. **Run `validate.py --strict` before declaring a snapshot done.** Exit code `0` = valid and complete, `1` = errors or incomplete (each printed with its JSON path), `2` = usage or I/O error. Do not report success while it exits non-zero.
2. **Prefer `scaffold.py` over hand-writing a bundle.** It generates `task_id` and ISO 8601 timestamps correctly, and renders Markdown from the same data so the two files cannot drift.
3. **`validate.py` checks what the hard rules require:** missing required fields, wrong types, invalid `status` enums, malformed `slug` patterns, non-ISO `date-time` values, keys `schema.json` does not define (every object is closed), and identity fields absent from the Markdown.
4. **`--strict` rejects a schema-valid skeleton that is not finished.** It fails on empty strings, an empty `goal.success_criteria`, an empty `progress.next_steps` while `status` is `initialized` / `in-progress` / `checkpointed`, placeholder markers (`TODO`, `TBD`, `FIXME`, `XXX`, a whole-string `<...>`, an all-caps `<YOUR_NAME>`, `{{...}}`, `...`), a relative `artifacts.files[].path` or one with doubled separators, a `files[].path` that misses `workspace.root` by a character or two (a mistyped root prefix, as opposed to a genuinely external file), a `files` list with no `workspace.root`, a relative `workspace.root` or one with doubled separators, a `vcs.commit` that is a moving ref, a `dirty` tree with no `uncommitted` description, `updated_at` earlier than `created_at`, any JSON string that is absent from `task-snapshot.md`, and log residue: an entry repeated or restated elsewhere (same content words, any order), an entry that narrates intent or describes an activity instead of its result, an entry that starts with a timestamp / speaker label / step number, and an entry over 600 characters (pasted output). Use it when finalizing a snapshot; a mid-task checkpoint may legitimately run without it.
5. **If Python 3 is unavailable, skip the scripts — do not block the task.** Perform Step 4's self-check manually instead.
6. **Keep the bundled example valid.** After changing `schema.json` or the example, run `python3 scripts/validate.py references/example-snapshot.json --md references/example-snapshot.md --strict`. The example is what successors copy, so a stale example silently teaches the wrong contract.
7. **`distill.py` filters, it does not summarize.** It copies candidate lines verbatim with their line numbers and never invents a conclusion. Choosing what belongs and writing the final wording stay yours; the worksheet is a working note, never a snapshot field.

## Migration & Resume (successor's view)

When you are the successor receiving a bundle:
1. Read `how_to_resume` in `task-snapshot.md` first, and start from the right place.
2. Locate the code through `workspace.root`. If `vcs.dirty` is `true`, run `git status` before trusting the checkout — the commit alone does not describe a dirty tree.
3. Cross-check `completed` / `in_progress` / `next_steps` to locate your position.
4. Check `dependencies` and `environment` are satisfied; fill gaps first.
5. On ambiguity, read `handoff_notes` and `key_decisions`; if still unclear, use `contact`.
6. Continue from the first item in `next_steps`.

## Hard Rules

1. **Never hand-calculate timestamps** — always use the `date` command.
2. **Never write state from memory** — files, progress, and decisions must be verified before writing.
3. **Never write only Markdown or only JSON** — produce both, in sync.
4. **Never write a snapshot without `how_to_resume`** — a snapshot without a resume guide is useless.
5. **Snapshot must be self-contained** — a successor reads only the latest snapshot plus the files it points to; never require "go back to past conversation history".
6. **Use absolute paths** — relative paths break across environments, violating the portability goal.
7. **Do not copy large files** — `files` records `path` and `description` only, not file bodies (unless the user explicitly requests packaging).
8. **Record the task's workspace, never the tool's.** `workspace.root` + VCS anchor only; a workbench space/project id must not appear in a snapshot. And never hand-write the commit — read the resolved hash (`git rev-parse HEAD`); `HEAD` or a branch name is a moving ref that reconstructs nothing.
9. **A dirty tree must say what is uncommitted.** `vcs.dirty: true` with no `vcs.uncommitted` silently loses that work on a fresh clone; commit it, stash it, or describe it.
10. **Never invent a field name.** The contract is closed: an unknown key fails validation, because a synonym is invisible to every downstream reader. When a needed fact has no dedicated field, put it in an existing free-text field (`handoff_notes`, `assumptions`) instead of adding a key.
11. **Compress the log; never paste it.** A snapshot is a conclusion set, not a transcript. Narration, timestamps, tool output, and second copies of the same conclusion cost the successor exactly the context the snapshot exists to save — and `--strict` fails on them.

## Scenario Quick Reference

| User intent | Your action |
|---|---|
| "Make this task migratable" / "start a portable task" | Initialization snapshot (Entry A) |
| "Snapshot current progress" / "checkpoint" | Incremental snapshot (Entry B) |
| "Switch environment / switch model" | Incremental snapshot + detailed resume guide |
| "Hand off to X" | Incremental snapshot + detailed `handoff_notes` and `key_decisions` |
| "Package the task to take away" | Incremental snapshot; zip/tar the bundle if requested |
| Received a bundle to resume | Follow the "Migration & Resume" flow |
