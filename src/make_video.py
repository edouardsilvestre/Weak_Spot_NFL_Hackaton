"""30-second motion-design teaser rendered frame by frame (PIL) and encoded with ffmpeg.
Route shapes are the real median trajectories per route class. Output: videos/weak_spot_30s.mp4"""
import math
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "videos" / "weak_spot_30s.mp4"
W, H, FPS, DUR = 1920, 1080, 30, 30
BG, ACC, TXT, MUT, FIELD = (11, 19, 32), (246, 201, 14), (238, 242, 248), (120, 136, 162), (47, 107, 58)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def clamp(x):
    return max(0.0, min(1.0, x))


def ease(x):  # easeOutCubic
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def mix(c1, c2, a):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


def text(d, xy, s, size, color, anchor="la", alpha=1.0, bg=BG):
    d.text(xy, s, font=font(size), fill=mix(bg, color, clamp(alpha)), anchor=anchor)


def templates():
    keys = ["gameId", "playId", "nflId"]
    summ = pd.read_parquet(ROOT / "data" / "route_summary.parquet", columns=keys + ["route"])
    r = pd.read_parquet(ROOT / "data" / "routes.parquet", columns=keys + ["frameId", "depth", "lat"]).merge(summ, on=keys)
    g = r.groupby(keys)
    r["q"] = np.round(g.cumcount() / (g.frameId.transform("size") - 1).clip(lower=1) * 20).astype(int)
    m = r.groupby(["route", "q"])[["depth", "lat"]].median()
    return {k: m.loc[k].to_numpy() for k in ["GO", "POST", "SLANT", "OUT", "IN/DIG", "CORNER", "HITCH/CURL"]}


# ---------------- scenes ----------------
def s_title(d, t):
    word = "WEAK SPOT"
    f = font(170)
    total = d.textlength(word, font=f)
    x = (W - total) / 2
    for i, ch in enumerate(word):
        a = ease((t - 0.08 * i) / 0.5)
        text(d, (x, 420 + (1 - a) * 90), ch, 170, TXT, alpha=a)
        x += d.textlength(ch, font=f)
    bw = ease((t - 1.0) / 0.7) * total
    d.rectangle([(W - total) / 2, 640, (W - total) / 2 + bw, 656], fill=ACC)
    text(d, (W / 2, 720), "COACH MODE", 40, MUT, "ma", alpha=ease((t - 1.6) / 0.6))


def s_choices(d, t):
    words = [("DOWN", "3e"), ("DISTANCE", "& long"), ("PERSONNEL", "Nickel 4-2-5")]
    for i, (w, tag) in enumerate(words):
        a = ease((t - 1.45 * i) / 0.45)
        if a <= 0:
            continue
        y = 190 + i * 210
        text(d, (140 + (1 - a) * -160, y), w, 150, TXT, alpha=a)
        b = ease((t - 1.45 * i - 0.25) / 0.4)
        if b > 0:
            ts = 100 if len(tag) <= 6 else 64
            tw = d.textlength(tag, font=font(ts)) + 70
            x0, off = W - 110 - tw, (1 - b) * 40
            d.rounded_rectangle([x0, y + 10 + off, x0 + tw, y + 160 + off], 22, fill=mix(BG, ACC, b))
            text(d, (x0 + tw / 2, y + 85 + off), tag, ts, BG, "mm", bg=mix(BG, ACC, b))
    c = ease((t - 4.6) / 0.5)
    if c > 0:
        text(d, (140, 860), "Trois choix,", 90, ACC, alpha=c)


def s_call(d, t):
    p = ease_io(t / 0.55)
    d.rectangle([0, 0, W * p, H], fill=ACC)
    a = ease((t - 0.35) / 0.4)
    if a > 0:
        text(d, (W / 2, H / 2), "un appel.", int(250 * (1 + (1 - a) * 0.25)), BG, "mm", bg=ACC)


def field_xy(depth, lat, y0):
    # offense going right: LOS at x=420, 1 yd = 52 px
    return 420 + depth * 52, y0 - lat * 30


def s_field(d, t, tm):
    a = ease(t / 0.5)
    top, bot = 150, 930
    d.rectangle([0, top, W * a, bot], fill=FIELD)
    for k in range(-10, 35, 5):
        x = 420 + k * 52
        if 0 <= x <= W * a:
            d.line([x, top, x, bot], fill=mix(FIELD, (255, 255, 255), 0.35 if k % 10 else 0.6), width=3)
    if a >= 1:
        d.line([420, top, 420, bot], fill=(77, 163, 255), width=7)
    starts = [("GO", 220, 1), ("POST", 300, 1), ("CORNER", 420, 1), ("HITCH/CURL", 640, -1), ("OUT", 710, -1), ("IN/DIG", 840, -1)]
    for i, (rname, y0, side) in enumerate(starts):
        p = ease((t - 0.6 - 0.35 * i) / 1.0)
        if p <= 0:
            continue
        pts = tm[rname]
        xy = [field_xy(dp, lt * side, y0) for dp, lt in pts[:max(2, int(len(pts) * p))]]
        d.line(xy, fill=mix(FIELD, (255, 255, 255), 0.75), width=9, joint="curve")
        d.ellipse([xy[0][0] - 11, xy[0][1] - 11, xy[0][0] + 11, xy[0][1] + 11], fill=TXT)
    # the call: SLANT, highlighted
    p = ease((t - 3.4) / 0.9)
    if p > 0:
        pts = tm["SLANT"]
        xy = [field_xy(dp, -lt, 560) for dp, lt in pts[:max(2, int(len(pts) * p))]]
        d.line(xy, fill=ACC, width=20, joint="curve")
        d.ellipse([xy[0][0] - 16, xy[0][1] - 16, xy[0][0] + 16, xy[0][1] + 16], fill=ACC)
        ex, ey = xy[-1]
        r = 24 * (1 + 0.25 * math.sin(max(0, t - 4.3) * 7) * clamp((t - 4.3) * 3))
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=ACC)
    c = ease((t - 4.4) / 0.5)
    if c > 0:
        x0 = 1280 + (1 - c) * 120
        d.rounded_rectangle([x0, 330, x0 + 500, 650], 30, fill=mix(FIELD, BG, c))
        text(d, (x0 + 50, 365), "SLANT", 90, ACC, alpha=c)
        text(d, (x0 + 50, 470), "59 %", 120, TXT, alpha=c)
        text(d, (x0 + 50, 600), "de succès", 38, MUT, alpha=c)


def s_bars(d, t):
    text(d, (200, 160), "Moins d'espace.", 96, TXT, alpha=ease(t / 0.4))
    text(d, (200, 280), "Plus de succès.", 96, ACC, alpha=ease((t - 0.5) / 0.4))
    rows = [("SLANT", 0.59, "2,6 yd", ACC), ("GO", 0.48, "2,8 yd", MUT)]
    for i, (name, v, sep, col) in enumerate(rows):
        p = ease((t - 1.1 - 0.25 * i) / 1.2)
        y = 500 + i * 220
        text(d, (200, y + 15), name, 64, TXT, alpha=clamp(p * 3))
        text(d, (200, y + 100), f"séparation {sep}", 30, MUT, alpha=clamp((t - 2.3) * 2))
        x0, full = 600, 1000
        bw = max(30, full * v / 0.6 * p)
        d.rounded_rectangle([x0, y, x0 + bw, y + 120], 18, fill=col)
        text(d, (x0 + bw + 30, y + 60), f"{round(100 * v * p)} %", 80, TXT, "lm", alpha=clamp(p * 3))
    text(d, (W - 200, 1000), "taux de succès · 783 et 1 028 ciblages · 2021, semaines 1-8", 28, MUT, "rs", alpha=clamp((t - 2.6) * 2))


def s_outro(d, t):
    text(d, (W / 2, 330), "Down. Distance. Personnel.", 90, TXT, "mm", alpha=ease(t / 0.5))
    text(d, (W / 2, 470), "Trois choix, un appel.", 110, ACC, "mm", alpha=ease((t - 0.5) / 0.5))
    b = ease((t - 1.2) / 0.6)
    d.rectangle([W / 2 - 300 * b, 580, W / 2 + 300 * b, 588], fill=ACC)
    text(d, (W / 2, 690), "WEAK SPOT", 120, TXT, "mm", alpha=ease((t - 1.4) / 0.5))
    text(d, (W / 2, 800), "coach.html  ·  NFL Big Data Bowl  ·  Next Gen Stats", 36, MUT, "mm", alpha=ease((t - 1.9) / 0.5))


SCENES = [(0, 3.5, s_title), (3.5, 9.6, s_choices), (9.6, 12.2, s_call), (12.2, 19.6, s_field), (19.6, 25.0, s_bars), (25.0, 30.0, s_outro)]


def frame(tsec, tm):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for t0, t1, scene in SCENES:
        if t0 <= tsec < t1:
            t = tsec - t0
            scene(d, t, tm) if scene is s_field else scene(d, t)
            # quick fades at scene edges (the yellow wipe is its own entrance)
            edge = min((t1 - tsec) / 0.18, 1.0 if scene is s_call else t / 0.18, 1.0)
            if tsec >= DUR - 0.6:
                edge = min(edge, (DUR - tsec) / 0.6)
            if edge < 1:
                img = Image.blend(Image.new("RGB", (W, H), BG), img, clamp(edge))
            break
    ImageDraw.Draw(img).rectangle([0, H - 8, W * tsec / DUR, H], fill=ACC)  # progress line
    return img


def main():
    OUT.parent.mkdir(exist_ok=True)
    tm = templates()
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", str(OUT)], stdin=subprocess.PIPE)
    for i in range(DUR * FPS):
        ff.stdin.write(frame(i / FPS, tm).tobytes())
    ff.stdin.close()
    ff.wait()
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
