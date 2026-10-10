# Rung 4: explainer video pipeline

Karpathy: "Create a 3b1b style video explainer on X. Use my ElevenLabs API key for audio narration … or you can ask your LLM to find you decent free alternatives that use your local compute."

## Output directory

```
explainers/<slug>/
├── narration.md      # numbered beats in STE prose
├── scene.py          # Manim Community scene, class Explainer (if manim is installed)
├── scene_frames.py   # OR: frames.py scene (no manim needed)
├── audio/            # one WAV/MP3 per beat (made by render_video.sh)
├── <slug>.vtt        # captions, one cue per beat or sentence group (made by render_video.sh)
└── <slug>.mp4        # final video (made by render_video.sh)
```

## 1. Narration beats

`narration.md` is a numbered list. Each item is one beat: one to three STE sentences that go with one animation step. Target 4–8 seconds of speech per beat (about 10–20 words). A full explainer is 8–20 beats.

```markdown
1. A Fourier transform takes a signal and finds the waves that build it.
2. Here is a signal. It looks complex, but it is the sum of two pure tones.
3. …
```

Narration follows the strictness setting, with one more rule: it is heard, not read, so avoid symbols and abbreviations that are hard to say. Write "x squared", not "x^2".

Lint it: `ste-lint.py --strictness 80 narration.md`.

## 2a. Manim scene (when `manim` is on PATH)

Use Manim Community (`uv tool install manim`). One class named `Explainer`. Keep one `self.play(...)` group (plus `self.wait`) per beat, in the same order, with a `# beat N` comment. `render_video.sh` reads the beat audio lengths and writes them to `audio/durations.json`. The scene reads that file so each beat waits for its narration:

```python
from manim import *
import json, pathlib

DUR = json.loads((pathlib.Path(__file__).parent / "audio" / "durations.json").read_text()) \
    if (pathlib.Path(__file__).parent / "audio" / "durations.json").exists() else {}

def hold(scene, beat, used):
    """Wait until beat audio ends. `used` = seconds of animation already played in this beat."""
    scene.wait(max(0.3, DUR.get(str(beat), used + 1.0) - used))

class Explainer(Scene):
    def construct(self):
        # beat 1
        title = Text("Fourier transform", font_size=56)
        self.play(Write(title), run_time=1.5)
        hold(self, 1, 1.5)
        # beat 2
        ...
```

The 3Blue1Brown style:
- Dark background (Manim default), few colors with fixed meanings (e.g. BLUE = signal, YELLOW = the thing that is changing).
- One idea on screen at a time. `FadeOut` the old idea before the next one.
- Motion shows the mechanism: `Transform` one form into the next, a `ValueTracker` for a moving parameter, `always_redraw` for things that depend on it.
- Use `MathTex` only if LaTeX is installed. Otherwise use `Text`. `render_video.sh` reports whether LaTeX is present.

## 2b. Frames scene (when Manim is missing)

`scripts/frames.py` is a small renderer built on numpy and Pillow. `render_video.sh` copies it next to `scene_frames.py` and runs the scene with `uv run --with numpy --with pillow`. uv keeps those packages in its own cache, so this needs no install approval. Use it instead of writing a renderer from scratch.

```python
import frames as F
np = F.np
mv = F.Movie(__file__)          # beat lengths come from audio/durations.json

@mv.beat(1)
def title(c, t):                # c = Canvas (1920x1080 coords), t = beat progress 0..1
    c.text("Fourier transform", (960, 500), size=96, alpha=F.ease(t * 3))
    c.text("how to find the waves inside a signal", (960, 600), size=40, color=F.GREY,
           alpha=F.phase(t, 0.3, 0.6))

@mv.beat(2)
def two_waves(c, t):
    ax = c.axes((160, 240, 1760, 840), x=(0, 2), y=(-2, 2), labels=("time", "value"))
    xs = np.linspace(0, 2, 800)
    c.curve(ax(xs, np.cos(2 * np.pi * 2 * xs)), F.BLUE, partial=F.phase(t, 0.0, 0.5))
    c.curve(ax(xs, np.cos(2 * np.pi * 3 * xs)), F.GREEN, partial=F.phase(t, 0.4, 0.9))

mv.render()                     # writes media/silent.mp4
```

What the API gives you:

| Call | Does |
|---|---|
| `F.ease(x)`, `F.phase(t, a, b)`, `F.lerp(a, b, x)` | Smooth timing. `phase` runs a sub-step from `a` to `b` of the beat. |
| `c.text(s, xy, size, color, alpha, font="sans"/"serif"/"mono", anchor="mm")` | Text. Use `serif` for math-like labels. |
| `c.axes(box, x=(lo,hi), y=(lo,hi), labels=(x,y))` | Draws axes and returns `to_px(xs, ys)` → (N, 2) points |
| `c.curve(pts, color, width, alpha, partial)` | Polyline, with write-on through `partial` |
| `c.line`, `c.arrow`, `c.dot`, `c.circle`, `c.rect` | Primitives. `alpha` fades toward the background. |
| Colors | `F.BLUE`, `F.YELLOW`, `F.RED`, `F.GREEN`, `F.PURPLE`, `F.WHITE`, `F.GREY`, `F.BG` |

Rules:
- Draw each frame from scratch from `t`. Do not keep state between calls. Then any frame can render on its own, and timing changes cannot break the scene.
- Compute the real math with numpy (a real transform, a real descent), the same as rung 3.
- `QUALITY=l` renders 720p at 15 fps for a fast check. Use the default `h` (1080p, 30 fps) for the final video.
- Check the result: `ffmpeg -ss <sec> -i <slug>.mp4 -frames:v 1 check.png`, then look at the image.

## 3. Voice (TTS)

`render_video.sh` picks the first one that is available:

| Order | Engine | Condition | Notes |
|---|---|---|---|
| 1 | ElevenLabs | `ELEVENLABS_API_KEY` is set | Best quality. Costs money. Voice from `ELEVENLABS_VOICE_ID` (default: Rachel, `21m00Tcm4TlvDq8NUfJ`). |
| 2 | Piper | `piper` on PATH and `PIPER_MODEL` points to a `.onnx` voice | Free, local, good quality. |
| 3 | Any local CLI (e.g. Kokoro) | `TTS_CMD` is set, with `{in}` (text file) and `{out}` (wav) placeholders | Free, local. Quality depends on the model. |
| 4 | macOS `say` | macOS | Free. Robotic, but always present on a Mac. |

Tell the user which engine produced the audio. If it fell back to `say`, mention that Piper or Kokoro sounds much better and give the install command. Do not install them without asking.

## 4. Render and combine

`scripts/render_video.sh explainers/<slug>` does this:
1. Checks for `uv`, `ffmpeg`, `ffprobe` and a TTS engine. If one is missing, it prints the install command and exits with code 2.
2. Writes one audio file per beat into `audio/`, and `audio/durations.json`. A beat is voiced again only when its text or the voice settings change. `beat-NN.key` holds a hash of both. Beats removed from `narration.md` are deleted. So after you edit one beat, a re-render voices only that beat.
3. Converts every beat to 44100 Hz mono. Engines differ (Piper is often 22050 Hz). Mixed rates would make the pauses play at the wrong length and the voice would drift behind the picture. After the join, the script stops with an error if the narration length does not match the beat timing.
4. Joins the beat audio into `audio/narration.wav`. It also writes `<slug>.vtt`, a WebVTT captions file. The cues use the same measured beat lengths as the picture, so beat edges are exact. A long beat splits at sentences into cues of about two caption lines. Inside a beat, each cue gets time in proportion to its text length.
5. Renders the scene: `manim -qh scene.py Explainer` if Manim is present and `scene.py` exists. Otherwise it runs `scene_frames.py` through uv. `QUALITY=l` gives a fast draft.
6. Combines video and audio with ffmpeg into `<slug>.mp4`, and prints the renderer and the voice.

`scripts/test_render_audio.sh` tests the audio stage (sample-rate timing, the cache and the captions) with ffmpeg and uv only.

Install commands (macOS), for the user to approve:
```bash
brew install ffmpeg            # if missing
uv tool install manim          # needs cairo/pango: brew install cairo pango pkg-config
brew install --cask mactex-no-gui   # only if the scene needs MathTex
uv tool install piper-tts      # optional better local voice, plus a .onnx voice model
```

## When tools are missing

Missing Manim is not a reason to stop. Use the frames path and deliver a video. Only a missing `ffmpeg` or `uv` blocks the video. In that case, deliver `narration.md` and the scene, state what is missing, and give the exact command. Do not claim a video exists when it does not.

## 5. Captions on a web page

Ship `<slug>.vtt` next to the MP4. In a rung-3 page, add a `<track>` inside the `<video>`, so that a reader with the sound off can follow the narration:

```html
<video controls preload="metadata" playsinline>
  <source src="video/<slug>.mp4" type="video/mp4">
  <track kind="captions" src="video/<slug>.vtt" srclang="en" label="English" default>
</video>
```

`default` shows the captions at once. The reader turns them off in the player. The page must come from a web server: a browser does not load a track from a `file://` page. Keep the captions as a track, not burned into the picture. A track is real text, so screen readers and search can use it.
