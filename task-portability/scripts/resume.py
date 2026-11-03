#!/usr/bin/env python3
"""Print a compact resume briefing from a snapshot bundle.

Usage:
    python3 resume.py <bundle-dir | task-snapshot.json>

Use this as the first step when taking over someone else's task: it surfaces the
goal, done criteria, blockers, next steps, and the resume guide in one screen.

Standard library only.
"""

import argparse
import json
import os
import sys


def load_snapshot(target):
    """Load snapshot data from a bundle directory or a JSON file."""
    path = target
    if os.path.isdir(target):
        path = os.path.join(target, "task-snapshot.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(
        description="Print a compact resume briefing from a snapshot bundle."
    )
    parser.add_argument("target", help="bundle directory or task-snapshot.json path")
    args = parser.parse_args()

    try:
        data = load_snapshot(args.target)
    except (OSError, ValueError) as exc:
        print("ERROR: cannot read snapshot: %s" % exc, file=sys.stderr)
        return 2

    identity = data.get("identity") or {}
    goal = data.get("goal") or {}
    context = data.get("context") or {}
    progress = data.get("progress") or {}
    artifacts = data.get("artifacts") or {}
    resume = data.get("resume") or {}

    rule = "=" * 62
    print(rule)
    print("RESUME BRIEFING — %s" % (identity.get("title") or "(untitled)"))
    print(rule)
    print("Task    : %s" % (identity.get("task_id") or "-"))
    print("Status  : %s" % (identity.get("status") or "-"))
    print("Updated : %s" % (identity.get("updated_at") or "-"))

    workspace = artifacts.get("workspace") or {}
    if workspace:
        print("\nWORKSPACE")
        if workspace.get("root"):
            print("  root    : %s" % workspace["root"])
        vcs = workspace.get("vcs") or {}
        if vcs:
            bits = [vcs.get("type") or "?"]
            if vcs.get("branch"):
                bits.append("branch %s" % vcs["branch"])
            if vcs.get("commit"):
                bits.append("commit %s" % vcs["commit"])
            print("  vcs     : %s" % ", ".join(bits))
            if vcs.get("remote"):
                print("  remote  : %s" % vcs["remote"])
            if vcs.get("toplevel") and vcs["toplevel"] != workspace.get("root"):
                print("  repo    : %s  (clone target; the task lives in a subdirectory)" % vcs["toplevel"])
            if vcs.get("dirty"):
                print("  WARNING : the working tree had uncommitted changes at snapshot time")
                if vcs.get("uncommitted"):
                    print("  uncommitted : %s" % vcs["uncommitted"])
                    print("            -> not in any commit; a fresh clone will NOT contain it")
                else:
                    print("            -> run `git status` before trusting this checkout")
        for item in workspace.get("excluded") or []:
            print("  omitted : %s (%s)" % (item.get("path", ""), item.get("reason", "")))

    print("\nGOAL")
    print("  %s" % (goal.get("goal") or "-"))

    criteria = goal.get("success_criteria") or []
    if criteria:
        print("\nDONE WHEN")
        for item in criteria:
            print("  [ ] %s" % item)

    completed = progress.get("completed") or []
    if completed:
        print("\nCOMPLETED")
        for item in completed:
            print("  [x] %s" % item)

    in_progress = progress.get("in_progress") or []
    if in_progress:
        print("\nIN PROGRESS")
        for item in in_progress:
            print("  [~] %s" % item)

    findings = progress.get("findings") or []
    if findings:
        print("\nFINDINGS")
        for item in findings:
            print("  > %s" % item)

    blockers = progress.get("blockers") or []
    if blockers:
        print("\nBLOCKERS")
        for item in blockers:
            print("  ! %s" % item)

    steps = progress.get("next_steps") or []
    if steps:
        print("\nNEXT STEPS")
        for item in steps:
            print("  %s. %s" % (item.get("priority", "-"), item.get("action", "")))

    print("\nHOW TO RESUME")
    print("  %s" % (resume.get("how_to_resume") or "-"))

    decisions = context.get("key_decisions") or []
    if decisions:
        print("\nKEY DECISIONS")
        for item in decisions:
            print("  * %s — %s" % (item.get("decision", ""), item.get("reason", "")))

    notes = resume.get("handoff_notes") or []
    if notes:
        print("\nHANDOFF NOTES")
        for item in notes:
            print("  * %s" % item)

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
