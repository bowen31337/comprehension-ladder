# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow"]
# ///
"""Rung 4: how the comprehension-ladder skill works. One draw function per narration beat.

Render from the repo root (render_video.sh copies scripts/frames.py next to this file):
    SLUG=comprehension-ladder-how-it-works scripts/render_video.sh examples/how-it-works/video
"""
import frames as F

np = F.np
mv = F.Movie(__file__)

BLUE, YEL, RED, GRN, WHITE, GREY = F.BLUE, F.YELLOW, F.RED, F.GREEN, F.WHITE, F.GREY
RUNGS = ["1  STE prose", "2  diagram", "3  web page", "4  video"]


def dashed(c, p0, p1, color, width=4, dash=18, gap=12, alpha=1.0, partial=1.0):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    v = p1 - p0
    length = np.hypot(*v) * partial
    u = v / max(1e-6, np.hypot(*v))
    s = 0.0
    while s < length:
        e = min(s + dash, length)
        c.line(p0 + u * s, p0 + u * e, color, width, alpha)
        s += dash + gap


def box(c, x, y, w, h, color=WHITE, alpha=1.0, fill=None, dash=False, width=3):
    if dash:
        for a, b in (((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)), ((x + w, y + h), (x, y + h)), ((x, y + h), (x, y))):
            dashed(c, a, b, color, width, alpha=alpha)
    else:
        c.rect((x, y, x + w, y + h), color, width, fill=fill, alpha=alpha)


def ladder(c, t, lit=None, x0=660, x1=1260, top=200, step=170, alpha=1.0):
    """Rails + four rungs, rung 1 at the bottom. `t` controls how many rungs are drawn."""
    bottom = top + step * 3 + 60
    c.line((x0, top - 40), (x0, bottom), WHITE, 6, alpha)
    c.line((x1, top - 40), (x1, bottom), WHITE, 6, alpha)
    for i, name in enumerate(RUNGS):
        a = F.phase(t, 0.1 + i * 0.18, 0.25 + i * 0.18) * alpha
        y = top + step * (3 - i)
        col = YEL if lit == i else (BLUE if lit is None or lit == "all" else GREY)
        c.line((x0, y), (x1, y), col, 6, a)
        c.text(name, ((x0 + x1) / 2, y - 34), 44, col, a)


# 1 ---------------------------------------------------------------------------
@mv.beat(1)
def title(c, t):
    c.text("Comprehension Ladder", (960, 470), 104, WHITE, F.ease(t * 3))
    c.text("how the skill works", (960, 580), 46, GREY, F.phase(t, 0.25, 0.5))
    c.line((660, 650), (F.lerp(660, 1260, F.phase(t, 0.4, 0.8)), 650), BLUE, 4)


# 2 ---------------------------------------------------------------------------
@mv.beat(2)
def four_rungs(c, t):
    lit = 3 if t > 0.82 else None
    ladder(c, t, lit=lit)
    if t > 0.82:
        c.arrow((1420, 200 - 34), (1290, 200 - 34), YEL, 5, 22, F.phase(t, 0.82, 0.95))
        c.text("you are here", (1540, 166), 36, YEL, F.phase(t, 0.82, 0.95))


# 3 ---------------------------------------------------------------------------
@mv.beat(3)
def pick_rung(c, t):
    a = F.ease(t * 4)
    box(c, 140, 420, 560, 130, WHITE, a)
    c.text('"explain this diff"', (420, 485), 40, WHITE, a, font="mono")
    c.arrow((720, 485), (F.lerp(720, 1000, F.phase(t, 0.25, 0.5)), 485), GREY, 4, 20, F.phase(t, 0.25, 0.5))
    c.text("reads your words", (860, 450), 28, GREY, F.phase(t, 0.3, 0.5))
    ladder(c, 1.0, lit=0 if t > 0.55 else "none", x0=1060, x1=1700, top=230, step=140, alpha=F.phase(t, 0.35, 0.55))


# 4 ---------------------------------------------------------------------------
@mv.beat(4)
def strictness(c, t):
    c.text("strictness", (960, 300), 54, WHITE, F.ease(t * 4))
    x0, x1, y = 360, 1560, 540
    c.line((x0, y), (x1, y), GREY, 6, F.ease(t * 4))
    for v in (0, 40, 70, 90, 100):
        px = F.lerp(x0, x1, v / 100)
        c.line((px, y - 16), (px, y + 16), GREY, 3, F.ease(t * 4))
        c.text(f"{v}%", (px, y + 50), 30, GREY, F.ease(t * 4))
    k = F.phase(t, 0.25, 0.75)
    px = F.lerp(x0, F.lerp(x0, x1, 0.8), k)
    c.line((x0, y), (px, y), BLUE, 10)
    c.dot((px, y), 20, YEL)
    c.text(f"{int(round(80 * k))}%", (px, y - 60), 52, YEL)
    c.text("default: 80% of the way to STE", (960, 760), 40, BLUE, F.phase(t, 0.7, 0.9))


# 5 ---------------------------------------------------------------------------
@mv.beat(5)
def sentence_cap(c, t):
    bands = [("90-100%", 20), ("70-89%", 25), ("40-69%", 30), ("0-39%", 35)]
    for i, (lab, cap) in enumerate(bands):
        y = 250 + i * 110
        a = F.phase(t, i * 0.08, i * 0.08 + 0.2)
        col = YEL if cap == 25 else GREY
        c.text(lab, (380, y), 36, col, a, anchor="rm")
        c.rect((420, y - 22, 420 + cap * 30, y + 22), col, 3, fill=(col if cap == 25 else None), alpha=a * (0.9 if cap == 25 else 0.6))
        c.text(f"{cap} words", (440 + cap * 30, y), 34, col, a, anchor="lm")
    # a sentence as word dots, filling up to the cap of 25
    n = int(F.phase(t, 0.45, 0.9) * 28)
    for i in range(n):
        x = 300 + i * 46
        c.dot((x, 820), 13, GRN if i < 25 else RED)
    if n > 25:
        c.text("word 26: split the sentence", (1590, 880), 32, RED, F.phase(t, 0.88, 0.97), anchor="rm")


# 6 ---------------------------------------------------------------------------
OUTLINE = ["1  core claims", "2  mechanism, in order", "3  every hedge", "4  one real example"]


def outline_box(c, x, y, t=1.0, alpha=1.0, size=40):
    box(c, x, y, 620, 420, BLUE, alpha, width=5)
    c.text("OUTLINE", (x + 310, y + 60), size + 6, BLUE, alpha, font="mono")
    for i, s in enumerate(OUTLINE):
        c.text(s, (x + 60, y + 140 + i * 70), size, GRN if i == 2 else WHITE,
               alpha * F.phase(t, 0.15 + i * 0.15, 0.3 + i * 0.15), anchor="lm")


@mv.beat(6)
def outline(c, t):
    c.text("first, one outline", (960, 170), 50, GREY, F.ease(t * 4))
    outline_box(c, 650, 300, t, F.ease(t * 5))


# 7 ---------------------------------------------------------------------------
@mv.beat(7)
def same_facts(c, t):
    outline_box(c, 120, 330, 1.0, 1.0, size=34)
    for i, name in enumerate(RUNGS):
        y = 250 + i * 190
        a = F.phase(t, 0.1 + i * 0.12, 0.25 + i * 0.12)
        p = np.array([[740, 540], [960, 540], [1080, y + 40], [1200, y + 40]])
        xs = np.linspace(0, 1, 60)
        # quadratic-ish blend for a smooth fan-out curve
        pts = np.stack([np.interp(xs, [0, .45, .8, 1], p[:, 0]), np.interp(xs, [0, .45, .8, 1], p[:, 1])], -1)
        c.curve(pts, GREY, 4, partial=a)
        box(c, 1210, y, 460, 80, WHITE, a)
        c.text(name, (1440, y + 40), 38, WHITE, a)
    c.text("form changes, facts stay", (960, 1000), 44, YEL, F.phase(t, 0.7, 0.9))


# 8 ---------------------------------------------------------------------------
@mv.beat(8)
def keep_hedge(c, t):
    c.text("rule 1: keep every hedge", (960, 180), 56, WHITE, F.ease(t * 4))
    a = F.phase(t, 0.15, 0.35)
    cw = 0.602 * 46                      # monospace advance at size 46
    quote = '"may be caused by a race condition"'
    x0 = 960 - len(quote) * cw / 2
    c.text("source:", (x0 - 30, 380), 36, GREY, a, anchor="rm")
    c.text(quote, (x0, 380), 46, WHITE, a, font="mono", anchor="lm")
    c.text("may", (x0 + cw, 380), 46, GRN, a, font="mono", anchor="lm")   # same glyphs, hedge colour
    k = F.phase(t, 0.4, 0.65)
    c.text("cause", (360, 600), 40, WHITE, k)
    dashed(c, (470, 600), (1260, 600), RED, 6, partial=k)
    if k > 0.98:
        c.arrow((1250, 600), (1290, 600), RED, 6, 26)
    c.text("may be", (865, 560), 40, RED, k)
    c.text("race condition", (1460, 600), 40, WHITE, k)
    w = F.phase(t, 0.7, 0.9)
    never = 'never: "is caused by"'
    cw44 = 0.602 * 44
    n0 = 960 - len(never) * cw44 / 2
    c.text(never, (n0, 820), 44, GREY, w, font="mono", anchor="lm")
    s0 = n0 + len("never: ") * cw44     # strike only the forbidden phrase
    c.line((s0, 820), (F.lerp(s0, n0 + len(never) * cw44, w), 820), RED, 5, w)


# 9 ---------------------------------------------------------------------------
@mv.beat(9)
def no_facts(c, t):
    c.text("rule 2: add no facts", (960, 180), 56, WHITE, F.ease(t * 4))
    a = F.phase(t, 0.15, 0.35)
    box(c, 260, 380, 560, 260, WHITE, a)
    c.text("retry.diff", (540, 430), 36, GREY, a, font="mono")
    for i, s in enumerate(["- MAX_RETRIES = 3", "+ MAX_RETRIES = 5", "+ BASE_DELAY = 0.5"]):
        c.text(s, (300, 500 + i * 46), 32, RED if s[0] == "-" else GRN, a, font="mono", anchor="lm")
    k = F.phase(t, 0.4, 0.6)
    c.arrow((850, 510), (F.lerp(850, 1050, k), 510), GREY, 4, 20, k)
    box(c, 1080, 400, 620, 220, YEL, F.phase(t, 0.5, 0.7), dash=True)
    c.text("why?", (1390, 470), 54, YEL, F.phase(t, 0.5, 0.7))
    c.text('"The diff does not say why."', (1390, 560), 34, WHITE, F.phase(t, 0.65, 0.85), font="mono")


# 10 --------------------------------------------------------------------------
@mv.beat(10)
def linter(c, t):
    c.text("ste-lint.py", (960, 180), 56, WHITE, F.ease(t * 4), font="mono")
    words = [("Our", WHITE), ("seamless", RED), ("cache", WHITE), ("may", GRN), ("help;", RED), ("it", WHITE), ("is", WHITE), ("fast.", WHITE)]
    x = 260
    for i, (w, col) in enumerate(words):
        a = F.phase(t, 0.05 + i * 0.04, 0.15 + i * 0.04)
        mark = F.phase(t, 0.45, 0.6)
        shown = WHITE if col is WHITE else (col if mark > 0.5 else WHITE)
        c.text(w, (x, 480), 56, shown, a, font="mono", anchor="lm")
        width = len(w) * 34 + 30
        if col is RED:
            c.line((x, 520), (x + width - 30, 520), RED, 5, mark)
        x += width
    c.text("marketing word", (520, 600), 32, RED, F.phase(t, 0.55, 0.7))
    c.text("semicolon", (1180, 600), 32, RED, F.phase(t, 0.55, 0.7))
    c.text("hedge: never flagged", (900, 680), 36, GRN, F.phase(t, 0.7, 0.85))


# 11 --------------------------------------------------------------------------
@mv.beat(11)
def voice(c, t):
    c.text("voice: first one found", (960, 220), 50, WHITE, F.ease(t * 4))
    names = ["ElevenLabs", "Piper", "TTS_CMD", "macOS say"]
    found = 3
    k = F.phase(t, 0.2, 0.85) * 4
    for i, n in enumerate(names):
        x = 160 + i * 420
        a = F.phase(t, 0.05 + i * 0.05, 0.15 + i * 0.05)
        col = YEL if (i == found and k >= i) else (GREY if k > i + 0.5 else WHITE)
        box(c, x, 460, 340, 120, col, a, width=4)
        c.text(n, (x + 170, 520), 40, col, a)
        if i < 3:
            c.arrow((x + 345, 520), (x + 415, 520), GREY, 4, 18, a)
        if k > i + 0.5 and i != found:
            c.text("not set", (x + 170, 630), 30, GREY, a)
    c.text("this video: macOS say", (960, 800), 40, YEL, F.phase(t, 0.85, 0.97))


# 12 --------------------------------------------------------------------------
@mv.beat(12)
def renderer(c, t):
    a = F.ease(t * 4)
    c.text("manim installed?", (480, 300), 44, WHITE, a)
    c.arrow((480, 340), (480, 440), GREY, 4, 20, a)
    c.text("no", (520, 395), 34, BLUE, a, anchor="lm")
    box(c, 220, 450, 520, 110, BLUE, a, width=5)
    c.text("frames.py via uv run", (480, 505), 38, BLUE, a, font="mono")
    c.text("numpy + Pillow", (480, 620), 32, GREY, F.phase(t, 0.15, 0.3))
    # a live drawing: the renderer drawing a wave, the way this video was drawn
    ax = c.axes((900, 300, 1760, 760), x=(0, 4), y=(-1.5, 1.5), alpha=F.phase(t, 0.2, 0.35), ticks=False)
    xs = np.linspace(0, 4, 500)
    pts = ax(xs, np.sin(2 * np.pi * xs) * np.exp(-0.15 * xs))
    k = F.phase(t, 0.3, 0.95)
    c.curve(pts, YEL, 6, partial=k)
    i = min(len(pts) - 1, int(len(pts) * k))
    c.dot(pts[i], 14, WHITE, F.phase(t, 0.3, 0.35))
    c.text("each frame drawn from scratch", (1330, 840), 32, GREY, F.phase(t, 0.6, 0.8))


# 13 --------------------------------------------------------------------------
@mv.beat(13)
def limits(c, t):
    a, b = F.phase(t, 0.05, 0.25), F.phase(t, 0.3, 0.5)
    box(c, 200, 330, 680, 300, GRN, a, width=4)
    c.text("form", (540, 400), 50, GRN, a)
    c.text("the linter checks this", (540, 500), 34, WHITE, a)
    box(c, 1040, 330, 680, 300, RED, b, dash=True)
    c.text("truth", (1380, 400), 50, RED, b)
    c.text("the linter cannot check this", (1380, 500), 34, WHITE, b)
    c.text("outline + two rules", (1380, 760), 40, YEL, F.phase(t, 0.65, 0.85))
    c.arrow((1380, 720), (1380, 650), YEL, 4, 20, F.phase(t, 0.65, 0.85))


# 14 --------------------------------------------------------------------------
@mv.beat(14)
def outro(c, t):
    ladder(c, 1.0, lit="all", alpha=1 - F.phase(t, 0.55, 0.8))
    c.text("pick a rung", (960, 380), 60, WHITE, F.phase(t, 0.6, 0.72))
    c.text("keep the facts", (960, 500), 60, WHITE, F.phase(t, 0.68, 0.8))
    c.text("climb when you need more", (960, 620), 60, YEL, F.phase(t, 0.76, 0.88))
    c.text("github.com/bowen31337/comprehension-ladder", (960, 820), 30, GREY, F.phase(t, 0.85, 0.95), font="mono")


mv.render()
