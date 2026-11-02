# Glossary

This file defines key terms used in this skill, so cross-model successors share consistent semantics.

| Term | Definition |
|---|---|
| Task Snapshot | Self-contained data (Markdown + JSON) that freezes a task's state. |
| Snapshot Bundle | The complete directory produced by one snapshot (md + json + artifacts). |
| Self-contained | A successor can resume by reading only the latest snapshot, without revisiting history. |
| Context | Goals, constraints, background, and key decisions. |
| Progress | Completed, in-progress, next steps, blockers, and risks. |
| Artifacts | Files involved/produced, dependencies, and environment. |
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

## Status Enum

| Value | Meaning |
|---|---|
| `initialized` | Before the task starts; only goal / constraints / background exist. |
| `in-progress` | The task is being executed. |
| `checkpointed` | A checkpoint snapshot saved during the task. |
| `completed` | The task has finished. |
| `abandoned` | The task is no longer continued. |
