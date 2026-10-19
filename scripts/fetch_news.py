#!/usr/bin/env python3
"""CobraEnDólares: genera data/news.json (solo titular + enlace + fuente, sin texto completo).
Uso: /workspace/cobraendolares-news/.venv/bin/python scripts/fetch_news.py (requiere feedparser y rapidfuzz)  (correr desde cron en el box, luego git commit/push del JSON)."""
import json, re, time, unicodedata, calendar
from datetime import datetime, timezone, timedelta
import pathlib
import feedparser
from rapidfuzz import fuzz

UA = "Mozilla/5.0 (X11; Linux x86_64) CobraEnDolaresBot/1.0 (+https://echacn-blip.github.io/)"
FEEDS = [  # (fuente, país, url) - todos verificados 2026-10-19
    ("Ámbito", "AR", "https://www.ambito.com/rss/pages/economia.xml"),
    ("Ámbito", "AR", "https://www.ambito.com/rss/pages/finanzas.xml"),
    ("Infobae", "AR", "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/"),
    ("iProfesional", "AR", "https://www.iprofesional.com/rss/finanzas"),
    ("El Cronista", "AR", "https://www.cronista.com/arc/outboundfeeds/rss/"),
    ("La Nación", "AR", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/"),
    ("El Economista", "MX", "https://www.eleconomista.com.mx/rss/ultimas-noticias"),
    ("El Financiero", "MX", "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/?outputType=xml"),
    ("Expansión", "MX", "https://expansion.mx/rss"),
    ("Portafolio", "CO", "https://www.portafolio.co/rss/economia.xml"),
    ("La República", "CO", "https://www.larepublica.co/rss/finanzas"),
    ("El Tiempo", "CO", "https://www.eltiempo.com/rss/economia.xml"),
    ("Gestión", "PE", "https://gestion.pe/arcio/rss/category/economia/"),
    ("El Comercio", "PE", "https://elcomercio.pe/arcio/rss/category/economia/"),
    ("La Tercera Pulso", "CL", "https://www.latercera.com/arc/outboundfeeds/rss/category/pulso/?outputType=xml"),
    ("Bloomberg Línea", "LatAm", "https://www.bloomberglinea.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("BBC Mundo", "LatAm", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ("Google News", "LatAm", "https://news.google.com/rss/search?q=remesas+d%C3%B3lar+when:7d&hl=es-419&gl=MX&ceid=MX:es-419"),
    ("Google News", "LatAm", "https://news.google.com/rss/search?q=Payoneer+OR+Wise+OR+DolarApp+OR+Global66+OR+Takenos+OR+Airtm+OR+Littio+when:30d&hl=es-419&gl=US&ceid=US:es-419"),
]
def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))
CATS = {  # palabras sin tildes; el orden define prioridad
    "fintech": r"payoneer|\bwise\b|dolarapp|global66|takenos|littio|\bdeel\b|airtm|fintech|billetera|stablecoin|usdt|usdc|cripto",
    "remesas": r"remesa|envio de dinero|transferencias? internacional|freelanc|trabajo remoto|teletrabaj",
    "impuestos": r"impuesto|\bsat\b|\bdian\b|\bsunat\b|\bsii\b|\barca\b|\bafip\b|ganancias|retencion|monotributo|tributari|\biva\b",
    "dólar": r"dolar|tipo de cambio|divisa|\bpeso\b|\btrm\b|\bmep\b|\bccl\b|cepo|banxico|\bbcra\b|banco central|\bfed\b",
}
CATS = {k: re.compile(v) for k, v in CATS.items()}
MAX_AGE = timedelta(days=7)

def item_date(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(t), timezone.utc) if t else None

def main():
    now, out, seen = datetime.now(timezone.utc), [], []
    for fuente, pais, url in FEEDS:
        d = feedparser.parse(url, agent=UA)
        if d.bozo and not d.entries:
            print(f"[warn] {fuente}: {d.get('bozo_exception')}"); continue
        for e in d.entries:
            title, link = (e.get("title") or "").strip(), e.get("link")
            dt = item_date(e)
            if not title or not link or not dt or now - dt > MAX_AGE: continue
            src = fuente
            if fuente == "Google News":  # titular "Título - Medio"
                src = (e.get("source") or {}).get("title") or title.rsplit(" - ", 1)[-1]
                title = title.rsplit(" - ", 1)[0]
            n = norm(title)
            cats = [k for k, rx in CATS.items() if rx.search(n)]
            if not cats: continue  # solo noticias relevantes para cobrar en USD
            if any(fuzz.token_set_ratio(n, s) >= 90 for s in seen): continue  # dedupe entre medios
            seen.append(n)
            out.append({"source": src, "country": pais, "title": title, "link": link,
                        "date": dt.isoformat(), "category": cats[0], "tags": cats})
        time.sleep(1)  # cortesía con los servidores
    out.sort(key=lambda x: x["date"], reverse=True)
    per, capped = {}, []
    for i in out:  # máx. 6 por medio para no saturar con un solo país
        per[i["source"]] = per.get(i["source"], 0) + 1
        if per[i["source"]] <= 6: capped.append(i)
    out = capped
    data = {"generated_at": now.isoformat(), "count": min(len(out), 60), "items": out[:60],
            "notice": "Titulares y enlaces a las fuentes originales; el contenido pertenece a cada medio."}
    out_path = pathlib.Path(__file__).resolve().parents[1] / "data" / "news.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} noticias relevantes -> data/news.json")
if __name__ == "__main__":
    main()
