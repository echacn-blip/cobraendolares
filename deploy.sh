#!/usr/bin/env bash
# Refresca datos, regenera site/ (diseño v2 incluido en assets/ + scripts/build.py) y publica en GitHub Pages sin Actions.
set -euo pipefail
cd "$(dirname "$0")"
git checkout -q main
git pull -q --ff-only origin main || true
./run.sh "$@"
git add -A
git diff --cached --quiet || git commit -qm "refresh $(date '+%Y-%m-%d %H:%M')"
git push -q origin main
git push -q --force origin "$(git subtree split --prefix site main)":refs/heads/gh-pages
gh api -X POST repos/echacn-blip/cobraendolares/pages/builds --jq .status
