#!/usr/bin/env bash
# Render a comprehension-ladder rung-4 explainer:
#   narration.md (numbered beats) -> per-beat audio -> scene -> <slug>.mp4
#   scene: manim scene.py if manim is installed, else scene_frames.py via frames.py
#   (numpy + Pillow in uv's isolated cache: no system install)
#
# Usage: render_video.sh <explainer-dir>
#   QUALITY=l|m|h   render quality (default h; l is a fast draft)
#   SLUG=name       output file name (default: the folder name)
#   TTS=elevenlabs|piper|custom|say   force an engine (default: first available)
#   ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID   ElevenLabs (paid, best quality)
#   PIPER_MODEL=/path/voice.onnx               Piper (free, local)
#   TTS_CMD='kokoro -t "$(cat {in})" -o {out}' any local CLI; {in}=text file, {out}=wav
#
# Exit codes: 0 video written, 2 a required tool is missing (audio may exist).
# Installs nothing. Prints install commands for the user to approve.
set -euo pipefail

DIR="${1:?usage: render_video.sh <explainer-dir>}"
DIR="$(cd "$DIR" && pwd)"
SLUG="${SLUG:-$(basename "$DIR")}"   # override with SLUG=topic-name when the folder name is generic
QUALITY="${QUALITY:-h}"
[[ -f "$DIR/narration.md" ]] || { echo "missing $DIR/narration.md"; exit 1; }
[[ -f "$DIR/scene.py" || -f "$DIR/scene_frames.py" ]] || { echo "missing $DIR/scene.py or scene_frames.py"; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

have uv || { echo "MISSING: uv. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 2; }
PY=(uv run --no-project --quiet python)

if ! have ffmpeg || ! have ffprobe; then
  echo "MISSING: ffmpeg. Install: brew install ffmpeg   (Linux: apt install ffmpeg)"
  exit 2
fi

# --- pick TTS engine --------------------------------------------------------
pick_tts() {
  if [[ -n "${TTS:-}" ]]; then echo "$TTS"; return; fi
  if [[ -n "${ELEVENLABS_API_KEY:-}" ]]; then echo elevenlabs; return; fi
  if have piper && [[ -n "${PIPER_MODEL:-}" && -f "${PIPER_MODEL}" ]]; then echo piper; return; fi
  if [[ -n "${TTS_CMD:-}" ]]; then echo custom; return; fi
  if have say; then echo say; return; fi
  echo none
}
ENGINE="$(pick_tts)"
if [[ "$ENGINE" == none ]]; then
  echo "MISSING: a TTS engine. Options:"
  echo "  export ELEVENLABS_API_KEY=...            (paid, best quality)"
  echo "  uv tool install piper-tts && export PIPER_MODEL=/path/en_US-lessac-medium.onnx"
  exit 2
fi
echo "TTS engine: $ENGINE"

# --- split narration.md into beats ------------------------------------------
AUDIO="$DIR/audio"
mkdir -p "$AUDIO"
"${PY[@]}" - "$DIR/narration.md" "$AUDIO" <<'PY'
import re, sys, pathlib
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
beats, cur = {}, None
for line in src.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
    if m:
        cur = int(m.group(1)); beats[cur] = m.group(2).strip()
    elif cur is not None and line.strip() and not line.lstrip().startswith("#"):
        beats[cur] += " " + line.strip()
    elif not line.strip():
        cur = None
if not beats:
    sys.exit("narration.md has no numbered beats (1. ..., 2. ...)")
for n, text in beats.items():
    text = re.sub(r"[*_`]", "", text)  # drop markdown emphasis before speech
    (out / f"beat-{n:02d}.txt").write_text(text + "\n", encoding="utf-8")
# A shorter narration must not leave old beats behind: later steps glob beat-*.
stale = [f for f in out.glob("beat-*") if int(f.name[5:7]) not in beats]
for f in stale:
    f.unlink()
print(f"{len(beats)} beats" + (f", removed {len(stale)} stale files" if stale else ""))
PY

# --- synthesize each beat ----------------------------------------------------
# Cache: beat-NN.key holds a hash of the voice settings and the beat text. A beat
# is voiced again only when that hash changes (edited text, or another engine or
# voice). Timestamps cannot work here: the splitter rewrites every .txt each run.
case "$ENGINE" in
  elevenlabs) VOICE_DESC="elevenlabs|${ELEVENLABS_VOICE_ID:-21m00Tcm4TlvDq8NUfJ}|eleven_multilingual_v2" ;;
  piper)      VOICE_DESC="piper|$PIPER_MODEL" ;;
  custom)     VOICE_DESC="custom|$TTS_CMD" ;;
  say)        VOICE_DESC="say" ;;
esac
sha() { if have sha256sum; then sha256sum; else shasum -a 256; fi | cut -d' ' -f1; }
voiced=0
for txt in "$AUDIO"/beat-*.txt; do
  wav="${txt%.txt}.wav"; keyf="${txt%.txt}.key"
  key="$( { printf '%s\n' "$VOICE_DESC"; cat "$txt"; } | sha)"
  [[ -f "$wav" && -f "$keyf" && "$(cat "$keyf")" == "$key" ]] && continue
  rm -f "$keyf"
  voiced=$((voiced + 1))
  case "$ENGINE" in
    elevenlabs)
      voice="${ELEVENLABS_VOICE_ID:-21m00Tcm4TlvDq8NUfJ}"
      body="$("${PY[@]}" -c 'import json,sys;print(json.dumps({"text":open(sys.argv[1]).read().strip(),"model_id":"eleven_multilingual_v2"}))' "$txt")"
      curl -sS -f -X POST "https://api.elevenlabs.io/v1/text-to-speech/$voice" \
        -H "xi-api-key: $ELEVENLABS_API_KEY" -H "Content-Type: application/json" \
        -d "$body" -o "${txt%.txt}.mp3"
      ffmpeg -loglevel error -y -i "${txt%.txt}.mp3" -ar 44100 -ac 1 "$wav" ;;
    piper)
      piper --model "$PIPER_MODEL" --output_file "$wav" < "$txt" >/dev/null 2>&1 ;;
    custom)
      cmd="${TTS_CMD//\{in\}/$txt}"; cmd="${cmd//\{out\}/$wav}"
      bash -c "$cmd" ;;
    say)
      say -o "${txt%.txt}.aiff" -f "$txt"
      ffmpeg -loglevel error -y -i "${txt%.txt}.aiff" -ar 44100 -ac 1 "$wav"
      rm -f "${txt%.txt}.aiff" ;;
  esac
  [[ -s "$wav" ]] && printf '%s\n' "$key" > "$keyf"   # only after a successful voice
done
echo "voiced $voiced beat(s), reused the rest from the cache"

# --- one canonical format for every clip -------------------------------------
# The concat demuxer below takes its stream format from the first file and reads
# every later file as if it had that format. Engines differ (Piper voices are
# often 22050 Hz, custom TTS_CMD output can be anything), so a 44100 Hz pause
# after a 22050 Hz beat played as 0.8 s instead of 0.4 s and the voice drifted
# behind the picture. Convert every beat, new or cached, to the format the pauses use.
CANON="pcm_s16le,44100,1"
for wav in "$AUDIO"/beat-*.wav; do
  fmt="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of csv=p=0 "$wav")"
  if [[ "$fmt" != "$CANON" ]]; then
    ffmpeg -loglevel error -y -i "$wav" -c:a pcm_s16le -ar 44100 -ac 1 "$wav.tmp.wav" && mv "$wav.tmp.wav" "$wav"
  fi
done

# --- durations + joined narration -------------------------------------------
"${PY[@]}" - "$AUDIO" <<'PY'
import json, pathlib, subprocess, sys
audio = pathlib.Path(sys.argv[1])
dur, lines = {}, []
for wav in sorted(audio.glob("beat-*.wav")):
    n = int(wav.stem.split("-")[1])
    s = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "default=nw=1:nk=1", str(wav)]).strip())
    dur[str(n)] = round(s + 0.4, 2)  # 0.4 s breath between beats
    lines.append(f"file '{wav.name}'\nduration {s:.3f}\nfile 'silence.wav'")
(audio / "durations.json").write_text(json.dumps(dur, indent=2))
(audio / "concat.txt").write_text("\n".join(lines) + "\n")
print(f"narration: {sum(dur.values()):.1f} s over {len(dur)} beats")
PY
ffmpeg -loglevel error -y -f lavfi -i anullsrc=r=44100:cl=mono -t 0.4 -c:a pcm_s16le "$AUDIO/silence.wav"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$AUDIO/concat.txt" -ar 44100 -ac 1 "$AUDIO/narration.wav"
# Guard: the picture is timed from durations.json, so the joined narration must
# match it. A mismatch means a clip format slipped through, so stop instead of drifting.
"${PY[@]}" - "$AUDIO" <<'PY'
import json, pathlib, subprocess, sys
audio = pathlib.Path(sys.argv[1])
expected = sum(json.loads((audio / "durations.json").read_text()).values())
actual = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                        "-of", "default=nw=1:nk=1", str(audio / "narration.wav")]))
if abs(actual - expected) > 0.1:
    sys.exit(f"ERROR: narration is {actual:.2f} s but the beats add up to {expected:.2f} s "
             f"({actual - expected:+.2f} s). Voice and picture would drift. Check the beat clip formats.")
PY
echo "audio: $AUDIO/narration.wav"
[[ "${STOP_AFTER_AUDIO:-}" == 1 ]] && exit 0   # test hook: audio stage only

# --- render scene ------------------------------------------------------------
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$DIR/scene.py" ]] && have manim; then
  RENDERER=manim
  if ! have latex; then
    echo "note: LaTeX not found. MathTex/Tex will fail. Use Text, or: brew install --cask mactex-no-gui"
  fi
  ( cd "$DIR" && manim -q"$QUALITY" --media_dir "$DIR/media" scene.py Explainer )
  VIDEO="$(find "$DIR/media/videos" -name 'Explainer.mp4' -newer "$AUDIO/narration.wav" | head -1)"
  [[ -n "$VIDEO" ]] || { echo "manim produced no Explainer.mp4"; exit 1; }
elif [[ -f "$DIR/scene_frames.py" ]]; then
  RENDERER=frames
  cp "$HERE/frames.py" "$DIR/frames.py"   # keep the explainer folder self-contained
  ( cd "$DIR" && QUALITY="$QUALITY" uv run --no-project --quiet --with numpy --with pillow python scene_frames.py )
  VIDEO="$DIR/media/silent.mp4"
  [[ -f "$VIDEO" ]] || { echo "scene_frames.py produced no media/silent.mp4"; exit 1; }
else
  echo "MISSING: manim, and there is no scene_frames.py fallback."
  echo "Either write scene_frames.py (see references/video-pipeline.md), or install manim:"
  echo "  uv tool install manim   (macOS also: brew install cairo pango pkg-config)"
  echo "Audio is ready. Run this script again after that."
  exit 2
fi

# --- combine -----------------------------------------------------------------
ffmpeg -loglevel error -y -i "$VIDEO" -i "$AUDIO/narration.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k "$DIR/$SLUG.mp4"
echo "video: $DIR/$SLUG.mp4  (renderer: $RENDERER, voice: $ENGINE)"
