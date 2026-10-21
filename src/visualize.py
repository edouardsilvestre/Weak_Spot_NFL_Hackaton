"""Weak Spot visuals: heatmap, per-team scouting card on a drawn field, man vs zone bars."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"

ROUTES = ["GO", "POST", "CORNER", "SLANT", "IN/DIG", "OUT", "HITCH/CURL", "FLAT", "SCREEN",
          "RB WHEEL/ANGLE", "RB CHECKDOWN"]
TEAMS = {"ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
         "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
         "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
         "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
         "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
         "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
         "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
         "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington"}
FONT = dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color="#1f2430")
RED, BLUE = "#c8102e", "#1d4e89"
# separation bins (yards) -> color, tight (red) to wide open (green)
SEP_BINS = [(0, 1.5, "#d7263d", "< 1,5 yd"), (1.5, 2.5, "#f46036", "1,5–2,5 yd"), (2.5, 3.5, "#f6c90e", "2,5–3,5 yd"),
            (3.5, 5, "#8bc34a", "3,5–5 yd"), (5, 99, "#1b998b", "> 5 yd")]


def fr(x, d=1):
    x = 0.0 if abs(x) < 0.05 else x
    return f"{x:+.{d}f}".replace(".", ",")


def dec(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def pct(x):
    return "–" if pd.isna(x) else f"{x*100:.0f} %"


def recommendation(team, tv):
    t = tv[(tv.defensiveTeam == team) & tv.show].sort_values("vuln", ascending=False)
    return t.head(3)


def sentence(team, top):
    r = top.iloc[0]
    comp = f", {pct(r.comp)} de complétion sur {r.n_tgt} ciblages" if r.n_tgt >= 5 else ""
    if r.raw_delta < 0.15:
        return (f"{team} ne laisse aucun tracé ouvert : même son point le moins solide, le <b>{r.route}</b>, "
                f"est au niveau de la ligue ({fr(r.raw_delta)} yd{comp}, n={r.n})")
    return (f"Contre {team}, attaquez avec le <b>{r.route}</b> : {fr(r.raw_delta)} yd de séparation vs la ligue"
            f"{comp} (n={r.n} tracés)")


# ---------- A. heatmap ----------
def heatmap(tv):
    order = tv.drop_duplicates("defensiveTeam").sort_values("overall", ascending=True).defensiveTeam.tolist()
    piv = lambda col: tv.pivot(index="defensiveTeam", columns="route", values=col).reindex(index=order, columns=ROUTES)
    z = piv("vuln").where(piv("show") == True)
    custom = np.dstack([piv(c).to_numpy(dtype=float) for c in ["n", "sep", "lg_sep", "comp", "ypt", "n_tgt", "raw_delta"]])
    text = z.map(lambda v: "" if pd.isna(v) else f"{v:+.1f}")
    worst = order[-1]
    wtop = recommendation(worst, tv).iloc[0]
    fig = go.Figure(go.Heatmap(
        z=z.to_numpy(), x=[r.replace("RB ", "RB<br>").replace("/", "/<br>") for r in ROUTES], y=[f"{t} · {TEAMS.get(t, t)}" for t in order], customdata=custom,
        text=text.to_numpy(), texttemplate="%{text}", textfont=dict(size=10),
        colorscale=[[0, BLUE], [0.5, "#f7f7f7"], [1, RED]], zmid=0, zmin=-0.8, zmax=0.8,
        xgap=2, ygap=2,
        colorbar=dict(title=dict(text="Yards d'espace<br>en plus que la ligue", side="right"), thickness=14,
                      tickvals=[-0.8, -0.4, 0, 0.4, 0.8], ticktext=["−0,8 (verrouillé)", "−0,4", "0", "+0,4", "+0,8 (ouvert)"]),
        hovertemplate="<b>%{y}</b> contre le <b>%{x}</b><br>Séparation à la passe : %{customdata[1]:.2f} yd "
                      "(ligue %{customdata[2]:.2f})<br>Écart brut : %{customdata[6]:+.2f} yd · score ajusté : %{z:+.2f}"
                      "<br>Tracés : %{customdata[0]:.0f} · ciblés : %{customdata[5]:.0f}"
                      "<br>Complétion : %{customdata[3]:.0%} · Yards/cible : %{customdata[4]:.1f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"<b>Weak Spot Matrix — où chaque défense NFL laisse de l'espace</b><br>"
                        f"<sup>Rouge = le receveur est plus ouvert que contre la moyenne de la ligue au moment de la passe.<br>"
                        f"Défenses les plus perméables en haut. {worst} : {wtop.route} {fr(wtop.raw_delta)} yd vs la ligue.</sup>",
                   x=0.01, font=dict(size=20)),
        font=FONT, height=1050, width=1150, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(side="top", tickangle=0, tickfont=dict(size=11, color="#1f2430"), title=None),
        yaxis=dict(tickfont=dict(size=11), autorange=True),
        margin=dict(l=210, r=40, t=170, b=40),
    )
    fig.add_annotation(text="Cellules vides : moins de 10 tracés. Score = écart de séparation vs ligue, rétréci vers 0 pour les petits échantillons (k=20). Semaines 1–8, 2021.",
                       xref="paper", yref="paper", x=0, y=-0.035, showarrow=False, font=dict(size=11, color="#666"), xanchor="left")
    return fig, order


# ---------- B. scouting card ----------
def field_shapes(x0=-8, x1=30):
    """Vertical field: sideline to sideline on x (0-53.3), yards past the LOS on y."""
    W = 53.3
    shapes = [dict(type="rect", x0=0, x1=W, y0=x0, y1=x1, fillcolor="#3a7d44", line=dict(width=0), layer="below")]
    for i, y in enumerate(range(x0 - x0 % 5, x1, 5)):
        if i % 2 == 0:
            shapes.append(dict(type="rect", x0=0, x1=W, y0=max(y, x0), y1=min(y + 5, x1), fillcolor="#367340", line=dict(width=0), layer="below"))
    for y in range(x0 - x0 % 5 + 5, x1, 5):
        shapes.append(dict(type="line", y0=y, y1=y, x0=0, x1=W, line=dict(color="rgba(255,255,255,0.7)", width=1.5), layer="below"))
    for y in range(x0, x1 + 1):  # hash marks
        for xh in (0.6, 23.4, 29.9, 52.7):
            shapes.append(dict(type="line", y0=y, y1=y, x0=xh - 0.5, x1=xh + 0.5, line=dict(color="rgba(255,255,255,0.6)", width=1), layer="below"))
    shapes.append(dict(type="line", y0=0, y1=0, x0=0, x1=W, line=dict(color="#2d6cdf", width=3), layer="below"))
    shapes.append(dict(type="rect", x0=0, x1=W, y0=x0, y1=x1, line=dict(color="white", width=3), fillcolor="rgba(0,0,0,0)"))
    annots = []
    for y in range(10, x1, 10):
        for xx, rot in ((5, -90), (48.3, 90)):
            annots.append(dict(x=xx, y=y, text=f"<b>{y}</b>", showarrow=False, textangle=rot,
                               font=dict(size=20, color="rgba(255,255,255,0.85)", family="Georgia, serif")))
    annots.append(dict(x=W + 0.5, y=0, text="ligne de<br>scrimmage", showarrow=False, font=dict(size=11, color="#2d6cdf"), xanchor="left", align="left"))
    annots.append(dict(x=W + 0.5, y=x1 - 1, text="sens de<br>l'attaque ↑", showarrow=False, font=dict(size=11, color="#555"), xanchor="left", align="left"))
    return shapes, annots


def scouting_card(tv, summ, routes, order):
    rng = np.random.default_rng(0)
    teams = sorted(tv.defensiveTeam.unique(), key=lambda t: order.index(t), reverse=True)
    shapes, base_ann = field_shapes()
    traces, vis_groups, layouts = [], [], []
    rk = routes.set_index(["gameId", "playId", "nflId"]).sort_index()
    for team in teams:
        idx0 = len(traces)
        top = recommendation(team, tv)
        sub = summ[(summ.defensiveTeam == team) & summ.route.isin(ROUTES)]
        smp = sub.sample(frac=1, random_state=1).groupby("route").head(12)
        hi = set(top.route)
        for lo, hi_, col, lab in SEP_BINS:
            s = smp[(smp.separation >= lo) & (smp.separation < hi_) & ~smp.route.isin(hi)]
            xs, ys = [], []
            for k in s[["gameId", "playId", "nflId"]].itertuples(index=False):
                g = rk.loc[tuple(k)]
                xs += g.y.tolist() + [None]; ys += g.x_los.tolist() + [None]
            traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=col, width=1.2), opacity=0.3,
                                     showlegend=False, hoverinfo="skip"))
        for rank, r in enumerate(top.itertuples(), 1):
            s = smp[smp.route == r.route]
            for lo, hi_, col, lab in SEP_BINS:
                ss = s[(s.separation >= lo) & (s.separation < hi_)]
                xs, ys = [], []
                for k in ss[["gameId", "playId", "nflId"]].itertuples(index=False):
                    g = rk.loc[tuple(k)]
                    xs += g.y.tolist() + [None]; ys += g.x_los.tolist() + [None]
                traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=col, width=4), opacity=1,
                                         showlegend=False, hoverinfo="skip"))
            ends = s.merge(routes.groupby(["gameId", "playId", "nflId"]).tail(1)[["gameId", "playId", "nflId", "x_los", "y"]],
                           on=["gameId", "playId", "nflId"])
            ex, ey = ends.y.median(), ends.x_los.median()
            txt = (f"#{rank} {r.route}<br>{fr(r.raw_delta)} yd vs ligue · n={r.n}"
                   + (f"<br>{pct(r.comp)} compl. · {r.ypt:.1f} yd/cible" if r.n_tgt >= 5 else ""))
            traces.append(go.Scatter(x=[ex], y=[ey], mode="markers+text", text=[f"<b>{rank}</b>"],
                                     marker=dict(size=24, color="white", line=dict(color="#111", width=2)),
                                     textfont=dict(size=13, color="#111"), showlegend=False,
                                     hovertemplate=txt + "<extra></extra>"))
        vis_groups.append((idx0, len(traces)))
        side = "<br>".join(
            f"<b>#{i} {r.route}</b> — {fr(r.raw_delta)} yd vs ligue, n={r.n}"
            + (f", {pct(r.comp)} compl., {r.ypt:.1f} yd/cible" if r.n_tgt >= 5 else "")
            for i, r in enumerate(top.itertuples(), 1))
        layouts.append(dict(
            title=dict(text=f"<b>Scouting card — {TEAMS.get(team, team)} ({team})</b><br><sup>{sentence(team, top)}</sup>",
                       x=0.01, font=dict(size=20)),
            annotations=base_ann + [dict(text=side, xref="paper", yref="paper", x=0, y=-0.08, showarrow=False,
                                         align="left", xanchor="left", yanchor="top", font=dict(size=13))]))
    for lo, hi_, col, lab in SEP_BINS:  # legend entries, always visible
        traces.append(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=col, width=4), name=lab))
    fig = go.Figure(traces)
    n = len(traces)
    n_leg = len(SEP_BINS)
    buttons = []
    for team, (a, b), lay in zip(teams, vis_groups, layouts):
        vis = [a <= i < b or i >= n - n_leg for i in range(n)]
        buttons.append(dict(label=f"{team} · {TEAMS.get(team, team)}", method="update", args=[{"visible": vis}, lay]))
    a, b = vis_groups[0]
    for i, t in enumerate(fig.data):
        t.visible = a <= i < b or i >= n - n_leg
    fig.update_layout(**layouts[0], shapes=shapes, font=FONT, width=1150, height=980,
                      plot_bgcolor="white", paper_bgcolor="white",
                      xaxis=dict(range=[-1, 62], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
                      yaxis=dict(range=[-8.5, 30.5], showgrid=False, zeroline=False, showticklabels=False,
                                 scaleanchor="x", scaleratio=1, fixedrange=True),
                      legend=dict(title="Séparation à la passe", orientation="h", y=-0.01, x=1, xanchor="right", yanchor="top"),
                      updatemenus=[dict(buttons=buttons, direction="down", x=1, xanchor="right", y=1.13, yanchor="top",
                                        bgcolor="white", font=dict(size=12))],
                      margin=dict(l=20, r=20, t=110, b=130))
    return fig, teams


# ---------- C. man vs zone ----------
def man_vs_zone(cov):
    p = cov.pivot(index="route", columns="pff_passCoverageType", values="sep").reindex(ROUTES)
    nn = cov.pivot(index="route", columns="pff_passCoverageType", values="n").reindex(ROUTES)
    wr = p.drop(["SCREEN", "RB CHECKDOWN", "RB WHEEL/ANGLE"])
    keep = (wr.Man / wr.Zone)
    best_man = wr.Man.idxmax()
    worst_man = wr.Man.idxmin()
    second = wr.Man.drop(best_man).idxmax()
    order = p.sort_values("Man", ascending=False).index.tolist()
    fig = go.Figure()
    for cv, col in (("Man", RED), ("Zone", BLUE)):
        fig.add_bar(x=order, y=p.loc[order, cv], name=f"vs {cv.lower() if cv == 'Zone' else 'man'}", marker_color=col,
                    text=[f"{v:.1f}".replace(".", ",") for v in p.loc[order, cv]], textposition="outside",
                    customdata=nn.loc[order, cv],
                    hovertemplate="%{x} vs " + cv + " : %{y:.2f} yd (n=%{customdata})<extra></extra>")
    fig.update_layout(
        title=dict(text=f"<b>La man coupe {(1 - keep.mean())*100:.0f} % de l'espace : contre elle, visez le {best_man} "
                        f"({dec(wr.Man.max())} yd) et le {second} ({dec(wr.Man[second])} yd), oubliez le {worst_man} ({dec(wr.Man.min())} yd)</b><br>"
                        f"<sup>Séparation moyenne au moment de la passe selon la couverture (hors screens et tracés de RB). "
                        f"Le {keep.idxmax()} est le tracé qui perd le moins d'espace face à la man (−{(1 - keep.max())*100:.0f} %).</sup>",
                   x=0.01, font=dict(size=19)),
        barmode="group", font=FONT, width=1150, height=560, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(title="Yards jusqu'au défenseur le plus proche", gridcolor="#eee", zeroline=False),
        xaxis=dict(title=None), legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"),
        margin=dict(l=70, r=30, t=110, b=60), bargap=0.25)
    return fig, dict(best_man=best_man, best_man_sep=wr.Man.max(), worst_man=worst_man,
                     keep_best=keep.idxmax(), drop_mean=1 - keep.mean())


# ---------- D. animated real play ----------
def play_animation(tv, summ, team):
    top = recommendation(team, tv).iloc[0]
    c = summ[(summ.defensiveTeam == team) & (summ.route == top.route) & summ.targeted & (summ.passResult == "C")
             & (summ.separation >= top.lg_sep)].sort_values("playResult", ascending=False).iloc[0]
    trk = pd.read_csv(ROOT / "data_raw" / "data" / "tracking" / f"tracking_{c.gameId}.csv",
                      usecols=["playId", "nflId", "frameId", "team", "playDirection", "x", "y", "jerseyNumber", "event"])
    trk = trk[trk.playId == c.playId].copy()
    left = trk.playDirection == "left"
    trk.loc[left, "x"] = 120 - trk.loc[left, "x"]
    trk.loc[left, "y"] = 53.3 - trk.loc[left, "y"]
    snap = trk[trk.event.isin(["ball_snap", "autoevent_ballsnap"])].frameId.min()
    pas = trk[trk.event.isin(["pass_forward", "autoevent_passforward"])].frameId.min()
    trk = trk[trk.frameId >= snap - 5]
    los = trk[(trk.team == "football") & (trk.frameId == snap)].x.iloc[0]
    trk["X"], trk["Y"] = trk.y, trk.x - los   # vertical field, offense going up
    frames_ids = sorted(trk.frameId.unique())
    trail = trk[(trk.nflId == c.nflId)]

    def frame_data(f):
        d = trk[trk.frameId == f]
        off = d[d.team == c.possessionTeam]
        de = d[(d.team != c.possessionTeam) & (d.team != "football")]
        ball = d[d.team == "football"]
        tr = trail[trail.frameId <= f]
        tgt = d[d.nflId == c.nflId]
        return [
            go.Scatter(x=tr.X, y=tr.Y, mode="lines", line=dict(color="#f6c90e", width=4), name=f"Tracé de {c.displayName}"),
            go.Scatter(x=off.X, y=off.Y, mode="markers+text", text=off.jerseyNumber.astype("Int64").astype(str),
                       marker=dict(size=20, color="white", line=dict(color="#111", width=1.5)),
                       textfont=dict(size=9, color="#111"), name=f"Attaque ({c.possessionTeam})"),
            go.Scatter(x=de.X, y=de.Y, mode="markers+text", text=de.jerseyNumber.astype("Int64").astype(str),
                       marker=dict(size=20, color=RED, line=dict(color="white", width=1.5)),
                       textfont=dict(size=9, color="white"), name=f"Défense ({team})"),
            go.Scatter(x=tgt.X, y=tgt.Y, mode="markers", marker=dict(size=30, color="rgba(0,0,0,0)",
                       line=dict(color="#f6c90e", width=3)), showlegend=False),
            go.Scatter(x=ball.X, y=ball.Y, mode="markers", marker=dict(size=11, color="#8b4513", symbol="diamond",
                       line=dict(color="white", width=1)), name="Ballon"),
        ]

    shapes, ann = field_shapes(-12, 40)
    fig = go.Figure(data=frame_data(frames_ids[0]),
                    frames=[go.Frame(data=frame_data(f), name=str(f),
                                     layout=dict(annotations=ann + ([dict(x=26.65, y=-10, text="<b>PASSE !</b>", showarrow=False,
                                                 font=dict(size=22, color="#f6c90e"))] if f >= pas else [])))
                            for f in frames_ids])
    desc = c.playDescription.split(") ", 1)[-1] if ")" in c.playDescription else c.playDescription
    fig.update_layout(
        title=dict(text=f"<b>Le weak spot en action : {top.route} contre {TEAMS.get(team, team)}</b><br>"
                        f"<sup>{c.displayName} ({c.possessionTeam}) a {dec(c.separation)} yd d'espace au départ du ballon "
                        f"(ligue sur ce tracé : {dec(top.lg_sep)} yd), {c.pff_passCoverage}. {desc}</sup>",
                   x=0.01, font=dict(size=19)),
        shapes=shapes, annotations=ann, font=FONT, width=1150, height=1000, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(range=[-1, 62], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(range=[-12.5, 40.5], showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", fixedrange=True),
        legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=110, b=110),
        updatemenus=[dict(type="buttons", x=0, y=-0.08, xanchor="left", direction="left", buttons=[
            dict(label="▶ Jouer", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="❚❚ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=0, x=0.2, len=0.8, y=-0.06, currentvalue=dict(prefix="t = ", suffix=" s après le snap"),
                      steps=[dict(label=f"{(f - snap) / 10:.1f}", method="animate",
                                  args=[[str(f)], dict(frame=dict(duration=0, redraw=True), mode="immediate")]) for f in frames_ids])],
    )
    still = go.Figure(fig)
    still.update(data=frame_data(pas))
    still.layout.updatemenus, still.layout.sliders, still.layout.height = (), (), 900
    return fig, still


def main():
    tv = pd.read_csv(DATA / "team_route_vuln.csv")
    cov = pd.read_csv(DATA / "coverage_route.csv")
    summ = pd.read_parquet(DATA / "route_summary.parquet")
    routes = pd.read_parquet(DATA / "routes.parquet", columns=["gameId", "playId", "nflId", "frameId", "x_los", "y"])
    FIG.mkdir(exist_ok=True)
    fa, order = heatmap(tv)
    fb, teams = scouting_card(tv, summ, routes, order)
    fc, mz = man_vs_zone(cov)
    fd, fd_still = play_animation(tv, summ, order[-1])

    head = ("<!doctype html><html><head><meta charset='utf-8'><title>Weak Spot</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{font-family:Inter,Helvetica,Arial,sans-serif;background:#fafafa;color:#1f2430;margin:0}"
            ".wrap{max-width:1180px;margin:0 auto;padding:24px 16px}h1{font-size:34px;margin:8px 0}"
            ".lead{font-size:17px;line-height:1.5;max-width:900px}.card{background:white;border-radius:10px;"
            "box-shadow:0 1px 4px rgba(0,0,0,.08);margin:24px 0;padding:8px;overflow-x:auto}</style></head><body><div class='wrap'>")
    worst = order[-1]
    wt = recommendation(worst, tv).iloc[0]
    intro = (f"<h1>Weak Spot</h1><p class='lead'>Le scouting report des tracés les moins bien défendus. "
             f"Pour chaque défense NFL (semaines 1–8, 2021, tracking Next Gen Stats), on classe chaque tracé de WR, TE et RB "
             f"et on mesure l'espace entre le receveur et le défenseur le plus proche <b>au moment où le ballon part</b>. "
             f"Exemple : {sentence(worst, recommendation(worst, tv))}.</p>")
    body = [head, intro]
    for i, f in enumerate([fa, fb, fc, fd]):
        body.append("<div class='card'>" + f.to_html(full_html=False, include_plotlyjs="inline" if i == 0 else False,
                                                    config={"displaylogo": False}) + "</div>")
    body.append("</div></body></html>")
    (ROOT / "weak_spot.html").write_text("\n".join(body), encoding="utf-8")

    fa.write_image(FIG / "weak_spot_matrix.png", scale=2)
    fc.write_image(FIG / "man_vs_zone.png", scale=2)
    fd_still.write_image(FIG / "play_at_pass.png", scale=2)
    # static scouting card for the README: the most vulnerable defense
    fb_png = go.Figure(fb)
    idx = teams.index(worst)
    fb_png.update_layout(updatemenus=[], **{k: v for k, v in fb.layout.updatemenus[0].buttons[idx].args[1].items()})
    for i, t in enumerate(fb_png.data):
        t.visible = fb.layout.updatemenus[0].buttons[idx].args[0]["visible"][i]
    fb_png.write_image(FIG / f"scouting_card_{worst}.png", scale=2)
    print("worst defense:", worst, "|", sentence(worst, recommendation(worst, tv)))
    print("man vs zone:", mz)


if __name__ == "__main__":
    main()
