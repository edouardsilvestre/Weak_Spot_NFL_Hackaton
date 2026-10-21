"""Separation-based vulnerability by defense x route and coverage x route."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
K = 20          # empirical-Bayes shrinkage strength (pseudo-routes at league average)
MIN_N = 10      # hide cells below this sample size

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


def main():
    summ = pd.read_parquet(DATA / "route_summary.parquet")
    summ = summ[summ.route.isin(ANALYZED) & summ.separation.notna()]
    league = summ.groupby("route").agg(lg_sep=("separation", "mean"), lg_n=("separation", "size")).reset_index()
    lt = summ[summ.targeted]
    league = league.merge(lt.groupby("route").agg(lg_comp=("passResult", lambda x: (x == "C").mean()),
                                                  lg_ypt=("playResult", "mean")).reset_index(), on="route")

    team = aggregate(summ, ["defensiveTeam"]).merge(league, on="route")
    team["raw_delta"] = team.sep - team.lg_sep
    team["vuln"] = team.raw_delta * team.n / (team.n + K)
    team["show"] = team.n >= MIN_N
    # overall team vulnerability: route-volume weighted shrunk delta
    overall = team.groupby("defensiveTeam").apply(lambda d: (d.vuln * d.n).sum() / d.n.sum()).rename("overall").reset_index()
    team = team.merge(overall, on="defensiveTeam")

    cov = aggregate(summ[summ.pff_passCoverageType.isin(["Man", "Zone"])], ["pff_passCoverageType"]).merge(league, on="route")

    team.to_csv(DATA / "team_route_vuln.csv", index=False)
    cov.to_csv(DATA / "coverage_route.csv", index=False)
    league.to_csv(DATA / "league_route.csv", index=False)
    print(league.round(2).to_string())
    print(cov.pivot(index="route", columns="pff_passCoverageType", values="sep").round(2))
    print(team.sort_values("vuln", ascending=False).head(10)[["defensiveTeam", "route", "n", "sep", "vuln", "n_tgt", "comp", "ypt"]].round(2))


if __name__ == "__main__":
    main()
