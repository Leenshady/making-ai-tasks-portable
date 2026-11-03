#!/usr/bin/env python3
"""Create a task snapshot bundle skeleton (task-snapshot.json + task-snapshot.md).

Usage:
    python3 scaffold.py --title "TITLE" --goal "GOAL" [--slug SLUG]
                        [--status initialized] [--out DIR] [--force]

The generated JSON satisfies schema.json, and the Markdown is rendered from the
same data so the two files never drift. Timestamps are generated automatically
(never hand-calculated).

Standard library only.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

STATUS_CHOICES = ["initialized", "in-progress", "checkpointed", "completed", "abandoned"]


def slugify(text):
    """Convert text to a lowercase hyphenated slug (may be empty)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return slug.strip("-")


def bullets(items, empty="—"):
    """Render a Markdown bullet list."""
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return "- %s" % empty
    return "\n".join("- %s" % value for value in values)


def numbered(items, empty="—"):
    """Render a Markdown numbered list."""
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return "1. %s" % empty
    return "\n".join("%d. %s" % (index, value) for index, value in enumerate(values, 1))


def render_md(data):
    """Render the snapshot Markdown from snapshot data."""
    identity = data["identity"]
    goal = data["goal"]
    context = data["context"]
    progress = data["progress"]
    artifacts = data["artifacts"]
    resume = data["resume"]

    decisions = [
        "Decision: %s → Reason: %s" % (item["decision"], item["reason"])
        for item in context.get("key_decisions", [])
    ]
    terminology = [
        "`%s`: %s" % (key, value) for key, value in context.get("terminology", {}).items()
    ]
    next_steps = [
        "[priority %s] %s" % (item["priority"], item["action"])
        for item in progress.get("next_steps", [])
    ]
    files = [
        "`%s` — %s" % (item["path"], item["description"])
        for item in artifacts.get("files", [])
    ]
    deps = [
        "%s: %s" % (item["name"], item["how_to_obtain"])
        for item in artifacts.get("dependencies", [])
    ]
    commands = "\n".join(artifacts.get("commands", [])).strip()

    lines = [
        "# Task Snapshot",
        "",
        "> This file is the task's self-contained state snapshot. **Any AI or person "
        "can resume the task by reading this one file** — no need to revisit past "
        "conversation history.",
        "> The structured counterpart is `task-snapshot.json`; both describe the same state.",
        "",
        "## Identity & Meta",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Task ID | `%s` |" % identity["task_id"],
        "| Title | %s |" % identity["title"],
        "| Status | %s |" % identity["status"],
        "| Created At | %s |" % identity["created_at"],
        "| Updated At | %s |" % identity["updated_at"],
        "| Schema Version | %s |" % data["schema_version"],
        "",
        "## Goal",
        "",
        "**Goal**",
        "",
        goal["goal"],
        "",
        "**Success Criteria**",
        "",
        bullets(goal.get("success_criteria", [])),
        "",
        "**Constraints**",
        "",
        bullets(goal.get("constraints", [])),
        "",
        "**Non-goals**",
        "",
        bullets(goal.get("non_goals", [])),
        "",
        "## Context",
        "",
        "**Background**",
        "",
        context["background"],
        "",
        "**Key Decisions**",
        "",
        bullets(decisions),
        "",
        "**Assumptions**",
        "",
        bullets(context.get("assumptions", [])),
        "",
        "**Terminology**",
        "",
        bullets(terminology),
        "",
        "## Progress",
        "",
        "**Completed**",
        "",
        bullets(progress.get("completed", [])),
        "",
        "**In Progress**",
        "",
        bullets(progress.get("in_progress", [])),
        "",
        "**Next Steps**",
        "",
        numbered(next_steps),
        "",
        "**Blockers**",
        "",
        bullets(progress.get("blockers", [])),
        "",
        "**Risks**",
        "",
        bullets(progress.get("risks", [])),
        "",
        "## Artifacts",
        "",
        "**Files**",
        "",
        bullets(files),
        "",
        "**Dependencies**",
        "",
        bullets(deps),
        "",
        "**Environment**",
        "",
        bullets(artifacts.get("environment", [])),
        "",
        "**Commands**",
        "",
        "```bash",
        commands,
        "```",
        "",
        "## Resume",
        "",
        "**How to Resume**",
        "",
        resume["how_to_resume"],
        "",
        "**Contact**",
        "",
        resume.get("contact", "") or "—",
        "",
        "**Handoff Notes**",
        "",
        bullets(resume.get("handoff_notes", [])),
        "",
    ]
    return "\n".join(lines)


def build_snapshot(title, goal, slug, status, background, how_to_resume):
    """Build snapshot data with auto-generated identity fields."""
    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d-%H%M")
    timestamp = now.isoformat(timespec="seconds")

    final_slug = slug or slugify(title) or "task-%s" % stamp

    return {
        "schema_version": "1.0.0",
        "identity": {
            "task_id": "task-%s" % stamp,
            "title": title,
            "slug": final_slug,
            "created_at": timestamp,
            "updated_at": timestamp,
            "status": status,
        },
        "goal": {
            "goal": goal,
            "success_criteria": [],
            "constraints": [],
            "non_goals": [],
        },
        "context": {
            "background": background,
            "key_decisions": [],
            "assumptions": [],
            "terminology": {},
        },
        "progress": {
            "completed": [],
            "in_progress": [],
            "next_steps": [],
            "blockers": [],
            "risks": [],
        },
        "artifacts": {
            "files": [],
            "dependencies": [],
            "environment": [],
            "commands": [],
        },
        "resume": {
            "how_to_resume": how_to_resume,
            "handoff_notes": [],
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create a task snapshot bundle skeleton."
    )
    parser.add_argument("--title", required=True, help="one-line task title")
    parser.add_argument("--goal", required=True, help="verifiable goal statement")
    parser.add_argument("--slug", help="filesystem-safe bundle name")
    parser.add_argument("--status", default="initialized", choices=STATUS_CHOICES)
    parser.add_argument("--background", default="TODO: why this task exists.", help="context.background")
    parser.add_argument(
        "--how-to-resume",
        default="TODO: the first thing a successor should do, and where to continue from.",
        help="resume.how_to_resume",
    )
    parser.add_argument("--out", help="bundle directory (default ./.task-portability/<slug>)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing bundle")
    args = parser.parse_args()

    data = build_snapshot(
        args.title,
        args.goal,
        args.slug,
        args.status,
        args.background,
        args.how_to_resume,
    )
    slug = data["identity"]["slug"]
    out_dir = args.out or os.path.join(".task-portability", slug)

    if os.path.isdir(out_dir) and os.listdir(out_dir) and not args.force:
        print(
            "ERROR: %s already exists and is not empty (use --force to overwrite)"
            % out_dir,
            file=sys.stderr,
        )
        return 2

    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "task-snapshot.json")
    md_path = os.path.join(out_dir, "task-snapshot.md")

    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_md(data))

    print("Created bundle: %s" % os.path.abspath(out_dir))
    print("  %s" % json_path)
    print("  %s" % md_path)
    print("Fill in the empty arrays, then run: python3 scripts/validate.py %s" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
