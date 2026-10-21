#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d data_raw/data ] || git clone --depth 1 https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data data_raw
$PY src/build_dataset.py
$PY src/classify_routes.py
$PY src/metrics.py
$PY src/visualize.py
$PY src/build_coach.py
$PY src/make_video.py
ffmpeg -v error -y -i videos/weak_spot_30s.mp4 -vf "fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" -loop 0 videos/weak_spot_30s.gif
