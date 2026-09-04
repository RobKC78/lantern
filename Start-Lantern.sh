#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  printf 'First-time setup: python3 -m venv .venv\nThen: .venv/bin/python -m pip install -r requirements.txt\n'
  exit 1
fi
exec .venv/bin/python run.py "$@"
