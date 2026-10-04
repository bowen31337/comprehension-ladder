# Rung 2: diagram style

Karpathy: "Instead of writing, ask your LLM to create a diagram. These can be a lot easier to process, parse, and understand."

The image in his post is the reference: a one-page **technical overview sheet** about ASD-STE100, drawn like an engineering drawing. Use that style by default.

## The overview-sheet style

- **Sheet.** Landscape, 1600×1000 viewBox or similar. Off-white background (`#fbfaf7`), near-black ink (`#1d1d1f`). One accent color for "approved/good" (blue `#1f5fbf`) and one for "not approved/bad" (red `#c0392b`). Use grey for structure.
- **Border with a grid reference.** A thin frame with column numbers (1–8) on the top and bottom edges and row letters (A–D) on the sides. It shows the reader that this is a reference sheet, and lets them say "panel B3".
- **Panels.** A grid of rectangles, each with a dark letter tab (A, B, C…) and a title in caps. **One concept per panel.** Six panels is a good maximum.
- **Title block.** Bottom-right box: title, subject, scope, date, "Sheet 1 of 1". Same as an engineering drawing.
- **Type.** A monospace font for labels and code (`ui-monospace, "SF Mono", Menlo, monospace`), a sans font for titles. Labels are 11–13px. Titles are 14–16px.
- **Marks.** Thin 1px rules. Small circles or ✓ / ✕ for status. Bar gauges for limits (e.g. "sentence length: max 20"). Callout lines with a short label to annotate an example.

## Panel types that work

| Panel | Use it for |
|---|---|
| Tree / structure | Parts of a system or a document |
| Annotated example | One real sentence, request or line of code, with callouts that name each part |
| Table with status marks | Allowed vs not allowed, before vs after |
| Gauge bars | Limits, sizes, budgets |
| Timeline | History, or the order of events |
| Sequence | Who sends what to whom, in order (arrows with labels) |

## Rules

- Show the mechanism. Every arrow has a label that says what moves (a token, a request, a value). An arrow with no label is decoration.
- Labels have ≤6 words and follow the strictness setting. Longer text goes in a Notes panel, in short STE sentences.
- A hedge in the source becomes a **dashed** line or box plus "possible" / "may" in the label. Never a solid line.
- Do not draw a value the source does not give. If a panel needs a sample number, label it "example".
- Make the SVG self-contained: no external fonts or images. Put `<title>` and `<desc>` first for accessibility.
- Use Mermaid only for a plain flowchart or sequence. It cannot show the panel layout.

## SVG skeleton

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" font-family="ui-monospace, 'SF Mono', Menlo, monospace">
  <title>TOPIC: overview</title>
  <desc>One-sentence summary of what the sheet shows.</desc>
  <rect width="1600" height="1000" fill="#fbfaf7"/>
  <rect x="20" y="20" width="1560" height="960" fill="none" stroke="#1d1d1f" stroke-width="1.5"/>
  <!-- grid reference: column numbers top/bottom, row letters left/right -->
  <g font-size="11" fill="#6e6e73" text-anchor="middle">
    <text x="117" y="14">1</text><!-- … repeat every 195px … -->
  </g>
  <!-- panel A -->
  <g transform="translate(40,40)">
    <rect width="500" height="420" fill="#fff" stroke="#c7c7cc"/>
    <rect width="28" height="28" fill="#1d1d1f"/>
    <text x="14" y="19" fill="#fff" font-size="14" text-anchor="middle" font-weight="700">A</text>
    <text x="40" y="19" font-size="14" font-weight="700" font-family="system-ui, sans-serif">PANEL TITLE</text>
    <!-- panel content -->
  </g>
  <!-- title block, bottom right -->
  <g transform="translate(1180,840)">
    <rect width="380" height="120" fill="#fff" stroke="#1d1d1f"/>
    <text x="12" y="28" font-size="16" font-weight="700" font-family="system-ui, sans-serif">Title of sheet</text>
    <text x="12" y="56" font-size="11">Subject: …</text>
    <text x="12" y="76" font-size="11">Scope: …</text>
    <text x="12" y="104" font-size="11">Sheet 1 of 1</text>
  </g>
</svg>
```

Check with `ste-lint.py --strictness 80 diagram.svg`. It reads the `<text>` content.
