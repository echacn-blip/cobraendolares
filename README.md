# CobraEnDólares

Comparador en español de cuánto te llega **de verdad** cuando te pagan desde el exterior: Payoneer, Wise, DolarApp (ARQ), Global66, Takenos, Littio, Deel y Airtm en México, Colombia, Perú, Chile y Argentina.

Sitio estático (Python stdlib) publicado en GitHub Pages desde la rama `gh-pages` (sin GitHub Actions).
En vivo: https://echacn-blip.github.io/cobraendolares/

## Datos
- Comisiones: `scripts/seed_providers.py` → `data/providers.json`. Solo páginas oficiales o centros de ayuda, con URL y fecha por campo. "sin verificar" / "margen no publicado" cuando no hay dato publicado.
- Tipo medio: fawazahmed0/currency-api (jsDelivr) con respaldo open.er-api.com.
- Argentina y dólares LatAm: DolarAPI; historia 30 días AR: ArgentinaDatos.
- Wise: API pública de comparaciones (sin clave).
- Noticias: `scripts/fetch_news.py` (19 feeds RSS, categorías remesas/dólar/fintech/impuestos).
- Historial de cambios: `data/changes.json` + hash de páginas oficiales (`data/snapshots.json`).

## Actualizar
```bash
./run.sh                       # todo: tasas + páginas oficiales + noticias + build
# o por pasos:
python3 scripts/seed_providers.py          # tras revisar comisiones a mano
python3 scripts/refresh.py [--no-news] [--no-pages]
/workspace/cobraendolares-news/.venv/bin/python scripts/fetch_news.py
python3 scripts/build.py
```

## Publicar (sin Actions)
```bash
git add -A && git commit -m "refresh" && git push origin main
git push origin `git subtree split --prefix site main`:gh-pages --force
gh api -X POST repos/echacn-blip/cobraendolares/pages/builds
```

## Newsletter
Modo demo mientras `NEWSLETTER_USERNAME` en `config.json` esté vacío (Buttondown).

## Licencias
uPlot (MIT) y countUp.js (MIT) en `assets/vendor/`. Inter y JetBrains Mono (OFL). Información orientativa, no es asesoría financiera.
