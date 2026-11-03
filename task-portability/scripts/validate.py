#!/usr/bin/env python3
"""Validate a task snapshot bundle against schema.json.

Usage:
    python3 validate.py <bundle-dir | task-snapshot.json> [--schema PATH]
                        [--md PATH] [--skip-md] [--strict]

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
    8. artifacts.files[].path is absolute and has no doubled separators.
    9. identity.updated_at is not earlier than identity.created_at.
   10. Every JSON leaf string appears verbatim in the Markdown (deep sync).

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


def has_repeated_separators(text):
    """Return True if a path contains doubled separators (an escaping mistake)."""
    body = text[2:] if text.startswith("\\\\") else text
    body = re.sub(r"^[A-Za-z]:", "", body)
    return bool(re.search(r"[/\\]{2,}", body))


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
        errors.append(
            "bundle: missing %s" % os.path.basename(md_path)
        )
        return
    try:
        with open(md_path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        errors.append("bundle: cannot read %s (%s)" % (os.path.basename(md_path), exc))
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
            r"\{\{[^}]{0,40}\}\}",
            r"^\s*[.\-\u2026]{2,}\s*$",
            r"待补",
            r"待填",
            r"占位",
        ]
    ),
    re.IGNORECASE,
)

# Angle brackets are case-sensitive on purpose: a whole-string token like
# "<unverified>" or an all-caps token like "<YOUR_NAME>" is a placeholder, while
# "<bundle>" inside a real command is not. Matching this case-insensitively would
# flag every documented command line.
ANGLE_PLACEHOLDER_RE = re.compile(r"^\s*<[^<>]{1,40}>\s*$|<[A-Z][A-Z_]{1,}>")


def find_placeholder(text):
    """Return the placeholder marker found in text, or None."""
    match = PLACEHOLDER_RE.search(text) or ANGLE_PLACEHOLDER_RE.search(text)
    return match.group(0) if match else None

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
        marker = find_placeholder(text)
        if marker:
            errors.append(
                "strict: %s contains placeholder text %r" % (path, marker)
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
        if isinstance(path, str) and path.strip():
            if not is_absolute_path(path):
                errors.append(
                    "strict: $.artifacts.files[%d].path %r is not absolute"
                    % (index, path)
                )
            elif has_repeated_separators(path):
                errors.append(
                    "strict: $.artifacts.files[%d].path %r has repeated separators "
                    "— a successor cannot open it; fix the escaping" % (index, path)
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


def check_deep_sync(snapshot, md_path, errors, limit=10):
    """Verify every leaf string in the JSON appears verbatim in the Markdown.

    The identity-only check in check_sync() cannot see content drift: edit the
    JSON and leave the Markdown stale, and a successor reads the stale file.
    """
    if not os.path.isfile(md_path):
        return
    try:
        with open(md_path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return
    missing = []
    for path, value in walk_strings(snapshot):
        if not value.strip() or path.startswith("$.schema_version"):
            continue
        if value not in text:
            missing.append((path, value))
    md_name = os.path.basename(md_path)
    for path, value in missing[:limit]:
        errors.append(
            "sync: %s %r is in the JSON but not in %s — re-render the Markdown "
            "from the JSON" % (path, value, md_name)
        )
    if len(missing) > limit:
        errors.append(
            "sync: %d more values are missing from %s" % (len(missing) - limit, md_name)
        )


def main():
    parser = argparse.ArgumentParser(
        description="Validate a task snapshot bundle against schema.json."
    )
    parser.add_argument("target", help="bundle directory or task-snapshot.json path")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="path to schema.json")
    parser.add_argument(
        "--md",
        help="explicit Markdown snapshot path (default: task-snapshot.md next to "
        "the JSON; use this to validate a differently named pair such as the "
        "bundled example)",
    )
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
    if args.md:
        md_path = os.path.abspath(args.md)

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
        if not args.skip_md:
            check_deep_sync(snapshot, md_path, strict_errors)
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
