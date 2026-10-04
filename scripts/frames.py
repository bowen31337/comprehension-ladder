# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow"]
# ///
"""Tiny 3Blue1Brown-style frame renderer: the no-Manim path for rung 4.

`uv run` puts numpy + Pillow in uv's isolated cache. Nothing goes into the
system Python, so no install approval is needed. render_video.sh copies this
file next to scene_frames.py, so the explainer folder runs on its own.

A scene is one function per narration beat. The function gets a Canvas and t,
the progress through the beat from 0 to 1. Beat length comes from
audio/durations.json, so the picture stays in step with the voice.

    import frames as F
    mv = F.Movie(__file__)

    @mv.beat(1)
    def title(c, t):
        c.text("Fourier transform", (960, 500), size=96, alpha=F.ease(t * 3))

    @mv.beat(2)
    def wave(c, t):
        ax = c.axes((160, 240, 1760, 840), x=(0, 4), y=(-2, 2))
        xs = F.np.linspace(0, 4, 800)
        c.curve(ax(xs, F.np.sin(2 * F.np.pi * xs)), F.BLUE, partial=F.ease(t * 2))

    mv.render()   # writes media/silent.mp4

Coordinates are always in a 1920x1080 space, whatever the output size.
"""
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 3b1b-like palette: fixed meanings per color are the scene author's job.
BG = "#0e1116"
WHITE = "#ece9e1"
GREY = "#8a8f98"
BLUE = "#58c4dd"
YELLOW = "#f4d35e"
RED = "#fc6255"
GREEN = "#83c167"
PURPLE = "#b48ead"

W, H = 1920, 1080
QUALITY = {"l": (1280, 720, 1, 15), "m": (1280, 720, 2, 30), "h": (1920, 1080, 2, 30)}

FONT_CANDIDATES = {
    "sans": ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"],
    "serif": ["/System/Library/Fonts/Supplemental/Times New Roman.ttf", "/System/Library/Fonts/Times.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "C:/Windows/Fonts/times.ttf"],
    "mono": ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "C:/Windows/Fonts/consola.ttf"],
}
_font_cache = {}


def ease(t):
    """Smoothstep on t clamped to [0, 1]. Use ease(t * k) to finish early in a beat."""
    t = min(1.0, max(0.0, float(t)))
    return t * t * (3 - 2 * t)


def phase(t, start, end):
    """Progress of a sub-step that runs from `start` to `end` of the beat (both 0..1)."""
    return ease((t - start) / max(1e-6, end - start))


def lerp(a, b, t):
    return a + (b - a) * t


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _font(kind, px):
    key = (kind, px)
    if key not in _font_cache:
        for path in FONT_CANDIDATES.get(kind, []) + FONT_CANDIDATES["sans"]:
            if os.path.exists(path):
                _font_cache[key] = ImageFont.truetype(path, px)
                break
        else:
            _font_cache[key] = ImageFont.load_default(size=px)
    return _font_cache[key]


class Canvas:
    """Draws in 1920x1080 coordinates onto a supersampled Pillow image."""

    def __init__(self, width, height, ss):
        self.k = width * ss / W
        self.size = (width, height)
        self.img = Image.new("RGB", (width * ss, height * ss), BG)
        self.d = ImageDraw.Draw(self.img)
        self.bg = _rgb(BG)

    def _c(self, color, alpha):
        # The background is flat, so alpha = blend toward it. Much faster than layers.
        r = _rgb(color)
        a = min(1.0, max(0.0, alpha))
        return tuple(int(self.bg[i] + (r[i] - self.bg[i]) * a) for i in range(3))

    def _p(self, xy):
        return (xy[0] * self.k, xy[1] * self.k)

    def clear(self, color=BG):
        self.d.rectangle((0, 0) + self.img.size, fill=color)

    def text(self, s, xy, size=48, color=WHITE, alpha=1.0, font="sans", anchor="mm"):
        if alpha <= 0:
            return
        self.d.text(self._p(xy), s, fill=self._c(color, alpha),
                    font=_font(font, int(size * self.k)), anchor=anchor)

    def line(self, p0, p1, color=WHITE, width=4, alpha=1.0):
        if alpha > 0:
            self.d.line([self._p(p0), self._p(p1)], fill=self._c(color, alpha), width=max(1, int(width * self.k)))

    def curve(self, pts, color=WHITE, width=5, alpha=1.0, partial=1.0):
        """Polyline through an (N, 2) array. `partial` draws the first fraction (write-on effect)."""
        pts = np.asarray(pts, float)
        n = int(round(len(pts) * min(1.0, max(0.0, partial))))
        if n < 2 or alpha <= 0:
            return
        flat = [tuple(p) for p in pts[:n] * self.k]
        self.d.line(flat, fill=self._c(color, alpha), width=max(1, int(width * self.k)), joint="curve")

    def dot(self, xy, r=10, color=YELLOW, alpha=1.0):
        if alpha > 0:
            x, y = self._p(xy)
            rr = r * self.k
            self.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=self._c(color, alpha))

    def circle(self, xy, r, color=WHITE, width=3, alpha=1.0):
        if alpha > 0:
            x, y = self._p(xy)
            rr = r * self.k
            self.d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=self._c(color, alpha),
                           width=max(1, int(width * self.k)))

    def arrow(self, p0, p1, color=WHITE, width=4, head=18, alpha=1.0):
        if alpha <= 0:
            return
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        v = p1 - p0
        length = np.hypot(*v)
        if length < 1e-6:
            return
        u = v / length
        h = min(head, length * 0.5)
        base = p1 - u * h
        perp = np.array([-u[1], u[0]]) * h * 0.5
        self.line(p0, base, color, width, alpha)
        self.d.polygon([self._p(p1), self._p(base + perp), self._p(base - perp)], fill=self._c(color, alpha))

    def rect(self, box, color=WHITE, width=3, fill=None, alpha=1.0):
        if alpha > 0:
            b = [v * self.k for v in box]
            self.d.rectangle(b, outline=self._c(color, alpha), width=max(1, int(width * self.k)),
                             fill=self._c(fill, alpha) if fill else None)

    def axes(self, box, x, y, color=GREY, alpha=1.0, ticks=True, labels=None):
        """Draw axes in `box` (x0, y0, x1, y1) for data ranges x=(lo, hi), y=(lo, hi).
        Returns a function f(xs, ys) -> (N, 2) pixel points, for curve()/dot()."""
        x0, y0, x1, y1 = box

        def to_px(xs, ys):
            xs, ys = np.asarray(xs, float), np.asarray(ys, float)
            px = x0 + (xs - x[0]) / (x[1] - x[0]) * (x1 - x0)
            py = y1 - (ys - y[0]) / (y[1] - y[0]) * (y1 - y0)
            return np.stack([px, py], axis=-1)

        zero_y = to_px(x[0], min(max(0, y[0]), y[1]))[1]
        zero_x = to_px(min(max(0, x[0]), x[1]), y[0])[0]
        self.arrow((x0, zero_y), (x1 + 20, zero_y), color, 3, 14, alpha)
        self.arrow((zero_x, y1), (zero_x, y0 - 20), color, 3, 14, alpha)
        if ticks:
            for v in range(int(np.ceil(x[0])), int(np.floor(x[1])) + 1):
                if v == 0:
                    continue
                px = to_px(v, 0)[0]
                self.line((px, zero_y - 8), (px, zero_y + 8), color, 2, alpha)
                self.text(str(v), (px, zero_y + 30), 26, color, alpha)
        if labels:
            self.text(labels[0], (x1 + 40, zero_y), 30, color, alpha, anchor="lm")
            self.text(labels[1], (zero_x + 16, y0 - 20), 30, color, alpha, anchor="lm")
        return to_px

    def frame(self):
        return self.img.resize(self.size, Image.Resampling.LANCZOS) if self.img.size != self.size else self.img


class Movie:
    """Collects beat functions and renders them to media/silent.mp4 through ffmpeg."""

    def __init__(self, scene_file, quality=None):
        self.dir = pathlib.Path(scene_file).resolve().parent
        q = quality or os.environ.get("QUALITY", "h")
        self.width, self.height, self.ss, self.fps = QUALITY.get(q, QUALITY["h"])
        dur_file = self.dir / "audio" / "durations.json"
        self.durations = {int(k): v for k, v in json.loads(dur_file.read_text()).items()} if dur_file.exists() else {}
        self.beats = {}

    def beat(self, n, seconds=None):
        """Register a beat. Length: audio/durations.json, else `seconds`, else 4 s."""
        def wrap(fn):
            self.beats[n] = (fn, seconds)
            return fn
        return wrap

    def render(self, out=None):
        out = pathlib.Path(out or self.dir / "media" / "silent.mp4")
        out.parent.mkdir(parents=True, exist_ok=True)
        numbers = sorted(set(self.beats) | set(self.durations))
        missing = [n for n in self.durations if n not in self.beats]
        if missing:
            print(f"note: beats {missing} have audio but no draw function; they hold the previous picture")
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{self.width}x{self.height}", "-r", str(self.fps), "-i", "-",
                               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)],
                              stdin=subprocess.PIPE)
        assert ff.stdin is not None
        last, total = None, 0
        for n in numbers:
            fn, sec = self.beats.get(n, (last, None))
            seconds = self.durations.get(n, sec or 4.0)
            frames = max(1, int(round(seconds * self.fps)))
            for i in range(frames):
                c = Canvas(self.width, self.height, self.ss)
                if fn:
                    fn(c, i / max(1, frames - 1))
                ff.stdin.write(c.frame().tobytes())
            last, total = fn, total + frames
            print(f"beat {n}: {seconds:.1f} s", file=sys.stderr)
        ff.stdin.close()
        if ff.wait() != 0:
            sys.exit("ffmpeg failed")
        print(f"silent video: {out} ({total / self.fps:.1f} s)")
        return out
