#!/usr/bin/env python3
"""Validate a task snapshot bundle against schema.json.

Usage:
    python3 validate.py <bundle-dir | task-snapshot.json> [--schema PATH]
                        [--md PATH] [--skip-md] [--strict]

Checks:
    1. The snapshot JSON conforms to schema.json (required fields, types, enums,
       patterns, ISO 8601 date-times, nested objects and arrays). Every object in
       the schema is closed, so a key the schema does not define — a renamed or
       synonym field — is rejected here rather than silently kept.
    2. A task-snapshot.md exists alongside the JSON.
    3. identity.task_id / title / status also appear in the Markdown (sync check).

Checks with --strict (completeness, run only when the checks above pass):
    4. No empty strings anywhere.
    5. goal.success_criteria is not empty.
    6. progress.next_steps is not empty while status is unfinished.
    7. No placeholder markers (TODO, TBD, FIXME, XXX, <...>, {{...}}, "...").
    8. artifacts.files[].path is absolute and has no doubled separators.
    9. artifacts.workspace.root is absolute and present whenever files or a VCS
       anchor exist; vcs.commit is a resolved revision, not a moving ref; a dirty
       tree names what is uncommitted; a files[].path that misses the root by a
       character or two is reported as a mistyped prefix rather than an external
       file.
   10. identity.updated_at is not earlier than identity.created_at.
   11. Every JSON leaf string appears verbatim in the Markdown (deep sync).
   12. The snapshot is a set of conclusions, not a transcript: no duplicated
       entry, no intent narration or activity description, no timestamp /
       speaker / step markers, and no entry long enough to be pasted output.

Exit codes:
    0  valid
    1  validation errors found (or incomplete under --strict)
    2  usage or I/O error

Standard library only.
"""

import argparse
import difflib
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
    """Return True if text looks like an absolute path on this or any platform.

    A snapshot written on Linux may be validated on Windows and vice versa, so
    both forms are accepted regardless of the host OS. The explicit leading
    "/" check matters: since Python 3.13 ntpath.isabs("/workspace/x") is False
    on Windows, which would reject perfectly valid POSIX snapshots.
    """
    return (
        os.path.isabs(text)
        or text.startswith("/")
        or bool(re.match(r"^[A-Za-z]:[\\/]", text))
        or text.startswith("\\\\")
    )


def normalize_path(text):
    """Normalise a path for containment comparison, whatever the platform form."""
    value = text.strip().replace("\\", "/")
    value = re.sub(r"/+", "/", value)
    if len(value) > 1:
        value = value.rstrip("/")
    return value.casefold()


def is_within(path, root):
    """True when path lies under root, compared at segment boundaries.

    A plain prefix test would accept C:/work/app-backup/x.js for root
    C:/work/app, so the separator after the root is required.
    """
    target, base = normalize_path(path), normalize_path(root)
    return target == base or target.startswith(base + "/")


def edit_distance(left, right, limit=3):
    """Levenshtein distance, abandoned as soon as it exceeds limit."""
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous = list(range(len(right) + 1))
    for i, char_left in enumerate(left, 1):
        current = [i]
        for j, char_right in enumerate(right, 1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (char_left != char_right),
                )
            )
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def looks_like_root_typo(path, root, limit=2):
    """True when a path outside the root is really the root, misspelled.

    A file outside the root is often legitimate (a sibling package in a
    monorepo, a global config). A path whose leading segments differ from the
    root by only a character or two is not: it is a mistyped root, and the
    successor opens a directory that does not exist.
    """
    target = normalize_path(path).split("/")
    base = normalize_path(root).split("/")
    depth = min(len(base), len(target) - 1)
    if depth <= 0:
        return False
    prefix = "/".join(target[:depth])
    wanted = "/".join(base[:depth])
    return prefix != wanted and edit_distance(prefix, wanted, limit) <= limit


def has_repeated_separators(text):
    """Return True if a path contains doubled separators (an escaping mistake)."""
    body = text[2:] if text.startswith(("\\\\", "//")) else text
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
                close = difflib.get_close_matches(key, list(properties), n=1, cutoff=0.6)
                hint = " — did you mean %r?" % close[0] if close else ""
                errors.append("%s: unexpected field %r%s" % (path, key, hint))
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

# Values people type into vcs.commit that are not commits. A moving ref looks
# like an anchor but points at different content later, so a successor who
# clones and checks it out gets code that is not the code the task ran on.
MOVING_REFS = ("head", "main", "master", "latest", "dev", "develop", "trunk")

# A snapshot records conclusions, not the conversation that produced them.
# These patterns catch the residue - narration, activity, transcript markers -
# that survives a copy-paste from a session log.
NARRATION_RE = re.compile(
    r"^\s*(?:let me|let's|now i|next i|i'll|i will|i'm going|i am going|first,? i"
    r"|then i|currently i|让我|我来|我先|我接下来|我现在|我准备|接下来(?:我|我们)"
    r"|现在我|现在让我们|好的[，,]|收到[，,]|明白[，,])",
    re.IGNORECASE,
)

ACTIVITY_RE = re.compile(
    r"^\s*(?:analyzing|checking|reading|reviewing|searching|looking at|looking into"
    r"|running|testing|debugging|inspecting|examining|exploring|digging|opening"
    r"|updating|modifying|implementing|refactoring|comparing|investigating"
    r"|分析|检查|查看|阅读|搜索|运行|测试|调试|排查|对比|修改|更新|重构|梳理)",
    re.IGNORECASE,
)

RESULT_CUE_RE = re.compile(
    r"(?:show(?:s|ed|ing)?|reveal(?:s|ed)?|found|findings?"
    r"|because|so that|therefore|thus|means|implies|confirmed|verified"
    r"|result(?:s|ed)?(?:\s+in)?|return(?:s|ed)?|fail(?:s|ed)?|error|exception"
    r"|cannot|can't|only|instead|conflict|limitation|requires?|no longer"
    r"|发现|显示|表明|说明|因此|所以|导致|结论|返回|报错|失败|冲突|限制|只有|改为"
    r"|意味着|确认|通过|正常|成功|生效|完成|仍然|还是)",
    re.IGNORECASE,
)

TRANSCRIPT_RE = re.compile(
    r"^\s*(?:\[\d{1,2}:\d{2}|【\d{1,2}:\d{2}】|\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"
    r"|(?:user|human|assistant|ai|system|用户|助手)\s*[:：]"
    r"|(?:step|步骤)\s*\d+\s*[:：.)、])",
    re.IGNORECASE,
)

# Fields where an activity statement means the author copied the log instead of
# the result. in_progress is excluded on purpose: there, activity is the fact.
ACTIVITY_FIELDS = ("completed", "findings", "handoff_notes", "assumptions")

MAX_ENTRY_CHARS = 600

# Words that carry no meaning for duplicate detection. Negations ("not", "no",
# "only") are deliberately absent: they invert a conclusion.
STOPWORDS = set(
    """a an the is are was were be been being am do does did doing have has had
    having and or but if then than that this these those it its of in on at to
    for from with by as so such there here we you i they he she them us our we
    will would shall should can could may might must""".split()
)


def normalize_entry(text):
    """Fold wording differences that do not change meaning."""
    value = text.strip().lower()
    value = re.sub(r"[`*_]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .。!！?？;；:：,，-—")


def content_tokens(text):
    """Meaning-carrying words, with separators inside identifiers removed.

    Splitting on "-", "_" and "." is what makes "download-interception" and
    "download interception" the same two words, while keeping "ct.js" and
    "bg.js" different (ct vs bg).
    """
    words = re.findall(r"[a-z0-9]+", re.sub(r"[-_.]", " ", text.lower()))
    return set(word for word in words if word not in STOPWORDS)


def cjk_units(text):
    """Character bigrams of the Chinese runs in text."""
    units = set()
    for chunk in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(chunk) == 1:
            units.add(chunk)
        units.update(chunk[index:index + 2] for index in range(len(chunk) - 1))
    return units


def entries_duplicate(left, right):
    """True when two entries would lead a successor to the same action.

    Word-level comparison, not character similarity: "the filter runs in ct.js"
    and "the filter runs in bg.js" are 96% identical as strings and say opposite
    things. Same content words in a different order, on the other hand, is the
    usual form of a conclusion restated after a retry.
    """
    if normalize_entry(left) == normalize_entry(right):
        return True
    words_left, words_right = content_tokens(left), content_tokens(right)
    if len(words_left) >= 4 and len(words_right) >= 4:
        return words_left == words_right
    units_left, units_right = cjk_units(left), cjk_units(right)
    if len(units_left) >= 4 and len(units_right) >= 4:
        union = units_left | units_right
        return len(units_left & units_right) / float(len(union)) >= 0.9
    return difflib.SequenceMatcher(None, left, right).ratio() >= 0.95


def iter_entry_texts(snapshot):
    """Yield (json_path, text, field) for every conclusion-bearing entry."""
    progress = snapshot.get("progress") or {}
    context = snapshot.get("context") or {}
    resume = snapshot.get("resume") or {}
    for field in ("completed", "in_progress", "findings", "blockers", "risks"):
        for index, value in enumerate(progress.get(field) or []):
            if isinstance(value, str) and value.strip():
                yield "$.progress.%s[%d]" % (field, index), value, field
    for index, item in enumerate(progress.get("next_steps") or []):
        if isinstance(item, dict) and isinstance(item.get("action"), str):
            if item["action"].strip():
                yield ("$.progress.next_steps[%d].action" % index, item["action"], "next_steps")
    for index, item in enumerate(context.get("key_decisions") or []):
        if isinstance(item, dict) and isinstance(item.get("decision"), str):
            if item["decision"].strip():
                yield ("$.context.key_decisions[%d].decision" % index, item["decision"], "decisions")
    for index, value in enumerate(context.get("assumptions") or []):
        if isinstance(value, str) and value.strip():
            yield "$.context.assumptions[%d]" % index, value, "assumptions"
    for index, value in enumerate(resume.get("handoff_notes") or []):
        if isinstance(value, str) and value.strip():
            yield "$.resume.handoff_notes[%d]" % index, value, "handoff_notes"


def check_log_quality(snapshot, errors):
    """Reject a snapshot that is a transcript rather than a set of conclusions.

    A copied log always looks valid: the fields have the right types, the values
    appear in the Markdown, and the file is huge. What it loses is the point of
    the snapshot - the successor pays for the process and still has to find the
    conclusion themselves. So narration, duplicated conclusions, and pasted
    output are errors under --strict.
    """
    entries = list(iter_entry_texts(snapshot))

    seen = []
    for path, text, field in entries:
        key = normalize_entry(text)
        for other_path, other_key in seen:
            if min(len(key), len(other_key)) < 10:
                continue
            if key == other_key:
                errors.append(
                    "strict: %s repeats %s word for word — one conclusion, one entry; "
                    "merge them and keep the more precise wording" % (path, other_path)
                )
                break
            if entries_duplicate(key, other_key):
                errors.append(
                    "strict: %s restates %s — same content, different wording; a "
                    "successor would act on it once, so merge them into one entry"
                    % (path, other_path)
                )
                break
        else:
            seen.append((path, key))

        if NARRATION_RE.match(text):
            errors.append(
                "strict: %s narrates the work (%r) — record the conclusion, not the "
                "intention; narration tells a successor nothing it can act on"
                % (path, text.strip()[:60])
            )
        elif (
            field in ACTIVITY_FIELDS
            and ACTIVITY_RE.match(text)
            and not RESULT_CUE_RE.search(text)
        ):
            errors.append(
                "strict: %s describes the activity (%r) rather than what it produced "
                "— state the outcome and its evidence" % (path, text.strip()[:60])
            )

        if TRANSCRIPT_RE.match(text):
            errors.append(
                "strict: %s starts with a transcript marker (%r) — timestamps, speaker "
                "labels and step numbers are the log, not the state" % (path, text.strip()[:60])
            )

        if len(text) > MAX_ENTRY_CHARS:
            errors.append(
                "strict: %s is %d characters — that reads as pasted log or tool "
                "output; quote the one line that decides the question"
                % (path, len(text))
            )



def check_file_prefixes(workspace, files, errors):
    """Reject paths that misspell workspace.root (--strict only)."""
    root = workspace.get("root")
    if not isinstance(root, str) or not root.strip():
        return
    root = root.strip()
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            continue
        path = path.strip()
        if not is_absolute_path(path) or is_within(path, root):
            continue
        if looks_like_root_typo(path, root):
            errors.append(
                "strict: $.artifacts.files[%d].path %r is outside workspace.root %r "
                "but differs from it only by a misspelling — this is a mistyped root "
                "prefix, so the successor opens nothing. Fix the prefix; a genuinely "
                "external file differs by whole directory names." % (index, path, root)
            )


def check_workspace(artifacts, errors):
    """Reject a workspace record that cannot be used to rebuild the checkout."""
    workspace = artifacts.get("workspace") or {}
    files = [entry for entry in (artifacts.get("files") or []) if isinstance(entry, dict)]
    raw_root = workspace.get("root")
    root = raw_root.strip() if isinstance(raw_root, str) else ""
    vcs = workspace.get("vcs") or {}

    if not root:
        if files:
            errors.append(
                "strict: $.artifacts.workspace.root is missing while $.artifacts.files "
                "lists %d path(s) — without the root a successor cannot tell which "
                "prefix is the project" % len(files)
            )
        if vcs:
            errors.append(
                "strict: $.artifacts.workspace.vcs is recorded but root is missing — "
                "a checkout exists at a location, so record it"
            )

    for label, value in (
        ("$.artifacts.workspace.root", root),
        ("$.artifacts.workspace.vcs.toplevel", vcs.get("toplevel")),
    ):
        if not isinstance(value, str) or not value.strip():
            continue
        if not is_absolute_path(value):
            errors.append(
                "strict: %s %r is not absolute — a successor cannot locate the "
                "project from a relative path" % (label, value.strip())
            )
        elif has_repeated_separators(value.strip()):
            errors.append(
                "strict: %s %r has repeated separators — fix the escaping"
                % (label, value.strip())
            )

    commit = vcs.get("commit")
    if isinstance(commit, str) and commit.strip().lower() in MOVING_REFS:
        errors.append(
            "strict: $.artifacts.workspace.vcs.commit %r is a moving ref, not a "
            "resolved revision — record the hash (git rev-parse HEAD)" % commit
        )

    uncommitted = vcs.get("uncommitted")
    if vcs.get("dirty") is True and not (
        isinstance(uncommitted, str) and uncommitted.strip()
    ):
        errors.append(
            "strict: $.artifacts.workspace.vcs.dirty is true but uncommitted is empty "
            "— a fresh clone will not contain that work, so the successor loses it; "
            "commit or stash it, or record what is uncommitted"
        )


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

    check_workspace(artifacts, errors)
    check_file_prefixes(
        artifacts.get("workspace") or {}, artifacts.get("files") or [], errors
    )
    check_log_quality(snapshot, errors)

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
        "relative file paths, a files[].path that misspells workspace.root, "
        "duplicated or narrated log residue, updated_at before created_at)",
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

    # A schema_version mismatch means the bundle predates (or postdates) this
    # skill. Replace the raw const message with something the reader can act on.
    version_errors = [
        item for item in errors if item.startswith("$.schema_version: expected const")
    ]
    if version_errors:
        expected = schema.get("properties", {}).get("schema_version", {}).get("const")
        errors = [item for item in errors if item not in version_errors]
        errors.insert(
            0,
            "snapshot format is %r but this skill expects %r — regenerate the bundle "
            "with scaffold.py, or add the fields introduced since then and bump "
            "schema_version (see the format changelog in SKILL.md)"
            % (snapshot.get("schema_version"), expected),
        )

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
        print(
            "    strict: no empty fields, no placeholders, no duplicated or narrated "
            "log residue, complete enough to hand off"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
