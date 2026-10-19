#!/usr/bin/env bash
# Refresca datos (tipos de cambio, Wise, historial, páginas oficiales, noticias) y regenera site/.
set -euo pipefail
cd "$(dirname "$0")"
VENV_PY=${NEWS_PY:-/workspace/cobraendolares-news/.venv/bin/python}
if [ -x "$VENV_PY" ]; then
  python3 scripts/refresh.py --no-news "$@"
  "$VENV_PY" scripts/fetch_news.py || python3 scripts/refresh.py --no-pages   # respaldo: RSS propio
else
  python3 scripts/refresh.py "$@"
fi
python3 scripts/build.py
