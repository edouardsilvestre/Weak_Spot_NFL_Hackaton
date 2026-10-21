"""Weak Spot - Coach Mode: self-contained coach.html with an embedded compact route table.
All filtering and hierarchical shrinkage happen in the browser (vanilla JS)."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = ROOT / "data_raw" / "data"
KEYS = ["gameId", "playId", "nflId"]
ROUTES = ["GO", "POST", "CORNER", "SLANT", "IN/DIG", "OUT", "HITCH/CURL", "FLAT", "SCREEN",
          "RB WHEEL/ANGLE", "RB CHECKDOWN"]
DIST = ["Court ≤3", "Moyen 4-6", "Long ≥7"]
PERSD = ["Base (4 DB)", "Nickel (5)", "Dime (6+)"]
COVS = ["Cover-0", "Cover-1", "2-Man", "Cover-2", "Cover-3", "Quarters", "Cover-6", "Red Zone", "Autre"]
N_PATH = 8


def pers_o(s):
    if not isinstance(s, str):
        return "Autre"
    rb = re.search(r"(\d) RB", s); te = re.search(r"(\d) TE", s)
    return f"{rb.group(1) if rb else 0}{te.group(1) if te else 0}"


def pers_d(s):
    m = re.search(r"(\d+) DB", s) if isinstance(s, str) else None
    if not m:
        return None
    n = int(m.group(1))
    return PERSD[0] if n <= 4 else PERSD[1] if n == 5 else PERSD[2]


def dist_bucket(y):
    return 0 if y <= 3 else 1 if y <= 6 else 2


def main():
    summ = pd.read_parquet(DATA / "route_summary.parquet")
    plays = pd.read_csv(RAW / "plays.csv", usecols=["gameId", "playId", "down", "yardsToGo", "personnelO", "personnelD"])
    summ = summ.drop(columns=[c for c in ("down", "yardsToGo") if c in summ.columns]).merge(plays, on=["gameId", "playId"])
    summ = summ[summ.route.isin(ROUTES) & summ.separation.notna() & summ.down.between(1, 4)].copy()

    summ["persO"] = summ.personnelO.map(pers_o)
    counts = summ.drop_duplicates(["gameId", "playId"]).persO.value_counts()
    keep = [p for p in counts.index if counts[p] >= 100 and p != "Autre"]
    summ.loc[~summ.persO.isin(keep), "persO"] = "Autre"
    PERSO = sorted(keep) + ["Autre"]
    summ["persD"] = summ.personnelD.map(pers_d).fillna(PERSD[1])
    summ["db"] = summ.yardsToGo.map(dist_bucket)
    summ["ct"] = summ.pff_passCoverageType.where(summ.pff_passCoverageType.isin(["Man", "Zone"]), "Other")
    summ["cv"] = summ.pff_passCoverage.where(summ.pff_passCoverage.isin(COVS), "Autre")
    gain = summ.playResult.fillna(0)
    need = np.select([summ.down == 1, summ.down == 2], [0.4 * summ.yardsToGo, 0.6 * summ.yardsToGo], summ.yardsToGo)
    summ["success"] = np.where(summ.targeted, (gain >= need).astype(int), -1)
    summ["complete"] = (summ.targeted & (summ.passResult == "C")).astype(int)

    # downsampled real paths (field coords: x across the field, y = yards past LOS)
    routes = pd.read_parquet(DATA / "routes.parquet", columns=KEYS + ["frameId", "x_los", "y", "depth", "lat"])
    routes = routes.merge(summ[KEYS], on=KEYS)
    g = routes.groupby(KEYS)
    routes["i"] = g.cumcount()
    routes["q"] = np.round(routes.i / (g.frameId.transform("size") - 1).clip(lower=1) * (N_PATH - 1)).astype(int)
    pts = routes.drop_duplicates(KEYS + ["q"]).sort_values(KEYS + ["q"])
    paths = pts.groupby(KEYS).apply(lambda d: [int(round(v)) for xy in zip(d.y * 2, d.x_los * 2) for v in xy]).rename("path")
    summ = summ.merge(paths.reset_index(), on=KEYS, how="left")
    summ["path"] = summ.path.apply(lambda p: p if isinstance(p, list) else [])

    # typical (median) route shape per class, relative to the start (lat + = toward sideline)
    rel = routes.merge(summ[KEYS + ["route"]], on=KEYS)
    rel["q"] = np.round(rel.i / (rel.groupby(KEYS).frameId.transform("size") - 1).clip(lower=1) * 10).astype(int)
    tmpl = rel.groupby(["route", "q"])[["lat", "depth"]].median().round(1)
    start = summ.assign(x0l=summ.x0 - summ.los).groupby("route").x0l.median()
    templates = {r: dict(pts=tmpl.loc[r].values.tolist(), x0=round(float(start[r]), 1)) for r in ROUTES}

    teams = sorted(set(summ.defensiveTeam) | set(summ.possessionTeam))
    names = sorted(summ.displayName.fillna("?").unique())
    ti, ni = {t: i for i, t in enumerate(teams)}, {n: i for i, n in enumerate(names)}
    enc = lambda col, cats: summ[col].map({c: i for i, c in enumerate(cats)}).astype(int).tolist()
    R = dict(
        d=summ.defensiveTeam.map(ti).tolist(), o=summ.possessionTeam.map(ti).tolist(), dn=summ.down.astype(int).tolist(),
        db=summ.db.tolist(), po=enc("persO", PERSO), pd=enc("persD", PERSD), ct=enc("ct", ["Man", "Zone", "Other"]),
        cv=enc("cv", COVS), r=enc("route", ROUTES), s=(summ.separation * 10).round().astype(int).tolist(),
        t=summ.targeted.astype(int).tolist(), c=summ.complete.tolist(),
        y=summ.playResult.where(summ.targeted, 0).fillna(0).astype(int).tolist(), u=summ.success.tolist(),
        p=summ.displayName.fillna("?").map(ni).tolist(), g=summ.gameId.astype(str).str[-4:].astype(int).tolist(),
        k=summ.playId.astype(int).tolist(), xy=summ.path.tolist(),
    )
    meta = dict(teams=teams, names=names, routes=ROUTES, dist=DIST, persO=PERSO, persD=PERSD, covs=COVS,
                ct=["Man", "Zone", "Other"], templates=templates)
    payload = json.dumps(dict(R=R, M=meta), ensure_ascii=False, separators=(",", ":"))
    html = (ROOT / "src" / "coach_template.html").read_text(encoding="utf-8")
    html = html.replace("/*__PLOTLY__*/", plotly.offline.get_plotlyjs()).replace("__DATA__", payload)
    (ROOT / "coach.html").write_text(html, encoding="utf-8")
    print(f"{len(summ)} routes, {summ.targeted.sum()} targeted, persO={PERSO}, payload {len(payload)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
