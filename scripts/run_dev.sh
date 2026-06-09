#!/usr/bin/env bash
# Local development runner.
set -e

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -r requirements.txt

python scripts/setup_db.py
python run.py
