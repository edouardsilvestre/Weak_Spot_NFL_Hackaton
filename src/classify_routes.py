"""Rule-based route classification from snap-to-pass trajectories.

Coordinates per route: depth (+ = downfield from start) and lat (+ = toward nearest sideline).
Key features: depth vs LOS at the pass, final heading over the last 0.6 s, stem depth at the break.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"

ORDER = ["GO", "POST", "CORNER", "SLANT", "IN/DIG", "OUT", "HITCH/CURL", "FLAT", "SCREEN",
         "RB WHEEL/ANGLE", "RB CHECKDOWN", "OTHER"]
KEYS = ["gameId", "playId", "nflId"]


def route_features(routes):
    def feats(g):
        d, l = g.depth.to_numpy(), g.lat.to_numpy()
        k = min(6, len(d) - 1)
        dd, dl = d[-1] - d[-1 - k], l[-1] - l[-1 - k]
        heading = np.degrees(np.arctan2(dl, dd)) if np.hypot(dd, dl) > 0.3 else np.nan
        # break = point farthest from the start->end chord
        p = np.c_[d, l]
        chord = p[-1] - p[0]
        n = np.hypot(*chord)
        dist = np.abs(chord[0] * (p[:, 1] - p[0, 1]) - chord[1] * (p[:, 0] - p[0, 0])) / n if n > 0 else np.zeros(len(p))
        b = int(np.argmax(dist))
        return pd.Series({
            "depth_end": d[-1], "lat_end": l[-1], "depth_max": d.max(),
            "los_depth_pass": g.x_los.iloc[-1], "heading": heading,
            "stem_depth": d[b], "break_dev": dist[b], "speed_end": g.s.iloc[-1],
            "comeback": d.max() - d[-1],
        })
    return routes.groupby(KEYS).apply(feats).reset_index()


def classify(r):
    is_rb = r.pff_positionLinedUp in ("HB", "HB-L", "HB-R", "FB", "FB-L", "FB-R") or str(r.pff_positionLinedUp).startswith("HB")
    d, h = r.los_depth_pass, r.heading
    if is_rb:
        return "RB WHEEL/ANGLE" if d >= 4 else "RB CHECKDOWN"
    if d < 0.5:
        return "SCREEN"
    if d >= 3 and r.depth_max < 18 and ((r.comeback > 1.0 and (np.isnan(h) or abs(h) > 90)) or r.speed_end < 1.5):
        return "HITCH/CURL"
    if np.isnan(h):
        return "OTHER"
    if abs(h) > 120:
        return "HITCH/CURL" if d >= 3 else "OTHER"
    if d < 4 and h > 30:
        return "FLAT"
    if abs(h) <= 25:
        return "GO" if d >= 10 else "OTHER"
    if 25 < h <= 65:
        return "CORNER" if d >= 10 else "OUT"
    if h > 65:
        return "OUT"
    if -65 <= h < -25:
        return "POST" if (d >= 10 and r.stem_depth >= 7) else "SLANT"
    return "IN/DIG"


def route_tree_figure(routes, summ, path, per_class=30):
    classes = [c for c in ORDER if c in summ.route.unique()]
    ncol = 4
    nrow = int(np.ceil(len(classes) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(16, 4.2 * nrow))
    rk = routes.set_index(KEYS)
    for ax, c in zip(axes.flat, classes):
        sub = summ[summ.route == c]
        smp = sub.sample(min(per_class, len(sub)), random_state=0)
        for key in smp[KEYS].itertuples(index=False):
            g = rk.loc[tuple(key)]
            ax.plot(g.lat, g.depth, lw=0.8, alpha=0.6)
        ax.axhline(0, color="grey", lw=0.5)
        ax.set_title(f"{c}  (n={len(sub)})")
        ax.set_xlim(-25, 25); ax.set_ylim(-8, 30)
        ax.set_xlabel("<- middle   |   sideline ->")
    for ax in list(axes.flat)[len(classes):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=80)


def main():
    routes = pd.read_parquet(DATA / "routes.parquet")
    summ = pd.read_parquet(DATA / "route_summary.parquet")
    f = route_features(routes)
    summ = summ.drop(columns=[c for c in f.columns if c in summ.columns and c not in KEYS]).merge(f, on=KEYS)
    summ["route"] = summ.apply(classify, axis=1)
    summ.to_parquet(DATA / "route_summary.parquet", index=False)
    FIG.mkdir(exist_ok=True)
    route_tree_figure(routes, summ, FIG / "route_tree_check.png")
    print(summ.route.value_counts())


if __name__ == "__main__":
    main()
