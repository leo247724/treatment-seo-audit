#!/usr/bin/env bash
# One-time setup: virtualenv, dependencies, .env, then a config check.
set -e
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  # Re-running setup must not fail on (or wipe) an existing .venv.
  [ -x .venv/bin/python ] || uv venv -q .venv
  uv pip install -q -p .venv/bin/python -r requirements.txt
else
  [ -x .venv/bin/python ] || python3 -m venv .venv
  .venv/bin/python -m pip install -q -r requirements.txt
fi
[ -f .env ] || [ ! -f .env.example ] || cp .env.example .env
echo "Installed. Config check:"
.venv/bin/python audit.py --doctor
echo
echo "Next: edit .env if you have keys, then"
echo '  .venv/bin/python audit.py https://www.example.org --city "City, ST" --brand "Facility Name"'
