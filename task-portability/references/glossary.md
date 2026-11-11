# Glossary

This file defines key terms used in this skill, so cross-model successors share consistent semantics.

| Term | Definition |
|---|---|
| Task Snapshot | Self-contained data (Markdown + JSON) that freezes a task's state. |
| Snapshot Bundle | The directory produced by one snapshot (`task-snapshot.md` + `task-snapshot.json`). Artifact locations are recorded inside the snapshot, not copied into the bundle. |
| Self-contained | A successor can resume by reading only the latest snapshot, without revisiting history. |
| Context | Goals, constraints, background, and key decisions. |
| Progress | Completed, findings, in-progress, next steps, blockers, and risks. |
| Artifacts | The workspace, files involved/produced, dependencies, environment, and commands. |
| Workspace | Where the task physically lives: the project root, the VCS anchor, and anything deliberately left out. |
| Workspace Root | Absolute path of the project the task operates in; anchors every `files[].path` so a successor never has to guess which prefix is the project. |
| VCS Anchor | `remote` + `branch` + `commit` — the most portable description of a code workspace, because any environment can rebuild it from those values alone. |
| Moving Ref | A ref such as `HEAD` or a branch name. It looks like a commit but resolves to different content later, so it cannot reconstruct the code the task ran on. |
| Excluded | Paths deliberately left out of the snapshot, each with a reason and how to regenerate. Marks the omission as intentional, so a short file list is not misread as "the task is small". |
| Findings | What the work has revealed so far, stated as an outcome (a diff result, a failure, a surprise) — never as an activity. |
| Log Compression | Turning a session log into the facts a successor needs: drop process, keep conclusions, merge duplicates. The snapshot is the distillate, never the log. |
| Process Residue | Log content that carries no state: intent narration, step numbers, timestamps, speaker labels, pasted tool output. It costs context and gives the successor nothing to act on. |
| Duplicate Conclusion | The same conclusion recorded twice, usually after a retry. One entry is enough — keep the more precise wording and fold in any reason the other carried. |
| Key Decisions | Decisions already made, each with its reason (the most easily lost asset). |
| Tacit Knowledge | Things "only known by word of mouth", which must go into the handoff notes. |
| Handoff Notes | Notes recording tacit knowledge so a successor can understand. |
| Resume Guide | Instructions telling a successor how to continue (`how_to_resume`). |
| Success Criteria | Observable, testable criteria for "done". |
| Constraints | Hard limits (tech stack, prohibitions, compliance, scope). |
| Non-goals | Explicitly out of scope, to prevent the successor from drifting. |
| Freeze | Turning runtime state into static data. |
| Resume / Take over | A new environment or model continues the task from the snapshot. |
| Dual-format sync | Markdown and JSON describe the same state; change one and sync the other. |
| Closed Contract | Every object in `schema.json` rejects keys it does not define. A synonym feels harmless but is invisible to every downstream reader, so the format treats an unknown field as an error rather than extra metadata. |

## Status Enum

| Value | Meaning |
|---|---|
| `initialized` | Before the task starts; only goal / constraints / background exist. |
| `in-progress` | The task is being executed. |
| `checkpointed` | A checkpoint snapshot saved during the task. |
| `completed` | The task has finished. |
| `abandoned` | The task is no longer continued. |
