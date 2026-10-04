#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Deterministic linter for the structural STE rules in SKILL.md.

Vendored from https://github.com/danyuchn/asd-ste100-skill (MIT License,
Copyright (c) 2026 Dustin Yuchen Teng). comprehension-ladder adds
--strictness (Karpathy's "80% of the way to ASD-STE100" setting) and
--html (lint the visible text of an HTML or SVG explainer).

Checks only rules verifiable without ASD's dictionary. Deliberately never
flags hedges or modality (may/might/could): the skill treats confidence as
content, and a linter that pressures hedges out would rewrite claims.

Usage:
    ste-lint.py FILE [FILE ...]
    echo "text" | ste-lint.py [--json]
    ste-lint.py --baseline 5 FILE      # pass unless hard violations exceed 5
    ste-lint.py --disable passive-voice,present-perfect FILE
    ste-lint.py --strictness 80 FILE   # rule set for 80% STE (see STRICTNESS)
    ste-lint.py --html page.html       # lint visible text only (auto for .html/.svg)
                                       # + prose-like JS strings (runtime captions);
                                       # --no-js-strings to skip them
    ste-lint.py --selftest

Exit 1 when hard ("advisory-free") violations exceed the baseline (default 0).
Advisory findings (passive voice, compound tenses) never fail the run.
"""
import json
import re
import sys

# ponytail: regex heuristics, not a parser. No noun-cluster rule — needs POS
# tagging to avoid constant false positives; add spaCy-backed rule if ever needed.
# No ellipsis rule by owner's choice: technical writing sometimes earns one.
RULES = [
    ("semicolon", "advisory-free",
     re.compile(r";"),
     "STE bans the semicolon (Rule 8.1). Split into separate sentences."),
    ("phrasal-verb", "advisory-free",
     re.compile(r"\b(spin(?:ning|s)? up|spun up|reach(?:ing|es|ed)? out|div(?:e|es|ing|ed) into|dove into|kick(?:ing|s|ed)? off|circl(?:e|es|ing|ed) back|touch(?:ing|es|ed)? base)\b", re.I),
     "Soft phrasal verb. Use the single plain verb (start, contact, read, begin)."),
    ("marketing-adjective", "advisory-free",
     re.compile(r"\b(seamless(?:ly)?|robust(?:ly)?|cutting-edge|effortless(?:ly)?|blazing[- ]fast|world-class|state-of-the-art|game-chang(?:ing|er))\b", re.I),
     "Marketing adjective. Delete, or replace with the measurement that earns the claim."),
    ("nominalization", "advisory-free",
     re.compile(r"\b(perform|performs|performed|conduct|conducts|conducted|carry out|carries out|carried out)\s+(?:a|an|the)\s+\w+(?:tion|sion|ment|ance|ence|ysis)\b", re.I),
     "Action frozen into a noun. Use the verb (analyze, not perform an analysis of)."),
    ("passive-voice", "advisory",
     re.compile(r"\b(is|are|was|were|been|being)\s+(\w+ed|given|taken|made|done|found|seen|known|shown|written|built|sent|set|run|read|kept|held|left|put)\b(?!\s+(?:to|for|by)\s+\w+ing)", re.I),
     "Possible passive voice. Name the actor and use an active verb, unless the actor is unknown or irrelevant."),
    ("present-perfect", "advisory",
     # modal + perfect infinitive ("may have failed") is a protected hedge, not present perfect
     re.compile(r"(?<!\bmay )(?<!\bmight )(?<!\bcould )(?<!\bshould )(?<!\bwould )(?<!\bmust )\b(has|have|had)\s+(?:been\s+)?\w+(?:ed|en)\b", re.I),
     "Compound tense. Use simple past/present unless current relevance is the point (then keep and flag)."),
]

# One word, one meaning: groups of verbs commonly rotated for the same action.
# Only pairs where the members are genuinely interchangeable — error/fault/failure
# are distinct concepts and stay out.
SYNONYM_GROUPS = [
    ("check", "verify", "confirm", "validate"),
    ("delete", "remove", "erase"),
    ("start", "launch", "begin", "initiate"),
    ("stop", "halt", "terminate"),
    ("show", "display"),
    ("use", "utilize", "employ"),
    ("fix", "repair", "correct"),
    ("send", "transmit"),
    ("get", "retrieve", "fetch", "obtain"),
    ("change", "modify", "alter"),
]

MAX_WORDS = 25  # descriptions cap; instructions cap is 20 but undetectable without context

# Strictness setting: (minimum %, sentence cap, rules that fail the run).
# Every other rule still reports, as advisory. Lexical rules (synonym rotation)
# turn hard only at the top setting, because without ASD's dictionary they are
# a direction of travel, not a checkable standard. present-perfect never turns
# hard: current relevance is a real exception (see SKILL.md).
STRICTNESS = [
    (90, 20, {"semicolon", "phrasal-verb", "marketing-adjective", "nominalization",
              "long-sentence", "dangling-conjunction", "synonym-rotation",
              "passive-voice"}),
    (70, 25, {"semicolon", "phrasal-verb", "marketing-adjective", "nominalization",
              "long-sentence", "dangling-conjunction"}),
    (40, 30, {"semicolon", "long-sentence", "marketing-adjective"}),
    (0, 35, set()),
]


def strictness_profile(percent):
    for floor, cap, hard in STRICTNESS:
        if percent >= floor:
            return cap, hard
    return STRICTNESS[-1][1], STRICTNESS[-1][2]


HTML_DROP = re.compile(r"<(script|style|head)\b.*?</\1\s*>", re.I | re.S)
HTML_BLOCK = re.compile(r"</?(p|div|li|h[1-6]|tr|td|th|section|article|br|text|tspan|title|figcaption|button|label|summary)\b[^>]*>", re.I)
HTML_TAG = re.compile(r"<[^>]+>")


JS_SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.I | re.S)
JS_STRING = re.compile(r"`((?:[^`\\]|\\.)*)`|\"((?:[^\"\\\n]|\\.)*)\"|'((?:[^'\\\n]|\\.)*)'")


def js_prose(markup):
    """Prose-like string literals in <script> blocks: captions the page writes at runtime.

    A literal counts as prose when it has 4+ words and starts with a letter or
    a ${...} value. ${...} becomes "N" so a caption template lints like the
    sentence a reader sees. Code strings (selectors, CSS, keys) rarely pass.
    """
    out = []
    for script in JS_SCRIPT.findall(markup):
        for m in JS_STRING.finditer(script):
            lit = next(g for g in m.groups() if g is not None)
            lit = re.sub(r"\$\{[^}]*\}", "N", lit).replace("\\n", " ")
            if re.match(r"^\s*[A-Za-z]", lit) and len(lit.split()) >= 4 and not re.search(r"[{}=<>]", lit):
                out.append(" ".join(lit.split()))
    return out


def html_text(markup, include_js=True):
    """Visible text of an HTML/SVG file, one block per line. Regex, not a parser.
    With include_js, prose-like JS string literals follow, one per line."""
    import html as _html
    extra = js_prose(markup) if include_js else []
    text = HTML_DROP.sub(" ", markup)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = HTML_BLOCK.sub("\n", text)
    text = HTML_TAG.sub(" ", text)
    text = _html.unescape(text)
    lines = [" ".join(l.split()) for l in text.splitlines() if l.strip()]
    return "\n".join(lines + extra)


CODE_FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
LIST_ITEM_START = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>[-*+]|[0-9]+[.)])(?P<gap> +)(?P<body>.*)$"
)
CONJUNCTION_END = re.compile(r"\b(?:and|or)\s*$", re.I)
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


def _word_re(base):
    return re.compile(r"\b" + base + r"(?:s|es|ed|d|ing)?\b", re.I)


def _leading_spaces(line):
    return len(line) - len(line.lstrip(" "))


def _is_list_continuation(line, content_indent):
    if not line.strip():
        return True
    if LIST_ITEM_START.match(line):
        return False
    return _leading_spaces(line) >= content_indent


def _split_table_row(line):
    """Return trimmed table cells and their zero-based source columns.

    A pipe must separate at least two cells. Escaped pipes stay in their cell.
    This deliberately implements only the ordinary Markdown table shape; it is
    enough to distinguish a table from prose that happens to contain a pipe.
    """
    left = len(line) - len(line.lstrip())
    right = len(line.rstrip())
    content = line[left:right]
    if "|" not in content:
        return None
    if content.startswith("|"):
        content = content[1:]
        left += 1
    if content.endswith("|"):
        content = content[:-1]
    raw_cells = re.split(r"(?<!\\)\|", content)
    if len(raw_cells) < 2:
        return None

    cells = []
    column = left
    for raw_cell in raw_cells:
        leading = len(raw_cell) - len(raw_cell.lstrip())
        cells.append((raw_cell.strip(), column + leading))
        column += len(raw_cell) + 1
    return cells


def _markdown_table_cells(lines):
    """Map ordinary Markdown table rows to their prose cells.

    The separator row anchors detection, so pipe-containing prose is not
    treated as a table. Both leading-pipe and no-leading-pipe table styles are
    accepted when their header and body use the same number of cells.
    """
    table_cells = {}
    index = 1
    while index < len(lines):
        separator = _split_table_row(lines[index])
        header = _split_table_row(lines[index - 1])
        if (not separator or not header or len(separator) != len(header)
                or not all(TABLE_SEPARATOR_CELL.fullmatch(cell)
                           for cell, _ in separator)):
            index += 1
            continue

        table_cells[index - 1] = header
        table_cells[index] = []
        index += 1
        while index < len(lines):
            row = _split_table_row(lines[index])
            if not row or len(row) != len(separator):
                break
            table_cells[index] = row
            index += 1
    return table_cells


def _dangling_conjunction_findings(text, filename):
    lines = text.splitlines()
    findings = []
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if CODE_FENCE.match(stripped):
            in_fence = not in_fence
            index += 1
            continue
        if in_fence:
            index += 1
            continue
        start = LIST_ITEM_START.match(line)
        if not start:
            index += 1
            continue

        content_indent = (len(start.group("indent"))
                          + len(start.group("marker"))
                          + len(start.group("gap")))
        item_lines = [(index, start.group("body"))]
        next_index = index + 1
        item_fence = False
        while next_index < len(lines):
            candidate = lines[next_index]
            candidate_stripped = candidate.strip()
            if CODE_FENCE.match(candidate_stripped):
                # Fence delimiters are state markers, not meaningful item lines.
                item_fence = not item_fence
                next_index += 1
                continue
            if item_fence:
                next_index += 1
                continue
            if not _is_list_continuation(candidate, content_indent):
                break
            item_lines.append((next_index, candidate))
            next_index += 1

        meaningful = []
        for line_index, item_line in item_lines:
            # Preserve code spans as neutral operands while ignoring their contents.
            cleaned = INLINE_CODE.sub(" CODE ", item_line).strip()
            if cleaned:
                meaningful.append((line_index, cleaned))
        if meaningful:
            end_line_index, end_line = meaningful[-1]
            conjunction = CONJUNCTION_END.search(end_line)
        else:
            end_line_index, end_line, conjunction = None, None, None
        if conjunction:
            if end_line_index == index:
                finding_line = index + 1
                finding_col = start.start("marker") + 1
            else:
                raw_end_line = next(
                    raw for line_index, raw in item_lines
                    if line_index == end_line_index
                )
                masked_end_line = INLINE_CODE.sub(
                    lambda match: " " * len(match.group(0)), raw_end_line
                )
                raw_conjunction = CONJUNCTION_END.search(masked_end_line)
                finding_line = end_line_index + 1
                finding_col = raw_conjunction.start() + 1 if raw_conjunction else 1
            findings.append({
                "file": filename,
                "line": finding_line,
                "col": finding_col,
                "rule": "dangling-conjunction",
                "level": "advisory-free",
                "match": end_line,
                "message": "List item ends with a coordinating conjunction. Complete the item or join it with the next item.",
            })
        index = next_index
    return findings


def lint(text, filename="<stdin>", max_words=MAX_WORDS):
    findings = []
    words_total = 0
    in_fence = False
    lines = text.splitlines()
    table_cells = _markdown_table_cells(lines)
    # first occurrence of each synonym-group member: (group_idx, base) -> (line, col, match)
    seen_synonyms = {}
    for lineno, raw_line in enumerate(lines, 1):
        if CODE_FENCE.match(raw_line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        segments = table_cells.get(lineno - 1, [(raw_line, 0)])
        for segment, source_column in segments:
            line = INLINE_CODE.sub("", segment)
            words_total += len(line.split())
            for rule_id, level, pattern, msg in RULES:
                for m in pattern.finditer(line):
                    findings.append({"file": filename, "line": lineno,
                                     "col": source_column + m.start() + 1,
                                     "rule": rule_id, "level": level,
                                     "match": m.group(0), "message": msg})
            for gi, group in enumerate(SYNONYM_GROUPS):
                for base in group:
                    if (gi, base) in seen_synonyms:
                        continue
                    m = _word_re(base).search(line)
                    if m:
                        seen_synonyms[(gi, base)] = (
                            lineno, source_column + m.start() + 1, m.group(0)
                        )
            for sent in re.split(r"(?<=[.!?])\s+", line):
                n = len(sent.split())
                if n > max_words:
                    findings.append({"file": filename, "line": lineno,
                                     "col": source_column + 1,
                                     "rule": "long-sentence", "level": "advisory-free",
                                     "match": f"{n} words",
                                     "message": f"Sentence has {n} words (cap {max_words}). Split it."})
    # synonym rotation: flag each member after the first, at its first occurrence
    for gi, group in enumerate(SYNONYM_GROUPS):
        present = [(seen_synonyms[(gi, b)], b) for b in group if (gi, b) in seen_synonyms]
        if len(present) > 1:
            present.sort()  # document order
            first_base = present[0][1]
            for (lineno, col, match), base in present[1:]:
                findings.append({"file": filename, "line": lineno, "col": col,
                                 "rule": "synonym-rotation", "level": "advisory-free",
                                 "match": match,
                                 "message": f"'{base}' and '{first_base}' name the same action. Pick one and use it every time."})
    findings.extend(_dangling_conjunction_findings(text, filename))
    findings.sort(key=lambda f: (f["line"], f["col"]))
    return findings, words_total


def report(findings, words_total, as_json, hard_count, baseline):
    rate = round(len(findings) * 100 / words_total, 1) if words_total else 0.0
    if as_json:
        print(json.dumps({"violations": findings, "count": len(findings),
                          "hard_count": hard_count, "baseline": baseline,
                          "words": words_total, "per_100_words": rate}, indent=2))
        return
    for f in findings:
        print(f"{f['file']}:{f['line']}:{f['col']} {f['rule']}: {f['message']} [{f['match']}]")
    print(f"\n{len(findings)} violations ({hard_count} hard, baseline {baseline}), "
          f"{words_total} words, {rate} per 100 words")
    print("Hedges/modality (may, might, could) are never flagged: confidence is content.")


def selftest():
    bad = ("The panel is removed; spin up the job. "
           "Perform an analysis of the seamless log. "
           "We have received the report.")
    findings, _ = lint(bad)
    rules = {f["rule"] for f in findings}
    for expected in ("semicolon", "phrasal-verb", "nominalization",
                     "marketing-adjective", "passive-voice", "present-perfect"):
        assert expected in rules, expected
    # hedges must never be flagged, including modal + perfect infinitive
    findings, _ = lint("The request may have failed. It could be a timeout. "
                       "The disk might have filled.")
    assert findings == [], findings
    # code blocks skipped
    findings, _ = lint("```\nx = a; y = b\n```")
    assert findings == []
    # all supported list markers, case variants, and trailing whitespace
    findings, _ = lint(
        "- Confirm the target and\n"
        "* Record the result OR  \n"
        "+ Close the panel\n"
        "1. Start the task and\n"
        "2) Stop the task OR"
    )
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 4, dangling
    assert [f["line"] for f in dangling] == [1, 2, 4, 5], dangling
    assert [f["col"] for f in dangling] == [1, 1, 1, 1], dangling
    assert all(f["level"] == "advisory-free" for f in dangling), dangling

    # valid continuation lines and standalone four-space code are ignored
    findings, _ = lint("  - Confirm the target and\n    record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Confirm the target\n  and")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["line"] == 2, dangling
    assert dangling[0]["col"] == 3, dangling
    findings, _ = lint("    - code and")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("> - Confirm the target and\n> - Record the result or")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Do this and\n~~~\ncode and\n~~~")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["line"] == 1, dangling
    findings, _ = lint("```text\n- code and\n```")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)

    # one- and three-space markers and ordered continuation width
    findings, _ = lint(" - Start the task and\n   record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("-  Start the task and\n   record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("-\tStart the task and")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("   - Start the task and", filename="fixture.md")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1 and dangling[0]["col"] == 4, dangling
    assert dangling[0]["file"] == "fixture.md"
    assert dangling[0]["match"].endswith("and")
    assert "Complete the item" in dangling[0]["message"]
    findings, _ = lint("100. Start the task and\n  unrelated text")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert len(dangling) == 1, dangling
    findings, _ = lint("- Start the task and.\n- Stop the task or,")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Start the task and\n\n  record the result.")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Parent item and\n  - Nested item or")
    dangling = [f for f in findings if f["rule"] == "dangling-conjunction"]
    assert [f["line"] for f in dangling] == [1, 2], dangling

    # ordinary prose, inline code, and fenced code are ignored
    findings, _ = lint("The process may include steps and")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Use `and` as a label")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint("- Combine `left` and `right`")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings), findings
    findings, _ = lint("~~~\n- code and\n~~~")
    assert not any(f["rule"] == "dangling-conjunction" for f in findings)
    findings, _ = lint(("word " * 30).strip() + ".")
    assert any(f["rule"] == "long-sentence" for f in findings)
    # Markdown table syntax is layout, not prose. Each cell stays lintable.
    short_cell = " ".join(f"term{number}" for number in range(1, 25)) + "."
    for table in (
            "| Label | Detail |\n"
            "| --- | --- |\n"
            f"| Clear | {short_cell} |",
            "Label | Detail\n"
            "--- | ---\n"
            f"Clear | {short_cell}"):
        findings, words_total = lint(table)
        assert not any(f["rule"] == "long-sentence" for f in findings), findings
        assert words_total == 27, words_total
    long_cell = " ".join(f"term{number}" for number in range(1, 27)) + "."
    findings, _ = lint(
        "| Label | Detail |\n"
        "| --- | --- |\n"
        f"| Clear | {long_cell} |"
    )
    long_sentences = [f for f in findings if f["rule"] == "long-sentence"]
    assert len(long_sentences) == 1, long_sentences
    assert long_sentences[0]["match"] == "26 words", long_sentences
    # synonym rotation: second member flagged, first named as the keeper
    findings, _ = lint("Check the config file. Then verify the output. Verify twice.")
    rot = [f for f in findings if f["rule"] == "synonym-rotation"]
    assert len(rot) == 1 and "'verify' and 'check'" in rot[0]["message"], rot
    # single consistent term: no flag
    findings, _ = lint("Check the config. Check the output.")
    assert not any(f["rule"] == "synonym-rotation" for f in findings)
    # per-file labels
    findings, _ = lint("a; b", filename="x.md")
    assert findings[0]["file"] == "x.md"
    # strictness: 80 keeps synonym rotation advisory, 95 makes it hard
    text = "Check the config. Verify the output."
    for pct, expect in ((80, "advisory"), (95, "advisory-free")):
        cap, hard = strictness_profile(pct)
        f = [x for x in lint(text, max_words=cap)[0] if x["rule"] == "synonym-rotation"]
        assert f and (("advisory-free" if f[0]["rule"] in hard else "advisory") == expect), (pct, f)
    # strictness changes the sentence cap: 22 words fails at 95, passes at 80
    s22 = " ".join(["word"] * 21) + " end."
    assert any(x["rule"] == "long-sentence" for x in lint(s22, max_words=strictness_profile(95)[0])[0])
    assert not any(x["rule"] == "long-sentence" for x in lint(s22, max_words=strictness_profile(80)[0])[0])
    # html: script/style dropped, block tags split lines, entities decoded
    t = html_text("<html><head><style>a{b:c;}</style></head><body><h1>Title</h1>"
                  "<p>One &amp; two.</p><script>x=1;</script><svg><text>Label</text></svg></body></html>")
    assert t.split("\n") == ["Title", "One & two.", "Label"], t
    # runtime captions in JS are linted, code strings are not
    page = ("<p>Hi.</p><script>const sel = 'div.figure > canvas';"
            "cap.textContent = `At ${lr}, the path overshoots; it diverges.`;"
            "el.innerHTML = '<b>x</b> and more words here';</script>")
    tj = html_text(page)
    assert tj.split("\n") == ["Hi.", "At N, the path overshoots; it diverges."], tj
    assert any(f["rule"] == "semicolon" for f in lint(tj)[0])
    assert html_text(page, include_js=False) == "Hi."
    assert lint(t)[0] == []
    print("selftest OK")


def main(argv):
    if "--selftest" in argv:
        selftest()
        return 0
    as_json = "--json" in argv
    baseline = 0
    strictness = None
    force_html = "--html" in argv
    include_js = "--no-js-strings" not in argv
    disabled = set()
    paths = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--baseline":
            i += 1
            baseline = int(argv[i])
        elif a == "--strictness":
            i += 1
            strictness = int(argv[i])
        elif a == "--disable":
            i += 1
            disabled = set(argv[i].split(","))
        elif not a.startswith("--"):
            paths.append(a)
        i += 1

    cap, hard = (MAX_WORDS, None) if strictness is None else strictness_profile(strictness)

    def load(text, name):
        if force_html or name.lower().endswith((".html", ".htm", ".svg")):
            return html_text(text, include_js)
        return text

    findings, words_total = [], 0
    if paths:
        for p in paths:
            f, w = lint(load(open(p, encoding="utf-8").read(), p), filename=p, max_words=cap)
            findings.extend(f)
            words_total += w
    else:
        findings, words_total = lint(load(sys.stdin.read(), "<stdin>"), max_words=cap)

    if hard is not None:
        for f in findings:
            f["level"] = "advisory-free" if f["rule"] in hard else "advisory"

    findings = [f for f in findings if f["rule"] not in disabled]
    hard_count = sum(1 for f in findings if f["level"] == "advisory-free")
    report(findings, words_total, as_json, hard_count, baseline)
    return 1 if hard_count > baseline else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
