# task-portability

> This is an **AI Skill** that decouples AI tasks from specific workbenches, models, and platforms, making tasks portable, migratable, and resumable.

Decouple AI tasks from any specific workbench, model, or platform by snapshotting a task's full state into a **self-contained, portable bundle**, so any AI or human can resume the task seamlessly by reading a single file — with minimal migration cost.

## What Problem It Solves

AI tasks typically "live" inside a particular conversation, tool, or model. Switch environments, models, or platforms, and the task's context, progress, and decisions are lost — making migration extremely costly.

This skill freezes a task's true assets — **context, progress, and artifacts** — into model-agnostic, platform-agnostic data, so tasks can be "carried over and picked up" anywhere.

## Core Output

Each snapshot produces a **task snapshot bundle**:

```
<task-slug>/
├── task-snapshot.md    # Human-readable → any AI or person can resume by reading this one file
└── task-snapshot.json  # Programmable → validatable, convertible, and diffable
```

- **Markdown** ensures "any model can read it" (the foundation of model-agnosticism)
- **JSON** ensures "validatable and convertible to other formats" (the foundation of platform-agnosticism and portability)
- **Artifacts record locations, not bodies** — project root, VCS anchor (remote + branch + resolved commit), key files, and dependencies all live in the snapshot's `artifacts` section
- **Compressed by construction** — the bundle carries conclusions, not the session that produced them: narration, timestamps, tool output, and repeated findings are filtered out before a field is written

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
6. **Workspace anchored to the repo** — record the project root plus `remote` + `branch` + the resolved commit hash: any environment can rebuild that with a clone, while a workbench's space / project id dies with the tool.
7. **One field name, no synonyms** — `schema.json` is a closed contract: an extra or misspelled key fails validation, because a synonym that feels natural to a human is silent data loss for every downstream reader.
8. **Conclusions, not a transcript** — the log is input, the snapshot is the distillate. Process narration, timestamps, tool output, and second copies of the same conclusion are removed, because a successor needs what was learned, not how the session went.

## File Structure

```
task-portability/
├── SKILL.md               # Skill body (methodology + workflow)
├── README.md              # This document
├── schema.json            # Validation schema for the snapshot JSON
├── _icon.png              # Skill icon (512×512)
├── scripts/               # Optional helpers (Python 3 stdlib only)
│   ├── validate.py        #   Validate a bundle against schema.json
│   ├── distill.py         #   Filter a session log into candidate conclusions
│   ├── scaffold.py        #   Create a bundle skeleton (also renders its Markdown)
│   ├── bundle.py          #   Package a bundle into a zip
│   └── resume.py          #   Print a resume briefing
└── references/
    ├── example-snapshot.md   # Example snapshot (what the output looks like)
    ├── example-snapshot.json # Its structured counterpart, kept in sync
    └── glossary.md           # Term glossary (cross-model semantics)
```

## Helper Scripts (optional)

Python 3 standard library only — no `pip install`. The snapshot itself never depends on them; they just enforce the rules mechanically.

| Command | Purpose |
|---|---|
| `python3 scripts/validate.py <bundle-dir> [--strict]` | Validate JSON against `schema.json` (a closed contract: unknown fields are rejected) + Markdown sync check; `--strict` also fails on unfinished skeletons (empty fields, placeholders, relative paths, a path that misspells `workspace.root`) and on log residue (duplicated, narrated, or transcript-marked entries) |
| `python3 scripts/validate.py references/example-snapshot.json --md references/example-snapshot.md --strict` | Self-check the bundled example; run it after touching `schema.json` or the example |
| `python3 scripts/distill.py <log-file> [--max N]` | Filter a session log into candidate conclusions (verbatim, with line numbers) and a drop tally; it never summarizes, so you still choose and re-word |
| `python3 scripts/scaffold.py --title "T" --goal "G"` | Create a bundle skeleton with auto timestamps |
| `python3 scripts/bundle.py <bundle-dir> -o out.zip` | Package a bundle for migration |
| `python3 scripts/resume.py <bundle-dir>` | Print a compact resume briefing |

