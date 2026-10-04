---
name: comprehension-ladder
description: |-
  Load this skill BEFORE replying whenever the main job is making a human understand something. Do not just answer in chat: the skill has a house style, a linter and render scripts that a plain reply skips. Cases:
  • Decoding: "I don't get this / what is it actually saying" about agent or log output, an error, a doc, a paper or your own earlier reply.
  • Explaining a PR, diff, design doc, code area or concept to the user, a manager, a newcomer or someone from another field.
  • Re-forming an explanation: "redo that as a diagram", a visual one-pager, an interactive HTML page, a narrated 3Blue1Brown/Manim-style video, or a fix for an earlier wall of text.
  • Any mention of Simplified Technical English, STE/STE100, or a strictness like "80% STE".
  Skip it for rewriting strings that agents read (tool descriptions, error messages, prompts; asd-ste100 does that), debugging Manim code, proofreading, translating, and marketing or voiceover copy.
---

# Comprehension Ladder

LLMs do more of the work every month. The human's job moves up to oversight and understanding. This skill helps with that job. It explains a topic in the format that makes it easiest to understand.

The idea comes from Andrej Karpathy's post of 2 October 2026 (https://x.com/karpathy/status/2105819303471976479). It describes a ladder of output formats. Each rung is usually easier to absorb than the one below it:

| Rung | Output | Good for |
|---|---|---|
| 1. STE prose | Markdown in ASD-STE100 style, at a chosen strictness | Short explanations, diffs, answers you will re-read |
| 2. Diagram | One SVG file (or Mermaid for pure flows and sequences) | Structure, data flow, sequences, comparisons |
| 3. Web page | One self-contained interactive HTML file | Anything with a parameter, a process over time, or a "what if" |
| 4. Explainer video | Manim scene + STE narration + TTS audio, muxed with ffmpeg | Topics that have a story and change over time |

Karpathy's other point matters as much as the ladder. Code is cheap now, so a large, custom, **discardable** artifact is a good trade if it makes one idea click. Build the artifact for this one reader and this one topic. Do not build a framework.

The rung-1 rules come from the asd-ste100 skill by Dustin Yuchen Teng (https://github.com/danyuchn/asd-ste100-skill, MIT). That skill writes for an *agent* that parses text. This skill writes for a *human* who must understand. The guarantees about meaning are the same.

Run every Python script and install every Python package through `uv` (`uv run`, `uv tool install`, `uvx`). Do not use bare `python3` or `pip`.

## Step 1: Pick the rung and the strictness

Use what the user asked for:
- "in STE", "plain explanation", "explain this diff" → rung 1
- "diagram", "draw", "visual", "chart the flow" → rung 2
- "HTML", "web page", "interactive", "explorable" → rung 3
- "video", "3b1b", "manim", "animation with narration" → rung 4

If the request does not name a format, pick one. Use rung 1 for a short explanation or a diff. Use rung 3 when the topic has a parameter or a process that a reader can change or step through. State the choice in one line, e.g. `Rung 3 (HTML) — the topic has a parameter you can move.`

**Strictness** is a percent that sets how close the prose is to ASD-STE100. Read it from the request ("80% STE", "full STE100", "light STE"). The default is **80**, because Karpathy found the full standard too stringent for explanation. The value applies to *all* prose the skill writes, including diagram labels, page text and narration.

| Setting | What it enforces |
|---|---|
| 90–100 | All structural rules. Sentences ≤20 words. One word for one meaning (no synonym rotation). Active voice. |
| 70–89 (default 80) | Structural rules. Sentences ≤25 words. No semicolons, phrasal verbs, nominalizations or marketing adjectives. Word choice can vary for readability. |
| 40–69 | Short sentences (≤30 words), no semicolons, no marketing adjectives. Everything else is advice. |
| <40 | Plain-language advice only. |

Details are in `references/ste-rules.md` and `references/strictness-dial.md`. Read `ste-rules.md` before you write rung-1 prose if you do not know the rules well.

## Step 2: Write the outline before you render

Write a short internal outline before you make any artifact:
1. **Core claims.** Three to seven facts the reader must leave with.
2. **The mechanism.** What causes what, in order.
3. **Hedges.** Every "may", "can", "probably" or "it is not known" in the source.
4. **One example.** A concrete case with real numbers or real names from the source.

All rungs render the same outline. This is why the ladder is safe to climb. When the user asks to "see it as a diagram", the facts do not change. Only the form changes. Keep the outline in your reasoning or a scratch file. The user does not need to see it.

**Do not invent facts.** This is the most common way an explanation goes wrong. A diagram needs an arrow label, a page needs a default slider value, a narration needs a transition. The easy fix is to supply a cause, a number or an intent that the source never stated. Do not do that. Use a visibly made-up value only if you mark it ("example value"). If you explain a diff or a document, every claim must point back to a line in it. If the source does not say *why* a change was made, say "the diff does not say why".

**Keep every hedge.** "May be caused by a race condition" must not become "is caused by a race condition" in any rung. A diagram does this with a dashed arrow and a "possible cause" label. A page does it with a caption. A video does it in the narration. Confidence is content.

## Step 3: Render the rung

### Rung 1: STE prose

Write Markdown. Lead with a one-sentence summary. Then use short sections or a numbered list for sequences. Use a table where the reader compares things. Define a technical term once, the first time it appears, and use that same term after that.

Run the linter on the result and fix every hard finding:

```bash
uv run <skill-dir>/scripts/ste-lint.py --strictness 80 explanation.md
```

The linter never flags hedges. Do not "fix" a hedge to pass a length cap. Split the sentence instead.

### Rung 2: Diagram

Read `references/diagram-style.md` first. The house style is a **blueprint overview sheet**. It has a title block, lettered panels (A, B, C…) with one concept each, and a grid reference on the border. Karpathy's post used this style for its own STE100 overview.

- Produce one self-contained `.svg`. Use Mermaid only when the content is a plain flowchart or sequence and nothing else.
- Show the real mechanism. If two boxes connect, the arrow label says what moves between them (a token, a request, a value).
- Labels follow the strictness setting and have ≤6 words. Put longer text in a short "Notes" panel.
- Run the linter on the SVG. It reads the `<text>` elements: `ste-lint.py --strictness 80 diagram.svg`.
- Open the file to check it if a browser or image viewer is available.

### Rung 3: Interactive HTML explainer

Read `references/html-explainer.md` first. Start from `assets/html-explainer-template.html`. It already has a light/dark theme, a layout that works on a phone, and a panel structure.

- One file. Inline CSS and JS. Load a library only if it saves real work (e.g. a math renderer), and only from cdnjs or jsdelivr. The page must still show its text if the CDN fails.
- Put an interaction where it helps understanding. Examples: a slider for a parameter, a step-through for a process, a "before / after" toggle. Every control changes something the reader can see, and a caption says what changed.
- Use real computation, not a faked animation. If the page shows gradient descent, the page runs gradient descent.
- All visible text follows the strictness setting, including captions that JS writes. Run `uv run <skill-dir>/scripts/ste-lint.py --strictness 80 page.html`. It reads the visible text and the prose-like strings in `<script>`.

### Rung 4: Explainer video

Read `references/video-pipeline.md` first. The user asked for a video, so deliver a video file, not only the scripts.

1. Check for Manim: `command -v manim`.
2. Write `narration.md`: the narration in STE prose at the chosen strictness, split into numbered beats. One beat ≈ one animation step.
3. Write the scene with one drawing step per beat. Use the 3Blue1Brown style: dark background, one idea on screen at a time, motion that shows the mechanism.
   - Manim is present → `scene.py`, a Manim Community scene.
   - Manim is absent → `scene_frames.py`, which uses the bundled `scripts/frames.py`. That is a small numpy + Pillow renderer that `uv run` puts in uv's isolated cache. It installs nothing in the system, so it needs no approval. Do not write your own renderer. `frames.py` already does canvas, axes, curves, arrows, text, easing and beat timing.
4. Run `scripts/render_video.sh <dir>`. It makes the voice track (ElevenLabs if `ELEVENLABS_API_KEY` is set, otherwise Piper, a `TTS_CMD` such as Kokoro, or macOS `say`). It renders the scene, combines audio and video with ffmpeg, and prints the renderer and the voice it used.
5. Check the result: pull two or three frames with ffmpeg and look at them. Fix overlaps and empty frames before you deliver.

In the reply, name the renderer and the voice. If they were the fallbacks, say in one line what would sound or look better (Manim, ElevenLabs or Piper) and give the `uv tool install` command. **Do not install tools system-wide or download voice models without asking the user.**

## Step 4: Deliver and offer the next rung

Save artifacts to `explainers/<topic-slug>/` in the current project unless the user names a different place. Use a short slug, e.g. `explainers/gradient-descent/`.

Your reply has three parts and nothing else:
1. The rung line (only if you chose the rung yourself).
2. The explanation (rung 1), or the path to the artifact plus a two-sentence summary of what it shows (rungs 2–4).
3. One final line that offers the next rungs:

```
Next: diagram (2) · HTML (3) · video (4)
```

List only the rungs above the current one. At rung 4, offer a change instead, e.g. `Next: change strictness, or rebuild one scene`.

Do not add a preamble about the skill, a list of the rules you applied, or a closing paragraph. If the user asks why you wrote something a certain way, then explain the rules.

## Boundaries

- This skill explains. It does not rewrite an agent-facing string, so the meaning stays the same in another register. That is the asd-ste100 skill's job.
- This skill does not claim certified ASD-STE100 compliance. It does not reproduce ASD's approved-word dictionary. The standard permits reproduction only with ASD's written authority. Lexical rules are a direction of travel here, not a checked standard.
- Clear form does not fix weak content. If the source does not explain something, say so. Do not fill the gap with a believable mechanism.
- Stop simplifying when the sentence is unambiguous. Shortest is not the goal. Clear is the goal.

## Files

- `references/ste-rules.md`: STE writing rules, adapted from asd-ste100-skill. Includes the scan checklist and the hedge rule.
- `references/strictness-dial.md`: which rules apply at each setting, with one paragraph rendered at 100, 80 and 50.
- `references/diagram-style.md`: blueprint overview-sheet conventions and an SVG skeleton.
- `references/html-explainer.md`: interaction patterns that help understanding, and ones that do not.
- `references/video-pipeline.md`: Manim scene pattern, narration beats, TTS choices, ffmpeg commands.
- `scripts/ste-lint.py`: structural STE linter with `--strictness` and HTML/SVG text extraction. `--selftest` checks it.
- `scripts/render_video.sh`: TTS → Manim or frames.py → ffmpeg pipeline with tool detection.
- `scripts/frames.py`: numpy + Pillow frame renderer for rung 4 when Manim is missing. Runs through `uv run`.
- `assets/html-explainer-template.html`: starting point for rung 3.
