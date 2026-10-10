#!/usr/bin/env bash
# Regression tests for the audio stage of render_video.sh:
#  1. narration timing must not depend on the TTS engine's sample rate
#  2. the beat audio cache re-voices only what changed
#
# Timing bug: Piper / TTS_CMD audio kept its native rate (e.g. 22050 Hz) while the
# 0.4 s pauses were 44100 Hz. The concat demuxer read every pause at the first
# file's rate, so each pause played as 0.8 s and the voice drifted 0.4 s per beat
# behind the picture (5.6 s over 14 beats).
#
# Needs only ffmpeg/ffprobe and uv: a fake engine emits tones at a chosen rate.
# Usage: scripts/test_render_audio.sh   (exit 0 = pass)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0

run_case() {  # name, TTS_CMD
  local name="$1" cmd="$2" dir="$TMP/$1"
  mkdir -p "$dir"
  for i in $(seq 1 14); do echo "$i. Beat number $i says a few words."; done > "$dir/narration.md"
  echo "# test placeholder" > "$dir/scene.py"
  STOP_AFTER_AUDIO=1 TTS=custom TTS_CMD="$cmd" bash "$HERE/render_video.sh" "$dir" >/dev/null
  uv run --no-project --quiet python - "$dir/audio" "$name" <<'PY'
import json, subprocess, sys, pathlib
audio, name = pathlib.Path(sys.argv[1]), sys.argv[2]
probe = lambda f, e: subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", e,
                                              "-of", "default=nw=1:nk=1", str(f)]).decode().split()
expected = sum(json.loads((audio / "durations.json").read_text()).values())
actual = float(probe(audio / "narration.wav", "format=duration")[0])
rate, ch = probe(audio / "narration.wav", "stream=sample_rate,channels")
drift = actual - expected
ok = abs(drift) < 0.05 and rate == "44100" and ch == "1"
print(f"{'PASS' if ok else 'FAIL'} {name}: expected {expected:.2f} s, got {actual:.2f} s, drift {drift:+.2f} s, {rate} Hz x{ch}")
sys.exit(0 if ok else 1)
PY
}

# 1. Piper-like engine: every beat at 22050 Hz.
run_case "all-22050" \
  'ffmpeg -loglevel error -y -f lavfi -i "sine=frequency=440:duration=1.5" -ar 22050 -ac 1 {out}' || fail=1

# 2. Mixed rates: beat 1 at 44100 Hz, the rest at 16000 Hz (would play later beats too fast).
run_case "mixed-44100-16000" \
  'case {in} in *beat-01.txt) r=44100;; *) r=16000;; esac; ffmpeg -loglevel error -y -f lavfi -i "sine=frequency=440:duration=1.5" -ar $r -ac 1 {out}' || fail=1

# ---------------------------------------------------------------------------
# Audio cache: re-voice only what changed. A fake engine logs each call.
CDIR="$TMP/cache"; COUNT="$TMP/calls.log"; mkdir -p "$CDIR"
echo "# test placeholder" > "$CDIR/scene.py"
engine() {  # $1 = tone frequency; a different frequency stands for a different voice
  echo "echo {in} >> '$COUNT'; ffmpeg -loglevel error -y -f lavfi -i \"sine=frequency=$1:duration=1\" -ar 22050 -ac 1 {out}"
}
narrate() { for i in $(seq 1 "$1"); do echo "$i. Beat number $i${2:+ $2}."; done > "$CDIR/narration.md"; }
render() { : > "$COUNT"; STOP_AFTER_AUDIO=1 TTS=custom TTS_CMD="$(engine "$1")" bash "$HERE/render_video.sh" "$CDIR" >/dev/null; wc -l < "$COUNT" | tr -d ' '; }
check() {  # name, got, want
  if [[ "$2" == "$3" ]]; then echo "PASS cache $1: $2"; else echo "FAIL cache $1: got $2, want $3"; fail=1; fi
}

narrate 14;  check "first run voices every beat" "$(render 440)" 14
check "unchanged second run voices nothing" "$(render 440)" 0
sed -i.bak 's/^3\. Beat number 3\./3. Beat number 3, now with new words./' "$CDIR/narration.md" && rm -f "$CDIR/narration.md.bak"
check "one edited beat voices one beat" "$(render 440)" 1
check "a different voice re-voices every beat" "$(render 550)" 14
narrate 10;  render 550 >/dev/null
check "shorter narration: beats in durations.json" \
  "$(uv run --no-project --quiet python -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$CDIR/audio/durations.json")" 10
check "shorter narration: leftover beat files" "$(find "$CDIR/audio" -name 'beat-1[1-4].*' | wc -l | tr -d ' ')" 0

# ---------------------------------------------------------------------------
# Captions: <slug>.vtt follows the narration. Cues come from the beat text and the
# measured beat lengths, so they must end where the narration ends. A long beat
# splits at sentences into cues of about two caption lines.
VDIR="$TMP/captions"; mkdir -p "$VDIR"
echo "# test placeholder" > "$VDIR/scene.py"
{
  echo "1. A *short* beat."
  echo "2. This is the first sentence of a long beat. Here is a second sentence with more words. And a third one ends it."
  echo "3. The last beat."
} > "$VDIR/narration.md"
STOP_AFTER_AUDIO=1 TTS=custom TTS_CMD='ffmpeg -loglevel error -y -f lavfi -i "sine=frequency=440:duration=2" -ar 22050 -ac 1 {out}' \
  bash "$HERE/render_video.sh" "$VDIR" >/dev/null
uv run --no-project --quiet python - "$VDIR" <<'PY' || fail=1
import re, subprocess, sys, pathlib
d = pathlib.Path(sys.argv[1]); vtt = d / "captions.vtt"
def result(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} captions {name}{': ' + detail if detail else ''}")
    return ok
if not result("file written", vtt.exists(), str(vtt.name)):
    sys.exit(1)
text = vtt.read_text(encoding="utf-8")
secs = lambda s: (lambda h, m, x: int(h) * 3600 + int(m) * 60 + float(x))(*s.split(":"))
cues = [(secs(a), secs(b), body.strip()) for a, b, body in
        re.findall(r"(\d\d:\d\d:\d\d\.\d{3}) --> (\d\d:\d\d:\d\d\.\d{3})\n(.+?)(?:\n\n|\Z)", text, re.S)]
narr = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                      "-of", "default=nw=1:nk=1", str(d / "audio" / "narration.wav")]))
ok = all([
    result("header", text.startswith("WEBVTT\n")),
    result("cue count", len(cues) >= 4, f"{len(cues)} cues for 3 beats"),
    result("times move forward", all(a < b for a, b, _ in cues) and all(c[1] <= n[0] + 1e-3 for c, n in zip(cues, cues[1:]))),
    result("ends with the narration", abs(cues[-1][1] - narr) < 0.05, f"last cue {cues[-1][1]:.2f} s, narration {narr:.2f} s"),
    result("markdown removed", "*" not in text and "A short beat." in text),
    result("long beat split", max(len(c[2]) for c in cues) <= 84, f"longest cue {max(len(c[2]) for c in cues)} chars"),
])
sys.exit(0 if ok else 1)
PY

[[ $fail == 0 ]] && echo "all audio tests passed" || { echo "audio tests FAILED"; exit 1; }
