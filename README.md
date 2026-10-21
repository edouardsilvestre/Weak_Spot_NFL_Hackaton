# Weak Spot

> ### Down. Distance. Personnel. Trois choix, un appel.

**Point Faible transforme les données de tracking de votre adversaire en votre prochain appel de jeu.**

Réglez le moment du match (down, distance, personnel), et Point Faible vous donne la réponse des deux côtés du ballon :

- **Mode attaque** : il affiche instantanément les tracés contre lesquels sa défense laisse le plus d'espace.
- **Mode défense** : il vous donne la couverture qui neutralise le mieux les tracés favoris de son attaque dans cette situation précise.

L'outil fonctionne des deux côtés du ballon parce qu'il étudie une seule chose : **comment cet adversaire précis se comporte dans cette situation précise**, à partir de chaque tracé couru dans les données de tracking Next Gen Stats.

> **Exemple** : sur 3e & long, PHI joue en zone sur 93 % des jeux (n=31). Toutes situations confondues, contre HOU, le GO laisse 3,7 yd de séparation contre 2,8 yd pour la ligue (n=175 tracés), pour 58 % de complétion (ligue : 44 %).

Pas de tableur, pas de séance vidéo : choisissez la situation, lisez la carte, transmettez l'appel.

---

## Vidéo

[**Regarder la présentation (30 s)**](videos/weak_spot_30s.mp4)

## Aperçu

| Mode attaque : 3e & long vs PHI | Mode défense : 3e & court vs KC |
|---|---|
| ![Mode attaque](figures/coach_att.png) | ![Mode défense](figures/coach_def.png) |

## Lancer l'outil

```bash
pip install -r requirements.txt && ./run_all.sh
open coach.html        # Coach Mode : fonctionne hors ligne, sans serveur (xdg-open sous Linux)
```

`coach.html` est déjà généré dans le repo : on peut l'ouvrir directement, sans rien installer. `weak_spot.html` contient l'analyse de fond (matrice des 32 défenses × 11 tracés, scouting cards, man vs zone).

## Sous le capot

| Étape | Fichier | Rôle |
|---|---|---|
| 1 | `src/build_dataset.py` | Frames entre le snap et la passe, normalisées. Séparation = distance au défenseur le plus proche au moment de la passe. |
| 2 | `src/classify_routes.py` | Classification géométrique des tracés en 11 familles (GO, POST, SLANT, OUT…). |
| 3 | `src/metrics.py` | Vulnérabilité par défense × tracé et par situation, avec shrinkage bayésien empirique. |
| 4 | `src/build_coach.py` | Table compacte embarquée dans `coach.html`. Le filtrage et le shrinkage hiérarchique (équipe × situation → équipe → ligue × situation → ligue, k=15) se font dans le navigateur. |
| 5 | `src/make_video.py` | Vidéo de présentation générée image par image à partir des vraies trajectoires médianes. |

Chaque recommandation affiche son **n** et un **badge de confiance** (Élevée n ≥ 30, Moyenne 10–29, Faible < 10).

## Limites

- Données : 8 premières semaines de 2021, jeux de passe uniquement.
- Séparation mesurée au moment de la passe, pas à la réception.
- Classification des tracés par règles géométriques : les tracés ambigus sont exclus.
- Les contextes très filtrés ont peu de jeux : la recommandation s'appuie alors surtout sur la tendance de l'équipe et de la ligue, ce que le badge de confiance indique.
