# Rung 3: interactive HTML explainer

Karpathy: "Ask for output 'in HTML' to get a beautiful, interactive webpage." And: you can ask for "large, custom, discardable software artifacts … that would have never made sense to create before."

The page exists to make one idea click for one reader. It is discardable. Spend the effort on the interaction, not on build tooling.

## Shape

Start from `assets/html-explainer-template.html`. It gives you:
- Apple system tokens with light and dark themes, and an Auto / Light / Dark control. Figures redraw on the `themechange` event.
- a mobile-first layout: a glass header that shows the title after the hero scrolls away, a main column, a contents sidebar and a footer
- on phones, the sidebar is a bottom sheet. A floating "Contents" capsule opens it. You can drag the sheet to close it. At 1024px and wider, the sidebar is a sticky glass column.
- a contents list that the page builds from each `section > h2`. You do not edit the list.
- a hero, a "the short version" card, numbered sections, and a `.figure.card` block with a canvas or SVG plus controls and a caption
- touch targets of 44px or more, large slider thumbs, and fallbacks for reduced motion, reduced transparency and high contrast

Edit only the content in `<main>`, the footer text and the "Figures" script block. Leave the "Page chrome" script block as it is. After you set a slider value from JS, call `syncRanges()` so that the slider fill moves too.

Typical page:
1. **Title and one-sentence summary.**
2. **The short version.** Three to five bullets in STE prose. These are the outline's core claims.
3. **One section per mechanism step.** Each has a short text and, where it helps, a live figure.
4. **"What this does not show."** Limits, hedges and open questions from the source. This is where the hedges stay visible.

## Interactions that help understanding

| Pattern | Use when | Example |
|---|---|---|
| Parameter slider | The outcome depends on a number | Learning rate → path of gradient descent |
| Step-through (Prev / Next) | A process has discrete stages | Each round of a protocol handshake |
| Before / after toggle | A change, a diff, a fix | Code before and after a refactor, with the changed lines marked |
| Hover or tap to reveal | Dense figure with many values | A heat map whose cells show their value |
| Play / pause | A process over continuous time | Particles in a diffusion process |
| Reader prediction | A result is surprising | "Guess the output, then reveal it" |

Rules for every control:
- It changes something visible at once (no "Run" button for a cheap calculation).
- A caption under the figure states what the current setting shows, in one STE sentence. Update the caption from JS when the control changes.
- Controls work by keyboard and by touch. Use real `<input type="range">` and `<button>` elements.
- Pick defaults that show the typical case. Add one preset button for the interesting edge case (e.g. "learning rate too high").

## Interactions that do not help

- Animation that only decorates (fade-ins on scroll, parallax).
- A control whose effect the reader cannot see.
- A "simulation" that plays a fixed script. If the page claims to show an algorithm, it runs the algorithm in JS.

## Technical rules

- One `.html` file. Inline CSS and JS.
- External scripts only from `cdnjs.cloudflare.com` or `cdn.jsdelivr.net`, and only when they save real work (KaTeX for math, D3 for a complex chart). The text must still render if the CDN fails.
- Canvas: scale for `devicePixelRatio` so lines are sharp. Redraw on resize.
- No tracking, no forms that send data, no `localStorage` unless it is a convenience (e.g. the last slider value) inside `try/catch`.
- Open the file in a browser to check it if one is available. Fix console errors.
- Lint the text: `uv run ste-lint.py --strictness 80 page.html`. The linter reads the visible text and also the prose-like string literals in `<script>` blocks, so runtime captions are checked too. It reads `${...}` as "N". A caption that you build from many small pieces can still slip through. Read those captions yourself.

## Facts on the page

The page shows numbers. Each number is either computed live, taken from the source, or labelled "example value". A default that looks like a measured fact but is not one breaks the "add no facts" rule.
