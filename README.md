# Weak Spot : quels tracés courir contre chaque défense NFL ?

**Weak Spot – Coach Mode** est un outil d'appel en direct pour la tablette de la touche, construit sur le tracking Next Gen Stats (semaines 1 à 8 de 2021). Le coach choisit l'adversaire, le down, la distance et le personnel. En mode **ATTAQUE**, il obtient les 3 tracés à appeler, la tendance man/zone de la défense et l'arbre des tracés réels. En mode **DÉFENSE**, il obtient les couvertures qui concèdent le moins face aux tracés que cette attaque cible. Chaque estimation est rétrécie hiérarchiquement (équipe × situation → équipe → ligue × situation → ligue, k=15) et porte un badge de confiance avec son n. Nous classons au **taux de succès** plutôt qu'à la séparation seule, car les deux divergent : le SLANT est le tracé le moins séparé de la ligue (2,6 yd au moment de la passe) mais le plus efficace, avec **59 % de succès (n=783 ciblages) contre 48 % pour le GO (n=1 028)**.

🎥 **[Vidéo de présentation (84 s)](videos/weak_spot_coach_demo.mp4)**. Elle est régénérable avec `python src/make_video.py` (Chrome et ffmpeg requis).

**▶ Ouvrir `coach.html`** (fichier autonome, sans serveur : téléchargez-le puis ouvrez-le dans un navigateur).

| Mode ATTAQUE (3e & long vs PHI) | Mode DÉFENSE (3e & court vs KC) |
|---|---|
| ![Coach mode attaque](figures/coach_att.png) | ![Coach mode défense](figures/coach_def.png) |

## Analyse de fond : `weak_spot.html`

À partir de 35 032 tracés classés en 11 familles, nous mesurons la **séparation au moment où le ballon part**. Contre **Houston, le GO laisse 3,7 yd d'espace contre 2,8 yd pour la ligue**, pour **58 % de complétion (ligue : 44 %) et 16,1 yards par cible (ligue : 12,1)**. Face à la man, la séparation chute de 44 % en moyenne. En 3e & long, le FLAT est le tracé le plus ouvert (5,2 yd, n=215 tracés) mais ne convertit que 20 % de ses ciblages (n=45), contre 43 % pour le SLANT (n=94) et 52 % pour le POST (n=44).

**Interface coach** : téléchargez et ouvrez [`weak_spot.html`](weak_spot.html), un fichier autonome qui ne demande pas de serveur. Le coach choisit la **défense adverse** et la **situation** (Tous / 1er-2e down / 3e & court ≤3 yds / 3e & long ≥7 yds). Il obtient aussitôt les 3 tracés à appeler, la tendance man/zone de l'adversaire et, sur 3e down, les tracés qui convertissent. Les mêmes menus mettent à jour la heatmap (cellules grises si n < 10, n au survol), la comparaison Man vs Zone et la scouting card. La page se termine par l'animation d'un vrai jeu.

![Weak Spot Matrix](figures/weak_spot_matrix.png)

![Scouting card ATL](figures/scouting_card_ATL.png)

![Man vs Zone](figures/man_vs_zone.png)

La même matrice filtrée sur **3e & long** (scores recalculés contre la moyenne de la ligue dans cette situation) :

![Weak Spot Matrix 3e & long](figures/weak_spot_matrix_3rd_long.png)

Le weak spot en action : Chris Godwin sur un GO contre ATL (Cover-2), avec 3,1 yd d'espace au moment de la passe, pour un gain de 26 yards. Le HTML contient la version animée.

![Jeu au moment de la passe](figures/play_at_pass.png)

## Comment lancer

```bash
pip install -r requirements.txt
./run_all.sh   # clone les données si besoin, puis dataset → classification → métriques → visuels → coach.html (~2 min)
```

## Méthode

1. `src/build_dataset.py` : ne garde que les frames entre le snap et la passe, oriente toujours l'attaque vers la droite et exprime chaque tracé par rapport à la position du joueur au snap (latéral + = vers la ligne de touche). Calcule aussi la distance au défenseur le plus proche à la frame de la passe, et retrouve le receveur ciblé dans `playDescription`.
2. `src/classify_routes.py` : règles géométriques lisibles (profondeur à la passe, cap sur les 0,6 dernières secondes, profondeur de la cassure, retour vers le QB). Les cas ambigus vont dans `OTHER` (18 %). Le contrôle visuel est dans [`figures/route_tree_check.png`](figures/route_tree_check.png).
3. `src/metrics.py` : vulnérabilité = séparation de la défense moins séparation de la ligue sur ce tracé, avec un shrinkage bayésien empirique `Δ·n/(n+20)`. Les cellules où n < 10 sont grisées. Tout est recalculé pour chaque situation de down et distance, en comparant à la ligue dans cette même situation.
4. `src/visualize.py` : produit `weak_spot.html` et les PNG.
5. `src/build_coach.py` et `src/coach_template.html` : exportent une table compacte (une ligne par tracé : défense, attaque, down, distance, personnel, couverture, tracé, séparation, succès) en JSON embarqué. Le filtrage et le shrinkage hiérarchique sont faits en JS vanilla. Succès = gain ≥ 40 % de la distance au 1er down, ≥ 60 % au 2e, 100 % aux 3e et 4e.

## Limites

- Seulement 8 semaines de données (environ 1 100 tracés par défense, beaucoup moins par situation : en 3e & court, la plupart des cellules sont grisées) : certaines cellules restent bruitées malgré le shrinkage.
- La séparation est mesurée **au moment de la passe**, pas à la réception (le tracking s'arrête peu après). Elle ne tient pas compte de la position du défenseur (devant ou derrière le receveur).
- La classification par règles reste approximative : les tracés interrompus par une passe rapide finissent dans `OTHER`, et les combinaisons ou les option routes ne sont pas distinguées.
- Dans le Coach Mode, la plupart des contextes croisés (équipe × down × distance × personnel) ont moins de 10 ciblages : la recommandation repose alors surtout sur la tendance de l'équipe et de la ligue, et le badge « Faible » l'indique.
- Ce sont des associations, pas des effets causaux : le contexte (down, distance, qualité du QB adverse) n'est pas contrôlé.
