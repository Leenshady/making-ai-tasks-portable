#!/usr/bin/env python3
"""Validate a task snapshot bundle against schema.json.

Usage:
    python3 validate.py <bundle-dir | task-snapshot.json> [--schema PATH] [--skip-md]

Checks:
    1. The snapshot JSON conforms to schema.json (required fields, types, enums,
       patterns, ISO 8601 date-times, nested objects and arrays).
    2. A task-snapshot.md exists alongside the JSON.
    3. identity.task_id / title / status also appear in the Markdown (sync check).

Exit codes:
    0  valid
    1  validation errors found
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


def is_datetime(text):
    """Return True if text is an ISO 8601 date-time."""
    if "T" not in text:
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


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


def main():
    parser = argparse.ArgumentParser(
        description="Validate a task snapshot bundle against schema.json."
    )
    parser.add_argument("target", help="bundle directory or task-snapshot.json path")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="path to schema.json")
    parser.add_argument(
        "--skip-md", action="store_true", help="skip Markdown presence and sync checks"
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

    print("OK  %s" % json_path)
    print("    schema: %s" % args.schema)
    if not args.skip_md:
        print("    markdown: %s (consistent)" % md_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
