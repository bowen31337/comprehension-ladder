The comprehension-ladder skill takes one thing you want to understand and turns it into one of four formats. Each format shows the same facts.

## The four rungs

| Rung | What you get | Best for |
|---|---|---|
| 1. STE prose | Markdown in Simplified Technical English | Short explanations, diffs |
| 2. Diagram | One SVG sheet with lettered panels | Structure, flows, incidents |
| 3. Web page | One interactive HTML file | Topics with a parameter you can move |
| 4. Video | A narrated MP4 | Topics that change over time |

**Simplified Technical English (STE)** is a controlled language from aircraft maintenance manuals. It uses short sentences, active verbs and one idea per sentence. Its rules make text hard to misread.

## What happens when you ask

1. **Claude reads the skill description.** The description tells Claude to load the skill when the main job is to help a person understand something. Words such as "STE", "diagram", "HTML explainer" or "video" make this very likely. A plain "explain X" may not load the skill, because Claude often answers that kind of request directly.
2. **The skill picks a rung.** It takes the format you name. If you name none, it picks rung 1 for a short explanation and rung 3 for a topic with a parameter. It states its choice in one line.
3. **The skill picks a strictness.** Strictness is a percent that sets how close the prose is to full STE. The default is 80, because Karpathy found the full standard too strict for explanation. At 80, sentences have 25 words or fewer, with no semicolons and no marketing words.
4. **The skill writes an outline first.** The outline lists the core claims, the mechanism, every hedge in the source, and one real example. All four rungs use this one outline. So when you climb from prose to a diagram, the form changes but the facts stay the same.
5. **The skill makes the artifact.** Each rung has its own rules in a reference file.
6. **A linter checks the text.** `ste-lint.py` checks sentence length, semicolons, phrasal verbs and similar rules. It reads Markdown, the text in an SVG, and the captions in an HTML page.
7. **The reply ends with an offer.** The last line names the rungs above the current one, for example `Next: diagram (2) · HTML (3) · video (4)`.

## Two rules that protect meaning

**Keep every hedge.** A hedge is a word that shows doubt, such as "may" or "could". In the test incident note, the cause "may be caused by a race condition". The diagram drew that cause with a dashed red line and the label "may be". It did not state the race condition as fact.

**Add no facts.** If the source does not say why something happened, the explanation says so. In the test diff, the reply said "The diff does not say why the authors made these changes." Example numbers get the label "example value".

## How the video works without heavy tools

The video rung needs a renderer, a voice and ffmpeg.

- If Manim is installed, the skill uses it.
- If Manim is not installed, the skill uses `frames.py`. This small renderer draws each frame with numpy and Pillow. `uv run` keeps those packages in its own cache, so nothing goes into the system Python.
- The voice is the first one available: ElevenLabs (with an API key), Piper, a command you set in `TTS_CMD`, or macOS `say`.
- `render_video.sh` makes the audio for each narration beat, then times each scene to its beat.

In the tests, this path made a 1 minute 43 second Fourier video with no installs.

## Limits

- The linter checks only the form of the text. It cannot tell if an explanation is true. The skill relies on the outline and the two rules for that.
- The skill does not include the official STE dictionary, because ASD does not permit others to copy it. Word choice is a direction, not a checked rule.
- A caption that the page builds from many small pieces of code can pass the linter without a check.
- The skill does not rewrite text for other agents to read. The asd-ste100 skill does that job.

Next: diagram (2) · HTML (3) · video (4)
