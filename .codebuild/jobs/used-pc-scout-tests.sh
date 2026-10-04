#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -e ".[fetchers]"
python -m pip install pytest

python -m pytest -q tests/campaigns/test_used_pc_scout.py
python -m py_compile   campaigns/used_pc_scout/scoring.py   campaigns/used_pc_scout/marketplaces.py   campaigns/used_pc_scout/scout.py   campaigns/used_pc_scout/run.py

mkdir -p artifacts/used-pc-scout-tests
printf '{"ok":true}\n' > artifacts/used-pc-scout-tests/result.json
