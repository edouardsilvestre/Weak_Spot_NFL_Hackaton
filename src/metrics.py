"""Separation-based vulnerability by defense x route and coverage x route."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
K = 20          # empirical-Bayes shrinkage strength (pseudo-routes at league average)
MIN_N = 10      # hide cells below this sample size

SITUATIONS = {
    "Tous": lambda d: d.down.notna(),
    "1er-2e down": lambda d: d.down.isin([1, 2]),
    "3e & court (≤3 yds)": lambda d: (d.down == 3) & (d.yardsToGo <= 3),
    "3e & long (≥7 yds)": lambda d: (d.down == 3) & (d.yardsToGo >= 7),
}

ANALYZED = ["GO", "POST", "CORNER", "SLANT", "IN/DIG", "OUT", "HITCH/CURL", "FLAT", "SCREEN",
            "RB WHEEL/ANGLE", "RB CHECKDOWN"]


def aggregate(summ, by):
    s = summ.assign(complete=(summ.passResult == "C").astype(float),
                    yds=summ.playResult.where(summ.targeted))
    t = s[s.targeted]
    g = s.groupby(by + ["route"]).agg(n=("separation", "size"), sep=("separation", "mean")).reset_index()
    gt = t.groupby(by + ["route"]).agg(n_tgt=("complete", "size"), comp=("complete", "mean"),
                                       ypt=("yds", "mean")).reset_index()
    g = g.merge(gt, on=by + ["route"], how="left")
    g["n_tgt"] = g.n_tgt.fillna(0).astype(int)
    return g


def analyze(summ):
    """Vulnerability tables for one situation; league baseline is computed within the same situation."""
    league = summ.groupby("route").agg(lg_sep=("separation", "mean"), lg_n=("separation", "size")).reset_index()
    lt = summ[summ.targeted]
    league = league.merge(lt.assign(conv=lt.playResult >= lt.yardsToGo).groupby("route").agg(
        lg_comp=("passResult", lambda x: (x == "C").mean()), lg_ypt=("playResult", "mean"),
        lg_conv=("conv", "mean"), lg_n_tgt=("conv", "size")).reset_index(), on="route", how="left")

    team = aggregate(summ, ["defensiveTeam"]).merge(league, on="route")
    team["raw_delta"] = team.sep - team.lg_sep
    team["vuln"] = team.raw_delta * team.n / (team.n + K)
    team["show"] = team.n >= MIN_N
    # overall team vulnerability: route-volume weighted shrunk delta
    overall = team.groupby("defensiveTeam").apply(lambda d: (d.vuln * d.n).sum() / d.n.sum()).rename("overall").reset_index()
    team = team.merge(overall, on="defensiveTeam")

    cov = aggregate(summ[summ.pff_passCoverageType.isin(["Man", "Zone"])], ["pff_passCoverageType"]).merge(league, on="route")
    # how often each defense plays man in this situation (one row per play)
    plays = summ.drop_duplicates(["gameId", "playId"])
    plays = plays[plays.pff_passCoverageType.isin(["Man", "Zone"])]
    man = plays.groupby("defensiveTeam").agg(man_rate=("pff_passCoverageType", lambda x: (x == "Man").mean()),
                                             n_plays=("playId", "size")).reset_index()
    team = team.merge(man, on="defensiveTeam", how="left")
    return team, cov, league


def main():
    summ = pd.read_parquet(DATA / "route_summary.parquet")
    plays = pd.read_csv(ROOT / "data_raw" / "data" / "plays.csv", usecols=["gameId", "playId", "down", "yardsToGo"])
    summ = summ.drop(columns=[c for c in ("down", "yardsToGo") if c in summ.columns]).merge(plays, on=["gameId", "playId"])
    summ = summ[summ.route.isin(ANALYZED) & summ.separation.notna()]
    teams, covs, leagues = [], [], []
    for name, f in SITUATIONS.items():
        t, c, l = analyze(summ[f(summ)])
        teams.append(t.assign(situation=name)); covs.append(c.assign(situation=name)); leagues.append(l.assign(situation=name))
    team, cov, league = (pd.concat(x, ignore_index=True) for x in (teams, covs, leagues))

    team.to_csv(DATA / "team_route_vuln.csv", index=False)
    cov.to_csv(DATA / "coverage_route.csv", index=False)
    league.to_csv(DATA / "league_route.csv", index=False)
    print(league.pivot(index="route", columns="situation", values="lg_sep").round(2))
    print(league.pivot(index="route", columns="situation", values="lg_n"))
    print(league.pivot(index="route", columns="situation", values="lg_comp").round(2))
    print(league.pivot(index="route", columns="situation", values="lg_ypt").round(1))
    t = team[team.situation == "Tous"]
    print(t.sort_values("vuln", ascending=False).head(5)[["defensiveTeam", "route", "n", "sep", "vuln", "n_tgt", "comp", "ypt"]].round(2))


if __name__ == "__main__":
    main()
