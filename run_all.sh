#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d data_raw/data ] || git clone --depth 1 https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data data_raw
$PY src/build_dataset.py
$PY src/classify_routes.py
$PY src/metrics.py
$PY src/visualize.py
