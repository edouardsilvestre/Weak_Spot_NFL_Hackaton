"""Build route-level dataset from NGS tracking: frames between snap and pass, normalized
so the offense always moves toward +x, plus separation at the moment of the pass."""
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw" / "data"
OUT = ROOT / "data"

SNAP_EVENTS = {"ball_snap", "autoevent_ballsnap"}
PASS_EVENTS = {"pass_forward", "autoevent_passforward"}
COLS = ["gameId", "playId", "nflId", "frameId", "team", "playDirection", "x", "y", "s", "event"]


def load_meta():
    plays = pd.read_csv(RAW / "plays.csv")
    pff = pd.read_csv(RAW / "pffScoutingData.csv", usecols=["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp"])
    players = pd.read_csv(RAW / "players.csv", usecols=["nflId", "officialPosition", "displayName"])
    runners = pff[pff.pff_role == "Pass Route"].merge(players, on="nflId", how="left")
    return plays, runners


def parse_target(plays, runners):
    """Match the receiver named in playDescription ("pass short right to M.Evans") to a route runner."""
    pat = r"pass (?:incomplete )?(?:short|deep) (?:left|middle|right) (?:to|intended for) ([A-Z][a-zA-Z'\-]*\.\s?[A-Z][a-zA-Z'\-]+)"
    tgt = plays.playDescription.str.extract(pat)[0]
    plays = plays.assign(target_abbr=tgt)
    r = runners.copy()
    parts = r.displayName.fillna("").str.split(" ", n=1)
    r["abbr"] = parts.str[0].str[0] + "." + parts.str[1].fillna("")
    r["last"] = parts.str[1].fillna("")
    m = r.merge(plays[["gameId", "playId", "target_abbr"]], on=["gameId", "playId"])
    full = m.abbr.str.replace(" ", "") == m.target_abbr.fillna("#").str.replace(" ", "")
    # fallback: last name match within the play (handles "Amon-Ra St. Brown" style names)
    last = m.target_abbr.fillna("#").str.split(".", n=1).str[-1].str.replace(" ", "") == m["last"].str.replace(" ", "")
    m["is_target"] = full
    nfull = m.groupby(["gameId", "playId"]).is_target.transform("sum")
    m.loc[(nfull == 0) & last, "is_target"] = True
    return m.loc[m.is_target, ["gameId", "playId", "nflId"]].drop_duplicates(["gameId", "playId"])


def process_game(args):
    path, plays_g, runners_g = args
    df = pd.read_csv(path, usecols=COLS)
    ev = df.dropna(subset=["event"])
    snap = ev[ev.event.isin(SNAP_EVENTS)].groupby(["gameId", "playId"]).frameId.min().rename("snap_f")
    pas = ev[ev.event.isin(PASS_EVENTS)].groupby(["gameId", "playId"]).frameId.min().rename("pass_f")
    fr = pd.concat([snap, pas], axis=1).dropna().reset_index()
    fr = fr[fr.pass_f > fr.snap_f]
    df = df.merge(fr, on=["gameId", "playId"])
    df = df[(df.frameId >= df.snap_f) & (df.frameId <= df.pass_f)].copy()
    left = df.playDirection == "left"
    df.loc[left, "x"] = 120 - df.loc[left, "x"]
    df.loc[left, "y"] = 53.3 - df.loc[left, "y"]
    df = df.merge(plays_g[["gameId", "playId", "possessionTeam"]], on=["gameId", "playId"])

    ball = df[(df.team == "football") & (df.frameId == df.snap_f)][["gameId", "playId", "x", "y"]]
    ball.columns = ["gameId", "playId", "los", "ball_y"]
    ball = ball.drop_duplicates(["gameId", "playId"])

    rr = df.merge(runners_g[["gameId", "playId", "nflId"]], on=["gameId", "playId", "nflId"])
    rr = rr.merge(ball, on=["gameId", "playId"]).sort_values(["gameId", "playId", "nflId", "frameId"])
    start = rr[rr.frameId == rr.snap_f][["gameId", "playId", "nflId", "x", "y"]].rename(columns={"x": "x0", "y": "y0"})
    rr = rr.merge(start, on=["gameId", "playId", "nflId"])
    side = np.sign(rr.y0 - rr.ball_y).replace(0, 1)
    rr["depth"] = rr.x - rr.x0                 # downfield from own start
    rr["lat"] = (rr.y - rr.y0) * side          # + toward nearest sideline, - toward middle
    rr["x_los"] = rr.x - rr.los
    rr["t"] = (rr.frameId - rr.snap_f) / 10

    # separation at pass: distance to the nearest defender
    at_pass = df[df.frameId == df.pass_f]
    defs = at_pass[(at_pass.team != at_pass.possessionTeam) & (at_pass.team != "football")][["gameId", "playId", "x", "y"]]
    rp = rr[rr.frameId == rr.pass_f][["gameId", "playId", "nflId", "x", "y"]]
    j = rp.merge(defs, on=["gameId", "playId"], suffixes=("", "_d"))
    j["d"] = np.hypot(j.x - j.x_d, j.y - j.y_d)
    sep = j.groupby(["gameId", "playId", "nflId"]).d.min().rename("separation").reset_index()

    keep = ["gameId", "playId", "nflId", "frameId", "t", "x", "y", "x_los", "depth", "lat", "s", "x0", "y0", "los", "ball_y"]
    return rr[keep], sep


def main(n_games=None):
    OUT.mkdir(exist_ok=True)
    plays, runners = load_meta()
    files = sorted((RAW / "tracking").glob("tracking_*.csv"))[:n_games]
    tasks = []
    for f in files:
        gid = int(f.stem.split("_")[1])
        tasks.append((f, plays[plays.gameId == gid], runners[runners.gameId == gid]))
    with Pool() as pool:
        res = pool.map(process_game, tasks)
    routes = pd.concat([r for r, _ in res], ignore_index=True)
    sep = pd.concat([s for _, s in res], ignore_index=True)

    tgt = parse_target(plays, runners)
    tgt["targeted"] = True
    summ = routes.groupby(["gameId", "playId", "nflId"]).agg(
        x0=("x0", "first"), y0=("y0", "first"), los=("los", "first"), ball_y=("ball_y", "first"),
        n_frames=("frameId", "size")).reset_index()
    summ = summ.merge(sep, on=["gameId", "playId", "nflId"], how="left")
    summ = summ.merge(tgt, on=["gameId", "playId", "nflId"], how="left")
    summ["targeted"] = summ.targeted.fillna(False).astype(bool)
    summ = summ.merge(runners[["gameId", "playId", "nflId", "pff_positionLinedUp", "officialPosition", "displayName"]],
                      on=["gameId", "playId", "nflId"], how="left")
    summ = summ.merge(plays[["gameId", "playId", "possessionTeam", "defensiveTeam", "passResult", "playResult",
                             "pff_passCoverage", "pff_passCoverageType", "playDescription"]], on=["gameId", "playId"], how="left")
    routes.to_parquet(OUT / "routes.parquet", index=False)
    summ.to_parquet(OUT / "route_summary.parquet", index=False)
    print(f"{len(files)} games, {summ[['gameId','playId']].drop_duplicates().shape[0]} plays, {len(summ)} routes, "
          f"{summ.targeted.sum()} targeted, sep mean {summ.separation.mean():.2f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
