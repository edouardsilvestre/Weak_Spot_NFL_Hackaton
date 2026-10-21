"""Presentation video of the tool: headless-Chrome screenshots of real app states + title cards,
assembled with ffmpeg (pans, captions, fades). Output: videos/weak_spot_coach_demo.mp4"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "videos" / "weak_spot_coach_demo.mp4"
CHROME = "google-chrome"
W, H, FPS = 1280, 720, 30

CSS = """<style>body{margin:0;font-family:Inter,Helvetica,Arial,sans-serif;color:#eef2f8}
.card{width:1280px;height:720px;background:radial-gradient(circle at 30% 20%,#1b2944,#0b1320 70%);display:flex;flex-direction:column;
justify-content:center;padding:0 110px;box-sizing:border-box}.k{color:#f6c90e;font-weight:800;letter-spacing:.12em;font-size:20px;text-transform:uppercase}
h1{font-size:68px;margin:14px 0}h2{font-size:44px;margin:12px 0;line-height:1.2}p{font-size:26px;line-height:1.5;color:#c4cede;margin:10px 0}
b{color:#f6c90e}.row{display:flex;gap:30px;margin-top:26px}.stat{background:#1b2944;border-radius:16px;padding:22px 28px;flex:1}
.stat .v{font-size:60px;font-weight:900}.stat .l{font-size:20px;color:#9aa8c0}
.cap{width:1280px;height:120px;display:flex;align-items:center;justify-content:center}
.cap div{background:rgba(11,19,32,.92);border:2px solid #f6c90e;border-radius:14px;padding:14px 26px;font-size:27px;font-weight:600;max-width:1150px;text-align:center}
.cap span{color:#f6c90e;font-weight:900;margin-right:10px}</style>"""

CARDS = {
    "title": """<div class=card><div class=k>NFL Big Data Bowl · Paris Side Quest</div><h1>WEAK SPOT <span style="color:#f6c90e">· Coach Mode</span></h1>
        <p>L'outil d'appel de la touche, construit sur le tracking Next Gen Stats.</p>
        <p style="font-size:20px;color:#9aa8c0">35 032 tracés de WR, TE et RB · semaines 1 à 8 de 2021</p></div>""",
    "problem": """<div class=card><div class=k>Le problème</div><h2>3e & long. Le coordinateur a 25 secondes.</h2>
        <h2 style="color:#f6c90e">Quel tracé appeler contre <u>cette</u> défense, dans <u>cette</u> situation ?</h2>
        <p>Et en défense : quelle couverture contre cette attaque ?</p></div>""",
    "method": """<div class=card><div class=k>Comment ça marche</div>
        <p>1 · Chaque tracé est classé automatiquement (GO, POST, SLANT, OUT…) à partir du tracking entre le snap et la passe.</p>
        <p>2 · On mesure la <b>séparation</b> au départ du ballon et le <b>taux de succès</b> du jeu.</p>
        <p>3 · Petits échantillons ? <b>Shrinkage hiérarchique</b> : équipe × situation → équipe → ligue × situation → ligue.</p>
        <p>4 · Chaque recommandation affiche son <b>n</b> et un <b>badge de confiance</b>.</p></div>""",
    "insight": """<div class=card><div class=k>L'insight</div><h2>L'espace ne fait pas tout.</h2>
        <div class=row><div class=stat><div class=l>SLANT · le tracé le moins séparé</div><div class=v>2,6 yd</div>
        <div class=l>mais <b>59 %</b> de succès (n=783 ciblages)</div></div>
        <div class=stat><div class=l>GO · bien plus de profondeur</div><div class=v>48 %</div><div class=l>de succès (n=1 028 ciblages)</div></div></div>
        <p style="margin-top:28px">→ Coach Mode classe les appels au <b>taux de succès</b>, pas à la séparation seule.</p></div>""",
    "outro": """<div class=card><div class=k>Essayez-le</div><h1 style="font-size:56px">Ouvrir <span style="color:#f6c90e">coach.html</span></h1>
        <p>Fichier autonome, sans serveur. Analyse de fond : weak_spot.html.</p>
        <p style="font-size:22px">github.com/edouardsilvestre/NFL_BigData_Hackaton_Baptiste_Edouard</p>
        <p style="font-size:18px;color:#9aa8c0;margin-top:30px">Données : 8 premières semaines 2021, jeux de passe uniquement. Ce sont des tendances, pas des certitudes.</p></div>""",
}


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def shot(url, path, w, h, transparent=False):
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--virtual-time-budget=10000",
           f"--window-size={w},{h}", f"--screenshot={path}", url]
    if transparent:
        cmd.insert(1, "--default-background-color=00000000")
    run(cmd)


def html_png(tmp, name, body, w, h, transparent=False):
    f = tmp / f"{name}.html"
    f.write_text(f"<!doctype html><meta charset=utf-8>{CSS}<body style='background:transparent'>{body}</body>", encoding="utf-8")
    png = tmp / f"{name}.png"
    # headless Chrome's viewport is shorter than the window: render taller, then crop to the exact size
    shot(f.as_uri(), png, w, h + 300, transparent)
    Image.open(png).crop((0, 0, w, h)).save(png)
    return png


def segment(out, img, dur, y0=0, y1=0, move=0.0, caption=None, fade_in=True, fade_out=True):
    """Still or vertical pan (eased) over a tall image, with an optional caption at the bottom."""
    ease = f"(0.5-0.5*cos(PI*min(1,t/{move})))" if move else "1"
    vf = f"scale={W}:-2,crop={W}:{H}:0:'min(ih-{H},{y0}+({y1}-{y0})*{ease})'"
    fades = []
    if fade_in:
        fades.append("fade=in:st=0:d=0.4")
    if fade_out:
        fades.append(f"fade=out:st={dur - 0.4}:d=0.4")
    inputs = ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", str(img)]
    if caption:
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", str(caption)]
        fc = f"[0]{vf},setsar=1[bg];[bg][1]overlay=0:{H}-h-18" + ("," + ",".join(fades) if fades else "") + ",format=yuv420p[v]"
    else:
        fc = f"[0]{vf},setsar=1" + ("," + ",".join(fades) if fades else "") + ",format=yuv420p[v]"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-r", str(FPS), "-t", str(dur),
         "-c:v", "libx264", "-preset", "medium", "-crf", "23", str(out)])


def main():
    OUT.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        coach, weak = (ROOT / "coach.html").as_uri(), (ROOT / "weak_spot.html").as_uri()
        att, att_all, dfn, ws = tmp / "att.png", tmp / "att_all.png", tmp / "def.png", tmp / "weak.png"
        shot(coach + "#mode=att&team=PHI&down=3&dist=2", att, W, 2000)
        shot(coach + "#mode=att&team=PHI&down=all&dist=all", att_all, W, 1300)
        shot(coach + "#mode=def&team=KC&down=3&dist=0", dfn, W, 1700)
        shot(weak, ws, W, 2600)
        cards = {k: html_png(tmp, k, v, W, H) for k, v in CARDS.items()}
        cap = lambda n, num, txt: html_png(tmp, f"cap{n}", f"<div class=cap><div><span>{num}</span>{txt}</div></div>", W, 120, True)

        segs = [
            (cards["title"], dict(dur=4.5)),
            (cards["problem"], dict(dur=5.5)),
            (att, dict(dur=5, caption=cap(1, "1", "Mode ATTAQUE : choisissez l'adversaire, le down, la distance et le personnel"), fade_out=False)),
            (att, dict(dur=5, y0=0, y1=170, move=1.5, caption=cap(2, "2", "La phrase prête à dire au QB, et la tendance Man / Zone de la défense"), fade_in=False, fade_out=False)),
            (att, dict(dur=6.5, y0=170, y1=560, move=1.8, caption=cap(3, "3", "Les 3 tracés à appeler : succès estimé, écart vs ligue, n et badge de confiance"), fade_in=False, fade_out=False)),
            (att, dict(dur=5.5, y0=560, y1=1150, move=2.2, caption=cap(4, "4", "Les tracés réels contre PHI dans ce contexte, colorés selon la séparation"), fade_in=False)),
            (att_all, dict(dur=6, y0=150, y1=150, caption=cap(5, "5", "Contexte plus large → plus de jeux → confiance plus élevée (shrinkage hiérarchique)"))),
            (dfn, dict(dur=5.5, caption=cap(6, "6", "Mode DÉFENSE : ce que l'attaque adverse cible, et son receveur clé"), fade_out=False)),
            (dfn, dict(dur=6, y0=0, y1=640, move=2, caption=cap(7, "7", "Les couvertures qui concèdent le moins face à ces tracés, avec n et confiance"), fade_in=False)),
            (cards["method"], dict(dur=8)),
            (cards["insight"], dict(dur=7)),
            (ws, dict(dur=8, y0=0, y1=900, move=5, caption=cap(8, "+", "Analyse de fond : la Weak Spot Matrix, 32 défenses × 11 tracés"))),
            (ROOT / "figures" / "play_at_pass.png", dict(dur=5.5, y0=40, y1=40, caption=cap(9, "+", "Exemple réel : Godwin sur un GO contre ATL, 3,1 yd d'espace, 26 yards"))),
            (cards["outro"], dict(dur=6)),
        ]
        parts = []
        for i, (img, kw) in enumerate(segs):
            p = tmp / f"seg{i:02d}.mp4"
            segment(p, img, **kw)
            parts.append(p)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(OUT)])
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
