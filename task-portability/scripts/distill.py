#!/usr/bin/env python3
"""Distill a session log into candidate snapshot conclusions.

Usage:
    python3 distill.py <log-file> [--max N] [--min-len N] [--out FILE]

Reads a chat transcript, terminal transcript, or agent memory dump and prints a
Markdown worksheet:

    * candidates - lines that state a conclusion, quoted verbatim with their
      source line numbers, deduplicated by meaning;
    * a drop tally - how many lines each filter removed.

It is a filter, not a summarizer: nothing is paraphrased and nothing is
invented, so every candidate can be checked against the log. You still decide
which ones belong in the snapshot and write the final wording, because a
snapshot records conclusions, not the process that produced them.

Standard library only.
"""

import argparse
import re
import sys
from difflib import SequenceMatcher

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# "[12:05] ", "2026-11-11 11:44:12 ", "12:05:33 " - the timestamp says when, not what.
TIMESTAMP_RE = re.compile(
    r"^\s*(?:\[\d{1,2}:\d{2}(?::\d{2})?\]|【\d{1,2}:\d{2}】"
    r"|\d{1,2}:\d{2}(?::\d{2})?"
    r"|\[\d{4}-\d{2}-\d{2}[^\]]*\]"
    r"|\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)"
    r"(?:\s+|$)"
)

# Speaker labels mark who talked, not what is true.
ROLE_RE = re.compile(
    r"^\s*(?:user|human|assistant|ai|system|tool|agent|用户|助手|系统|工具)\s*[:：]\s*",
    re.IGNORECASE,
)

# Shell prompts, tool-call syntax, and pipeline noise.
TOOL_RE = re.compile(
    r"^\s*(?:\$|>|PS>|>>>|#|❯|→)\s+\S"
    r"|^\s*(?:tool_call|tool_use|function_call|tool result|Calling)\b"
    r"|^\s*\|\s*\S",
    re.IGNORECASE,
)

NARRATION_RE = re.compile(
    r"^\s*(?:let me|let's|now i|next i|i'll|i will|i'm|i am|first,?\s+i|then i"
    r"|currently i|okay[,.]?\s|sure[,!]\s|great question|of course|happy to"
    r"|done\.|让我|我来|我先|我想|我接下来|我现在|我准备"
    r"|接下来(?:我|我们)?|现在(?:我|我们)?|首先我们|好的[，,]|收到[，,]|明白[，,])",
    re.IGNORECASE,
)

# A gerund at the start describes the action, not the result - unless the
# sentence also reports what the action produced ("Reading ct.js revealed ...").
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
    r"|prefer(?:s|red)?|works|passed"
    r"|发现|显示|表明|说明|因此|所以|导致|结论|返回|报错|失败|冲突|限制|只有|改为"
    r"|意味着|确认|通过|正常|成功|生效|完成|偏好|习惯|要求|仍然|还是)",
    re.IGNORECASE,
)

CODE_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
ERROR_LINE_RE = re.compile(
    r"(?:error|exception|traceback|failed|fatal|cannot|not found"
    r"|报错|错误|失败|异常|未找到)",
    re.IGNORECASE,
)
BULLET_RE = re.compile(r"^\s*[-*•]\s+")
QUESTION_END_RE = re.compile(r"[?？]\s*$")

# Split on CJK terminators anywhere, but on an ASCII period only when a space
# follows and the next clause looks like a new sentence. Splitting on every "."
# cuts "ct.js" and "downloadItem.name" in half, which silently corrupts the
# very evidence a finding needs.
SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[。！？；])|(?<=[.!?])\s+(?=[A-Z0-9\"'(\[`])"
)

DROP_ORDER = (
    "empty",
    "fenced output",
    "tool call",
    "header",
    "narration",
    "activity",
    "question",
    "too short",
    "no conclusion",
    "duplicate",
)


def read_text(path):
    """Read a log file, tolerating UTF-8 (with BOM) and GB18030."""
    with open(path, "rb") as handle:
        data = handle.read()
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def normalize(text):
    """Fold wording differences that do not change meaning."""
    value = text.strip().lower()
    value = re.sub(r"[`*_]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .。!！?？;；:：,，-—")


STOPWORDS = set(
    """a an the is are was were be been being am do does did doing have has had
    having and or but if then than that this these those it its of in on at to
    for from with by as so such there here we you i they he she them us our
    will would shall should can could may might must""".split()
)


def cjk_units(text):
    """Character bigrams of the Chinese runs in text."""
    units = set()
    for chunk in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(chunk) == 1:
            units.add(chunk)
        units.update(chunk[index:index + 2] for index in range(len(chunk) - 1))
    return units


def similarity(left, right):
    """Similarity of two conclusions, decided on content words, not characters.

    "the filter runs in ct.js" and "the filter runs in bg.js" are 96% identical
    as strings and say opposite things, so a character ratio would collapse a
    contradiction into a duplicate. Same content words in a different order is
    the usual shape of a conclusion restated after a retry, and that is what
    this returns 1.0 for.
    """
    if left == right:
        return 1.0
    words_left = set(w for w in re.findall(r"[a-z0-9]+", re.sub(r"[-_.]", " ", left))
                     if w not in STOPWORDS)
    words_right = set(w for w in re.findall(r"[a-z0-9]+", re.sub(r"[-_.]", " ", right))
                      if w not in STOPWORDS)
    if len(words_left) >= 4 and len(words_right) >= 4:
        return 1.0 if words_left == words_right else 0.0
    units_left, units_right = cjk_units(left), cjk_units(right)
    if len(units_left) >= 4 and len(units_right) >= 4:
        union = units_left | units_right
        return len(units_left & units_right) / float(len(union))
    return SequenceMatcher(None, left, right).ratio()


def sentences(text):
    """Split a line into sentence-sized units without breaking file names."""
    return [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]


def strip_prefixes(line):
    """Remove timestamps and speaker labels, reporting what was stripped."""
    timestamps = labels = 0
    changed = True
    while changed:
        changed = False
        match = TIMESTAMP_RE.match(line)
        if match and match.end() < len(line):
            line = line[match.end():]
            timestamps += 1
            changed = True
            continue
        match = ROLE_RE.match(line)
        if match and match.end() < len(line):
            line = line[match.end():]
            labels += 1
            changed = True
    return line.strip(), timestamps, labels


def distill(text, min_len=12, max_items=40):
    """Return (candidates, stats, stripped, total_lines, truncated)."""
    lines = text.splitlines()
    stats = dict.fromkeys(DROP_ORDER, 0)
    stripped = {"timestamp": 0, "label": 0}
    candidates = []
    in_fence = False

    def offer(number, sentence):
        """Keep a sentence unless one already kept says the same thing."""
        key = normalize(sentence)
        if not key:
            stats["empty"] += 1
            return
        for index, (kept_line, kept_text) in enumerate(candidates):
            if normalize(kept_text) == key:
                stats["duplicate"] += 1
                return
            # Near-duplicates: the same conclusion restated after a retry. Keep
            # the longer wording, which usually carries the extra detail.
            if min(len(key), len(normalize(kept_text))) >= 12:
                if similarity(key, normalize(kept_text)) >= 0.9:
                    stats["duplicate"] += 1
                    if len(sentence) > len(kept_text) * 1.15:
                        candidates[index] = (kept_line, sentence)
                    return
        candidates.append((number, sentence))

    for number, raw in enumerate(lines, 1):
        line = ANSI_RE.sub("", raw).replace("\t", "  ").rstrip()
        if not line.strip():
            stats["empty"] += 1
            continue

        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            stats["fenced output"] += 1
            continue

        if in_fence:
            # Pasted output is not a conclusion - except the decisive error line,
            # which is often the only evidence for a finding.
            if ERROR_LINE_RE.search(line) and len(line.strip()) <= 300:
                offer(number, line.strip())
            else:
                stats["fenced output"] += 1
            continue

        if TOOL_RE.match(line):
            stats["tool call"] += 1
            continue

        text_part, timestamps, labels = strip_prefixes(line)
        stripped["timestamp"] += timestamps
        stripped["label"] += labels
        if not text_part:
            stats["header"] += 1
            continue

        if NARRATION_RE.match(text_part):
            stats["narration"] += 1
            continue

        if ACTIVITY_RE.match(text_part) and not RESULT_CUE_RE.search(text_part):
            stats["activity"] += 1
            continue

        for sentence in sentences(text_part):
            body = BULLET_RE.sub("", sentence).strip()
            if len(body) < min_len:
                stats["too short"] += 1
                continue
            if QUESTION_END_RE.search(body) and not RESULT_CUE_RE.search(body):
                stats["question"] += 1
                continue
            if BULLET_RE.match(sentence) or RESULT_CUE_RE.search(body):
                offer(number, body)
            else:
                stats["no conclusion"] += 1

    truncated = max(0, len(candidates) - max_items)
    return candidates[:max_items], stats, stripped, len(lines), truncated


def render(path, candidates, stats, stripped, total, truncated, max_items):
    """Render the worksheet as Markdown."""
    dropped = sum(stats.values())
    tally = ", ".join(
        "%s %d" % (name, stats[name]) for name in DROP_ORDER if stats[name]
    )
    cleaned = []
    if stripped["timestamp"]:
        cleaned.append("%d timestamp(s)" % stripped["timestamp"])
    if stripped["label"]:
        cleaned.append("%d speaker label(s)" % stripped["label"])
    lines = [
        "# Log distillation worksheet",
        "",
        "Source: `%s` — %d lines, %d candidate(s) kept." % (path, total, len(candidates)),
        "",
        "Dropped %d line(s): %s" % (dropped, tally or "nothing"),
        "Stripped from kept lines: %s" % (", ".join(cleaned) or "nothing"),
    ]
    if truncated:
        lines.append("Truncated %d candidate(s) at --max %d." % (truncated, max_items))
    lines += [
        "",
        "Kept text is **verbatim** and each line number points back into the log. "
        "Nothing was paraphrased and nothing was invented: decide which conclusions "
        "belong in the snapshot, then write the final wording yourself.",
        "",
        "## Candidates",
        "",
    ]
    if not candidates:
        lines.append(
            "- None. The log carries no conclusion-shaped line — read it again, or "
            "write the findings from what you learned rather than from the text."
        )
    else:
        for number, content in candidates:
            lines.append("- `L%d` — %s" % (number, content))
    lines += [
        "",
        "## What to do with them",
        "",
        "- Changes what the successor does → `progress.findings` (outcome + evidence).",
        "- Is now simply true → `progress.completed`.",
        "- A choice with its reason → `context.key_decisions`.",
        "- Only says what was done → drop it: that is the process, and the snapshot "
        "exists to not carry it.",
        "- Then run `validate.py --strict`, which rejects narration and duplicates "
        "that slipped through.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Distill a session log into candidate snapshot conclusions."
    )
    parser.add_argument("log", help="log / transcript / memory file to read")
    parser.add_argument(
        "--max", type=int, default=40, help="maximum candidates to print (default 40)"
    )
    parser.add_argument(
        "--min-len",
        type=int,
        default=12,
        help="shortest sentence to consider a conclusion (default 12 chars)",
    )
    parser.add_argument("--out", help="write the worksheet here instead of stdout")
    args = parser.parse_args()

    if args.max < 1:
        print("ERROR: --max must be at least 1", file=sys.stderr)
        return 2
    try:
        text = read_text(args.log)
    except OSError as exc:
        print("ERROR: cannot read %s (%s)" % (args.log, exc), file=sys.stderr)
        return 2

    candidates, stats, stripped, total, truncated = distill(text, args.min_len, args.max)
    worksheet = render(args.log, candidates, stats, stripped, total, truncated, args.max)

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(worksheet)
        except OSError as exc:
            print("ERROR: cannot write %s (%s)" % (args.out, exc), file=sys.stderr)
            return 2
        print(
            "Wrote worksheet: %s (%d candidates from %d lines)"
            % (args.out, len(candidates), total)
        )
    else:
        print(worksheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
