#!/usr/bin/env bash
set -euo pipefail

export SCOUT_MAX_PRICE="${SCOUT_MAX_PRICE:-1200}"
export SCOUT_MAX_SEED_PAGES="${SCOUT_MAX_SEED_PAGES:-10}"
export SCOUT_MIN_SCORE="${SCOUT_MIN_SCORE:-5}"
export SCOUT_OUTPUT_DIR="artifacts/used-pc-scout"
export SCOUT_CRAWL_DIR=".crawl/used-pc-scout"

python -m pip install --upgrade pip
python -m pip install -e ".[fetchers]"
python -m pip install pytest

python -m pytest -q tests/campaigns/test_used_pc_scout.py
python campaigns/used_pc_scout/run.py

test -s artifacts/used-pc-scout/report.md
test -s artifacts/used-pc-scout/candidates.json
test -s artifacts/used-pc-scout/stats.json

sed -n '1,140p' artifacts/used-pc-scout/report.md
