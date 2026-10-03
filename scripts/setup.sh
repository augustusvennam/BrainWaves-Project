#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm install
if [ ! -f .env ]; then cp .env.example .env; fi
printf '\nSetup complete. Edit .env, then run npm run dev.\n'
