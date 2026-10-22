#!/usr/bin/env bash
# One-time setup: virtualenv, dependencies, .env, then a config check.
set -e
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  uv venv -q .venv && uv pip install -q -p .venv/bin/python -r requirements.txt
else
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
echo "Installed. Config check:"
.venv/bin/python audit.py --doctor
echo
echo "Next: edit .env if you have keys, then"
echo '  .venv/bin/python audit.py https://www.example.org --city "City, ST" --brand "Facility Name"'
