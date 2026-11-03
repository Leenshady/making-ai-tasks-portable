#!/usr/bin/env python3
"""Validate a task snapshot bundle against schema.json.

Usage:
    python3 validate.py <bundle-dir | task-snapshot.json> [--schema PATH]
                        [--skip-md] [--strict]

Checks:
    1. The snapshot JSON conforms to schema.json (required fields, types, enums,
       patterns, ISO 8601 date-times, nested objects and arrays).
    2. A task-snapshot.md exists alongside the JSON.
    3. identity.task_id / title / status also appear in the Markdown (sync check).

Checks with --strict (completeness, run only when the checks above pass):
    4. No empty strings anywhere.
    5. goal.success_criteria is not empty.
    6. progress.next_steps is not empty while status is unfinished.
    7. No placeholder markers (TODO, TBD, FIXME, XXX, <...>, {{...}}, "...").
    8. artifacts.files[].path is absolute.
    9. identity.updated_at is not earlier than identity.created_at.

Exit codes:
    0  valid
    1  validation errors found (or incomplete under --strict)
    2  usage or I/O error

Standard library only.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SCHEMA = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "schema.json"))


def json_type(value):
    """Return the JSON Schema type name for a Python value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def matches_type(value, expected):
    """Check a value against a JSON Schema type name."""
    actual = json_type(value)
    if expected == "number":
        return actual in ("number", "integer")
    return actual == expected


def parse_datetime(text):
    """Return a datetime for text, or None if it is not ISO 8601."""
    if not isinstance(text, str) or "T" not in text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_datetime(text):
    """Return True if text is an ISO 8601 date-time."""
    return parse_datetime(text) is not None


def is_absolute_path(text):
    """Return True if text looks like an absolute path on this or any platform."""
    return (
        os.path.isabs(text)
        or bool(re.match(r"^[A-Za-z]:[\\/]", text))
        or text.startswith("\\\\")
    )


def validate(instance, schema, path="$", errors=None):
    """Validate instance against schema, appending messages to errors."""
    if errors is None:
        errors = []
    if not isinstance(schema, dict):
        return errors

    if "const" in schema and instance != schema["const"]:
        errors.append("%s: expected const %r, got %r" % (path, schema["const"], instance))

    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r is not one of %r" % (path, instance, schema["enum"]))

    expected = schema.get("type")
    if expected:
        options = expected if isinstance(expected, list) else [expected]
        if not any(matches_type(instance, option) for option in options):
            errors.append(
                "%s: expected type %s, got %s" % (path, expected, json_type(instance))
            )
            return errors

    if isinstance(instance, str):
        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, instance):
            errors.append("%s: %r does not match pattern %s" % (path, instance, pattern))
        if schema.get("format") == "date-time" and not is_datetime(instance):
            errors.append("%s: %r is not an ISO 8601 date-time" % (path, instance))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append("%s: missing required field %r" % (path, key))
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], "%s.%s" % (path, key), errors)
            elif extra is False:
                errors.append("%s: unexpected field %r" % (path, key))
            elif isinstance(extra, dict):
                validate(value, extra, "%s.%s" % (path, key), errors)

    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, value in enumerate(instance):
                validate(value, items, "%s[%d]" % (path, index), errors)

    return errors


def resolve_paths(target):
    """Return (json_path, md_path) for a bundle directory or a JSON file."""
    if os.path.isdir(target):
        return (
            os.path.join(target, "task-snapshot.json"),
            os.path.join(target, "task-snapshot.md"),
        )
    json_path = os.path.abspath(target)
    return json_path, os.path.join(os.path.dirname(json_path), "task-snapshot.md")


def check_sync(snapshot, md_path, errors):
    """Verify key identity values also appear in the Markdown."""
    if not os.path.isfile(md_path):
        errors.append("bundle: missing task-snapshot.md")
        return
    try:
        with open(md_path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        errors.append("bundle: cannot read task-snapshot.md (%s)" % exc)
        return
    identity = snapshot.get("identity") or {}
    for field in ("task_id", "title", "status"):
        value = identity.get(field)
        if isinstance(value, str) and value and value not in text:
            errors.append(
                "sync: identity.%s %r not found in task-snapshot.md" % (field, value)
            )


def walk_strings(node, path="$"):
    """Yield (json_path, string) for every string in the snapshot."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            for item in walk_strings(value, "%s.%s" % (path, key)):
                yield item
    elif isinstance(node, list):
        for index, value in enumerate(node):
            for item in walk_strings(value, "%s[%d]" % (path, index)):
                yield item


PLACEHOLDER_RE = re.compile(
    "|".join(
        [
            r"\bTODO\b",
            r"\bTBD\b",
            r"\bFIXME\b",
            r"\bXXX\b",
            r"lorem ipsum",
            r"<[^<>]{0,40}>",
            r"\{\{[^}]{0,40}\}\}",
            r"^\s*[.\-\u2026]{2,}\s*$",
            r"待补",
            r"待填",
            r"占位",
        ]
    ),
    re.IGNORECASE,
)

UNFINISHED_STATUSES = ("initialized", "in-progress", "checkpointed")


def check_strict(snapshot, errors):
    """Detect skeletons that are schema-valid but not finished (--strict only)."""
    identity = snapshot.get("identity") or {}
    goal = snapshot.get("goal") or {}
    progress = snapshot.get("progress") or {}
    artifacts = snapshot.get("artifacts") or {}
    resume = snapshot.get("resume") or {}

    for path, text in walk_strings(snapshot):
        if not text.strip():
            errors.append(
                "strict: %s is an empty string — fill it in or omit the field" % path
            )
            continue
        match = PLACEHOLDER_RE.search(text)
        if match:
            errors.append(
                "strict: %s contains placeholder text %r" % (path, match.group(0))
            )

    if not goal.get("success_criteria"):
        errors.append(
            "strict: $.goal.success_criteria is empty — "
            "a task without success criteria cannot be verified as done"
        )

    status = identity.get("status")
    steps = progress.get("next_steps") or []
    if status in UNFINISHED_STATUSES and not steps:
        errors.append(
            "strict: $.progress.next_steps is empty while status is %r — "
            "a successor has nowhere to continue" % status
        )

    for index, entry in enumerate(artifacts.get("files") or []):
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and path.strip() and not is_absolute_path(path):
            errors.append(
                "strict: $.artifacts.files[%d].path %r is not absolute" % (index, path)
            )

    if not resume.get("how_to_resume", "").strip():
        errors.append(
            "strict: $.resume.how_to_resume is empty — the successor has no entry point"
        )

    created = parse_datetime(identity.get("created_at"))
    updated = parse_datetime(identity.get("updated_at"))
    if created and updated and updated < created:
        errors.append(
            "strict: $.identity.updated_at %r is earlier than created_at %r"
            % (identity.get("updated_at"), identity.get("created_at"))
        )


def main():
    parser = argparse.ArgumentParser(
        description="Validate a task snapshot bundle against schema.json."
    )
    parser.add_argument("target", help="bundle directory or task-snapshot.json path")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="path to schema.json")
    parser.add_argument(
        "--skip-md", action="store_true", help="skip Markdown presence and sync checks"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail on skeletons that are schema-valid but unfinished "
        "(empty strings, empty success criteria / next steps, placeholder text, "
        "relative file paths, updated_at before created_at)",
    )
    args = parser.parse_args()

    json_path, md_path = resolve_paths(args.target)

    for path, label in ((json_path, "snapshot JSON"), (args.schema, "schema")):
        if not os.path.isfile(path):
            print("ERROR: %s not found: %s" % (label, path), file=sys.stderr)
            return 2

    try:
        with open(json_path, encoding="utf-8") as handle:
            snapshot = json.load(handle)
        with open(args.schema, encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, ValueError) as exc:
        print("ERROR: cannot read input: %s" % exc, file=sys.stderr)
        return 2

    errors = validate(snapshot, schema)
    if not args.skip_md:
        check_sync(snapshot, md_path, errors)

    if errors:
        print("INVALID  %s" % json_path)
        for message in errors:
            print("  - %s" % message)
        return 1

    if args.strict:
        strict_errors = []
        check_strict(snapshot, strict_errors)
        if strict_errors:
            print("INCOMPLETE  %s" % json_path)
            print("    schema-valid, but not finished:")
            for message in strict_errors:
                print("  - %s" % message)
            return 1

    print("OK  %s" % json_path)
    print("    schema: %s" % args.schema)
    if not args.skip_md:
        print("    markdown: %s (consistent)" % md_path)
    if args.strict:
        print("    strict: no empty fields, no placeholders, complete enough to hand off")
    return 0


if __name__ == "__main__":
    sys.exit(main())
