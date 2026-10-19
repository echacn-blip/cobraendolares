#!/usr/bin/env python3
"""CobraEnDólares – descarga datos reales a data/. Solo librería estándar.
  rates.json    tipo de cambio medio USD→MXN/COP/PEN/CLP/ARS (currency-api de fawazahmed0; respaldo open.er-api.com)
                + DolarAPI: dólares de Argentina (oficial, blue, MEP, CCL, cripto, tarjeta) y de México, Chile y Colombia
  history.json  31 días: currency-api (5 monedas) + ArgentinaDatos (oficial, blue, MEP)
  wise.json     cotización oficial de Wise para US$1.000 y US$2.000 (API pública de comparaciones) → fijo + %
  news.json     titulares de los RSS de Economía de Ámbito, Infobae e iProfesional
  changes.json  historial: hashea cada página oficial de comisiones (data/snapshots.json) y registra cambios
Uso: python3 scripts/refresh.py [--no-news] [--no-pages]"""
import json, sys, pathlib, datetime, urllib.request, re, html, hashlib, email.utils, concurrent.futures as cf
import xml.etree.ElementTree as ET
ROOT = pathlib.Path(__file__).resolve().parents[1]; DATA = ROOT/"data"; DATA.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 CobraEnDolares-refresh"}
NOW = datetime.datetime.now(datetime.timezone.utc); TODAY = NOW.date()
CUR = ["MXN", "COP", "PEN", "CLP", "ARS"]
def get(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r: return r.read()
def getj(url): return json.loads(get(url))
def load(name, d=None):
    p = DATA/name; return json.loads(p.read_text()) if p.exists() else d
def save(name, obj): (DATA/name).write_text(json.dumps(obj, ensure_ascii=False, indent=1)); print(f"  ✓ data/{name}")

def fawaz(date="latest"):
    for u in (f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.min.json",
              f"https://{date}.currency-api.pages.dev/v1/currencies/usd.min.json"):
        try: d = getj(u); return d["date"], {c: d["usd"][c.lower()] for c in CUR}
        except Exception: continue
    return None, None

def rates():
    date, r = fawaz()
    if r: mid = {"source": "currency-api (fawazahmed0)", "source_url": "https://github.com/fawazahmed0/exchange-api", "date": date, "rates": r}
    else:
        d = getj("https://open.er-api.com/v6/latest/USD")
        mid = {"source": "ExchangeRate-API (open.er-api.com)", "source_url": "https://www.exchangerate-api.com/docs/free",
               "date": datetime.datetime.fromtimestamp(d["time_last_update_unix"], datetime.timezone.utc).date().isoformat(), "rates": {c: d["rates"][c] for c in CUR}}
    out = {"fetched_utc": NOW.isoformat(timespec="seconds"), "mid": mid, "ar": [], "local": {}}
    try:
        out["ar"] = [{"casa": x["casa"], "nombre": x["nombre"], "compra": x["compra"], "venta": x["venta"], "t": x["fechaActualizacion"]} for x in getj("https://dolarapi.com/v1/dolares")]
    except Exception as ex: print("  ! DolarAPI AR:", ex); out["ar"] = (load("rates.json", {}) or {}).get("ar", [])
    for cc in ("mx", "cl", "co"):
        try:
            x = next(i for i in getj(f"https://{cc}.dolarapi.com/v1/cotizaciones") if i["moneda"] == "USD")
            out["local"][cc] = {"compra": x.get("compra"), "venta": x.get("venta"), "t": x.get("fechaActualizacion")}
        except Exception as ex: print(f"  ! DolarAPI {cc}:", ex)
    return out

def history(days=31):
    end, _ = fawaz(); end = datetime.date.fromisoformat(end) if end else TODAY
    dates = [(end - datetime.timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]
    with cf.ThreadPoolExecutor(8) as ex: res = [x for x in ex.map(fawaz, dates) if x[1]]
    out = {"generated_utc": NOW.isoformat(timespec="seconds"),
           "mid": {"source": "currency-api (fawazahmed0)", "dates": [d for d, _ in res], "rates": {c: [r[c] for _, r in res] for c in CUR}}, "ar": {}}
    start = dates[0]
    for casa in ("oficial", "blue", "bolsa"):
        try:
            xs = [x for x in getj(f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}") if x["fecha"] >= start]
            out["ar"][casa] = {"dates": [x["fecha"] for x in xs], "venta": [x["venta"] for x in xs], "compra": [x["compra"] for x in xs]}
        except Exception as ex: print("  ! ArgentinaDatos", casa, ex)
    out["ar_source"] = "ArgentinaDatos (api.argentinadatos.com)"
    print(f"  historial: {len(res)} días · AR: {', '.join(f'{k} {len(v['dates'])}' for k, v in out['ar'].items())}")
    return out

def wise():
    out = {"fetched_utc": NOW.isoformat(timespec="seconds"), "source": "Wise – API pública de comparaciones (api.wise.com/v4/comparisons)", "cur": {}}
    for c in CUR:
        q = {}
        for amt in (1000, 2000):
            try:
                d = getj(f"https://api.wise.com/v4/comparisons/?sourceCurrency=USD&targetCurrency={c}&sendAmount={amt}")
                w = next(p for p in d["providers"] if p["alias"] == "wise")["quotes"][0]
                q[amt] = w
            except Exception as ex: print("  ! Wise", c, amt, ex)
        if len(q) == 2:
            f1, f2 = q[1000]["fee"], q[2000]["fee"]; pct = (f2 - f1) / 1000 * 100; fixed = f1 - pct * 10
            out["cur"][c] = {"fixed": round(fixed, 4), "pct": round(pct, 5), "rate": q[1000]["rate"], "markup": q[1000].get("markup"),
                             "fee1000": f1, "fee2000": f2, "received1000": q[1000]["receivedAmount"], "date": q[1000]["dateCollected"]}
    print(f"  Wise: {len(out['cur'])}/5 monedas")
    return out

FEEDS = [("Ámbito", "https://www.ambito.com/rss/pages/economia.xml"),
         ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/"),
         ("iProfesional", "https://www.iprofesional.com/rss/economia")]
KW = re.compile(r"d[oó]lar|peso|tipo de cambio|divisa|moneda|cotiza|brecha|mep|blue|cepo|freelanc|remesa|exporta|banco central|bcra|banxico|inflaci", re.I)
def news(total=24):
    def one(f):
        src, url = f
        try: root = ET.fromstring(get(url))
        except Exception as ex: print("  ! feed:", src, ex); return []
        items = []
        for it in root.iter("item"):
            title = html.unescape((it.findtext("title") or "").strip()); link = (it.findtext("link") or "").strip()
            try: dt = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(datetime.timezone.utc)
            except Exception: continue
            if title and link and (NOW - dt).days <= 7 and KW.search(title):
                items.append({"title": title, "source": src, "date": dt.isoformat(timespec="seconds"), "link": link})
        return items[:10]
    with cf.ThreadPoolExecutor(3) as ex: items = sorted([x for r in ex.map(one, FEEDS) for x in r], key=lambda x: x["date"], reverse=True)
    seen, out = set(), []
    for x in items:
        k = re.sub(r"\W+", "", x["title"].lower())[:60]
        if k not in seen: seen.add(k); out.append(x)
    print(f"  noticias: {len(out[:total])}")
    return {"generated_utc": NOW.isoformat(timespec="seconds"), "sources": [f[0] + " (RSS Economía)" for f in FEEDS], "items": out[:total]}

def page_text(raw):
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", t); t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t); t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\b\d{1,2}:\d{2}\b|\b20\d\d-\d\d-\d\dT[\d:.]+Z?\b", "", t)  # quita horas/marcas de tiempo volátiles
    return t.strip()
def pages():
    prov = load("providers.json"); snaps = load("snapshots.json", {}); changes = load("changes.json", [])
    used = {}
    for p in prov["providers"]:
        for cc, v in p["countries"].items():
            for key in [v.get("src")] + [v[k]["src"] for k in ("rx", "fx", "wd") if k in v]:
                if key and "api.wise.com" not in prov["sources"][key]: used.setdefault(key, set()).add(p["name"])
    if not changes:
        changes = [{"date": prov["checked"], "type": "base", "provider": p["name"], "title": f"Registro inicial de comisiones de {p['name']}",
                    "detail": "Datos verificados a mano en las páginas oficiales citadas en cada campo.", "reviewed": True} for p in prov["providers"]]
    def chk(key):
        url = prov["sources"][key]
        try:
            raw = get(url); txt = page_text(raw) if not url.endswith(".pdf") else raw
            return key, hashlib.sha256(txt.encode() if isinstance(txt, str) else txt).hexdigest()
        except Exception as ex: return key, None
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(chk, used))
    ok = 0
    for key, h in res:
        if not h: continue
        ok += 1; old = snaps.get(key, {}).get("hash")
        if old and old != h:
            changes.append({"date": TODAY.isoformat(), "type": "detectado", "provider": ", ".join(sorted(used[key])), "url": prov["sources"][key],
                            "title": f"Cambió una página oficial de {', '.join(sorted(used[key]))}", "detail": "El robot detectó un cambio en el texto. Pendiente de revisión humana antes de tocar los datos.", "reviewed": False})
        snaps[key] = {"hash": h, "checked": NOW.isoformat(timespec="seconds"), "url": prov["sources"][key]}
    print(f"  páginas oficiales: {ok}/{len(used)} revisadas")
    save("snapshots.json", snaps); save("changes.json", changes)

if __name__ == "__main__":
    print("Refrescando datos…")
    save("rates.json", rates()); save("history.json", history())
    w = wise()
    if w["cur"]: save("wise.json", w)
    if "--no-news" not in sys.argv:
        n = news()
        if n["items"]: save("news.json", n)
    if "--no-pages" not in sys.argv: pages()
