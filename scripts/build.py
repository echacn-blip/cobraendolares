#!/usr/bin/env python3
"""CobraEnDólares – genera site/ desde data/*.json + config.json (solo librería estándar).
Config (config.json o variables de entorno): SITE_URL, BASE_PATH (/cobraendolares/), NEWSLETTER_USERNAME (vacío = modo demo)."""
import json, os, shutil, html, pathlib, datetime, re, math, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT, ASSETS = ROOT/"data", ROOT/"site", ROOT/"assets"
sys.path.insert(0, str(ROOT/"scripts"))
CFG = json.loads((ROOT/"config.json").read_text()) if (ROOT/"config.json").exists() else {}
def cfg(k, d=""): return os.environ.get(k, CFG.get(k, d))
SITE_URL = cfg("SITE_URL", "https://USUARIO.github.io/cobraendolares").rstrip("/")
BASE_PATH = "/" + cfg("BASE_PATH", "/").strip("/") + "/" if cfg("BASE_PATH", "/").strip("/") else "/"
NL_USER = cfg("NEWSLETTER_USERNAME", "").strip()
NAME = "CobraEnDólares"
J = lambda n, d=None: json.loads((DATA/n).read_text()) if (DATA/n).exists() else d
PROV, RATES, HIST, WISE = J("providers.json"), J("rates.json"), J("history.json"), J("wise.json", {"cur": {}})
NEWS, CHANGES = J("news.json", {"items": []}), sorted(J("changes.json", []), key=lambda c: c["date"], reverse=True)
SRC = PROV["sources"]; COUNTRIES = PROV["countries"]
SLUG = {"mx": "mexico", "co": "colombia", "pe": "peru", "cl": "chile", "ar": "argentina"}
FLAG = {"mx": "MX", "co": "CO", "pe": "PE", "cl": "CL", "ar": "AR"}
MID = RATES["mid"]["rates"]
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)
MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
def fecha(iso): y,m,d = iso[:10].split("-"); return f"{int(d)} {MESES[int(m)-1]} {y}"
def fmt(v, dec=2): return f"{v:,.{dec}f}"
def money(v, cur):
    dec = 0 if cur in ("COP", "CLP", "ARS") else 2
    return f"{cur} {fmt(v, dec)}"
def usd(v): return f"US${fmt(v)}"
CHECKED = fecha(PROV["checked"])
AR = {x["casa"]: x for x in RATES.get("ar", [])}
pages = []

# ---------- motor de cálculo (misma lógica que assets/app.js) ----------
def fee(c, A):
    k = c["k"]
    if k == "fixed": return (c["fixed"], c["fixed"], True)
    if k == "pct":
        v = A * c["pct"] / 100; v = max(v, c.get("min", 0)); v = min(v, c["max"]) if c.get("max") else v; return (v, v, True)
    if k == "fixed_pct":
        v = c["fixed"] + A * c["pct"] / 100; v = min(v, c["max"]) if c.get("max") else v; return (v, v, True)
    if k == "range_pct": return (A * c["lo"] / 100, A * c["hi"] / 100, True)
    if k == "tiered":
        for t in c["tiers"]:
            if "upto" not in t or A < t["upto"]:
                v = t.get("fixed", A * t.get("pct", 0) / 100); return (v, v, True)
    if k == "included": return (0, 0, True)
    return (0, 0, False)
def calc(p, cc, A):
    v = p["countries"].get(cc); cur = COUNTRIES[cc]["cur"]; mid = MID[cur]
    if not v or not v["ok"]: return {"st": "na", "why": v["why"] if v else "", "p": p}
    r = {"p": p, "v": v, "st": "ok", "flags": []}
    if v.get("min") and A < v["min"]: r["st"] = "min"; return r
    if v.get("max") and A > v["max"]: r["flags"].append("max")
    rx = fee(v["rx"], A); A1 = A - rx[0]; A1h = A - rx[1]
    rate = mid
    if v["fx"]["k"] == "wise":
        w = WISE["cur"].get(cur)
        if not w: fx = (0, 0, False)
        else: f = w["fixed"] + w["pct"] * A1 / 100; fx = (f, f, True); rate = w["rate"]
    else: fx = fee(v["fx"], A1)
    A2lo, A2hi = A1h - fx[1], A1 - fx[0]
    wd = fee(v["wd"], A2hi)
    A3lo, A3hi = A2lo - wd[1], A2hi - wd[0]
    r.update(rx=rx, fx=fx, wd=wd, rate=rate, mid=mid, cur=cur, netlo=A3lo * rate, nethi=A3hi * rate,
             complete=rx[2] and fx[2] and wd[2], range=rx[0] != rx[1] or fx[0] != fx[1] or wd[0] != wd[1])
    r["costlo"] = A - r["nethi"] / mid; r["costhi"] = A - r["netlo"] / mid
    if A3lo <= 0: r["st"] = "min"
    return r
def ranking(cc, A):
    rs = [calc(p, cc, A) for p in PROV["providers"]]
    comp = sorted([r for r in rs if r["st"] == "ok" and r["complete"]], key=lambda r: -(r["netlo"] + r["nethi"]) / 2)
    inc = sorted([r for r in rs if r["st"] == "ok" and not r["complete"]], key=lambda r: -r["nethi"])
    return comp, inc, [r for r in rs if r["st"] == "min"], [r for r in rs if r["st"] == "na"]

def comp_html(c, A, cur, r):
    k = c["k"]
    if k in ("unpublished",): return '<span class="f unk">Margen no publicado</span>'
    if k == "unknown": return '<span class="f unk">Sin verificar</span>'
    if k == "wise": return f'US${fmt(r["fx"][0])}<small>Comisión Wise · tipo {fmt(r["rate"],4)}</small>'
    if k == "range_pct": return f'{c["lo"]:g}%–{c["hi"]:g}%<small>Rango publicado</small>'
    if k == "included": return 'Incluido'
    lo = fee(c, A)[0]
    return "US$0" if lo == 0 else f"US${fmt(lo)}"

# ---------- piezas ----------
def nl_form(r, variant="hero", tag="web"):
    if NL_USER:
        attrs = f'action="https://buttondown.com/api/emails/embed-subscribe/{e(NL_USER)}" method="post"'
        hidden = f'<input type="hidden" name="embed" value="1"><input type="hidden" name="tag" value="{e(tag)}">'; demo = ""
    else:
        attrs = f'action="#" method="post" data-placeholder data-thanks="{r}gracias/index.html"'; hidden = ""
        demo = '<div class="demo-note">Modo demo: el formulario aún no está conectado (falta NEWSLETTER_USERNAME). No se guarda ningún correo.</div>'
    uid = f"em-{variant}"
    return (f'<form class="nl-form" {attrs}>{hidden}<label class="sr" for="{uid}">Tu correo</label>'
            f'<div class="capture"><input id="{uid}" type="email" name="email" required placeholder="tu@correo.com" autocomplete="email">'
            f'<button class="btn pri" type="submit">Únete gratis →</button></div>'
            f'<div class="capture-note"><span>1 correo por semana</span><span>Sin spam</span><span>Te das de baja con un clic</span></div>{demo}</form>')
DISC = ("Información, no asesoría financiera. Comparamos las comisiones que cada proveedor publica en sus páginas oficiales (con fuente y fecha en cada dato) "
        "y un tipo de cambio medio de referencia. Los montos son estimaciones: confirma siempre el costo final en la app del proveedor antes de operar. "
        "No decimos cuál es “el mejor”: el orden depende del monto, tu país y los datos disponibles.")
def disc(r): return f'<p class="disc"><span>{DISC} <a href="{r}metodologia/index.html">Metodología</a>.</span></p>'
def badge(p, size=""): return f'<span class="mono-badge" data-b="{p["slug"]}"{size}>{e(p["mono"])}</span>'
FLAGS = {
 "mx": '<rect width="6" height="12" fill="#006847"/><rect x="6" width="6" height="12" fill="#fff"/><rect x="12" width="6" height="12" fill="#ce1126"/><circle cx="9" cy="6" r="1.6" fill="#8c5a2b"/>',
 "co": '<rect width="18" height="6" fill="#fcd116"/><rect y="6" width="18" height="3" fill="#003893"/><rect y="9" width="18" height="3" fill="#ce1126"/>',
 "pe": '<rect width="6" height="12" fill="#d91023"/><rect x="6" width="6" height="12" fill="#fff"/><rect x="12" width="6" height="12" fill="#d91023"/>',
 "cl": '<rect width="18" height="6" fill="#fff"/><rect y="6" width="18" height="6" fill="#d52b1e"/><rect width="6" height="6" fill="#0039a6"/><circle cx="3" cy="3" r="1.2" fill="#fff"/>',
 "ar": '<rect width="18" height="4" fill="#74acdf"/><rect y="4" width="18" height="4" fill="#fff"/><rect y="8" width="18" height="4" fill="#74acdf"/><circle cx="9" cy="6" r="1.3" fill="#f6b40e"/>'}
def flag(cc): return f'<svg class="flag" viewBox="0 0 18 12" aria-hidden="true">{FLAGS[cc]}</svg>'
def flag_seg(cc):
    return '<span class="seg flags" role="group" aria-label="País">' + "".join(f'<button type="button" data-c="{k}" aria-pressed="{"true" if k==cc else "false"}">{flag(k)}<span>{e(v["name"])}</span></button>' for k, v in COUNTRIES.items()) + '</span>'
def cost_bar(r, scale):
    v = r["v"]; segs = []; known = 0
    for key, cls, lab in (("rx","rx","Recepción"),("fx","fx","Cambio"),("wd","wd","Retiro")):
        k = v[key]["k"]; lo, hi = r[key][0], r[key][1]
        if k in ("unpublished","unknown"): segs.append(f'<span class="s unk" title="{lab}: {"margen no publicado" if k=="unpublished" else "sin verificar"}">?</span>'); continue
        known += hi
        if lo > 0: segs.append(f'<span class="s {cls}" style="width:{lo/scale*100:.2f}%" title="{lab}: US${fmt(lo)}"></span>')
        if hi > lo: segs.append(f'<span class="s {cls} rg" style="width:{(hi-lo)/scale*100:.2f}%" title="{lab}: hasta US${fmt(hi)}"></span>')
    lab = ("≥ " if not r["complete"] else "") + (f'US${fmt(r["rx"][0]+r["fx"][0]+r["wd"][0])}' + (f'–{fmt(known)}' if known > r["rx"][0]+r["fx"][0]+r["wd"][0] + 0.005 else ""))
    return f'<div class="cbarw"><div class="cbar" role="img" aria-label="Costos publicados {lab}">{"".join(segs)}</div><span class="cbar-l">{lab} en comisiones publicadas</span></div>'
def src_link(key, label=None):
    u = SRC[key]; host = re.sub(r"^https?://(www\.)?", "", u).split("/")[0]
    return f'<a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(label or host)} ↗</a>'

def row_html(r, i, A, rr, scale=1):
    p, v, cur = r["p"], r["v"], r["cur"]
    top = " top" if i == 0 and r["complete"] else ""
    if r["complete"]: st = '<span class="badge acc">Costo verificado</span>' if not r["range"] else '<span class="badge">Rango publicado</span>'
    else: st = '<span class="badge warn">Datos incompletos</span>'
    if i == 0 and r["complete"]: st = '<span class="badge win">★ Más te llega</span>' + st
    if "max" in r["flags"]: st += f'<span class="badge dn">{e(v.get("max_txt",""))}</span>'
    net = (f'<b>{money((r["netlo"]+r["nethi"])/2, cur)}</b><small>{money(r["netlo"],cur)} – {money(r["nethi"],cur)}</small>' if r["range"]
           else f'<b>{"≤ " if not r["complete"] else ""}{money(r["nethi"], cur)}</b>')
    net += f'<small>≈ {usd(r["nethi"]/r["mid"])} · costo {"≥ " if not r["complete"] else ""}{usd(max(0,r["costlo"]))}</small>'
    srcs = "".join(f'<li><b>{lab}:</b> {e(v[k]["txt"])} — {src_link(v[k]["src"])} <span class="dim">({fecha(v[k]["date"])})</span></li>' for k, lab in (("rx","Recepción"),("fx","Cambio"),("wd","Retiro")))
    notes = "".join(f"<li>{e(n)}</li>" for n in v.get("notes", []))
    return (f'<div class="rrow{top}" data-p="{p["slug"]}"><span class="rk">{i+1 if r["complete"] else "–"}</span>'
            f'<div class="pv">{badge(p)}<div><a href="{rr}proveedores/{p["slug"]}/index.html">{e(p["name"])}</a><span class="route">{e(v["route"])}</span><div>{st}</div></div></div>'
            f'<span class="f" data-l="Recepción">{comp_html(v["rx"], A, cur, r)}</span><span class="f" data-l="Cambio">{comp_html(v["fx"], A, cur, r)}</span>'
            f'<span class="f" data-l="Retiro">{comp_html(v["wd"], A, cur, r)}</span><div class="net">{net}</div>{cost_bar(r, scale)}'
            f'<details><summary>Fuentes y notas</summary><ul>{srcs}{notes}</ul></details></div>')

def results_static(cc, A, rr):
    comp, inc, mins, na = ranking(cc, A); cname = COUNTRIES[cc]["name"]
    scale = max([1] + [x["rx"][1] + x["fx"][1] + x["wd"][1] for x in comp + inc]) * 1.12
    h = '<div class="cleg"><span><i class="rx"></i>Recepción</span><span><i class="fx"></i>Cambio / margen</span><span><i class="wd"></i>Retiro</span><span><i class="rg"></i>Rango publicado</span><span><i class="unk"></i>No publicado</span></div><div class="rhead"><span>#</span><span>Proveedor</span><span>Recepción</span><span>Cambio</span><span>Retiro</span><span>Te llega</span></div>'
    h += f'<div class="grp">Costo total publicado · ordenado por lo que te llega</div>' + "".join(row_html(r, i, A, rr, scale) for i, r in enumerate(comp))
    if inc: h += '<div class="grp">Datos incompletos · neto antes del margen o comisión que no publican</div>' + "".join(row_html(r, -1, A, rr, scale) for r in inc)
    if mins: h += '<div class="grp">Monto mínimo no alcanzado</div>' + "".join(f'<div class="rrow na"><span class="rk">–</span><div class="pv">{badge(r["p"])}<div><b>{e(r["p"]["name"])}</b><span class="route">{e(r["v"].get("min_txt","Monto mínimo no alcanzado"))}</span></div></div></div>' for r in mins)
    if na: h += f'<div class="grp">No disponible en {e(cname)}</div>' + "".join(f'<div class="rrow na"><span class="rk">–</span><div class="pv">{badge(r["p"])}<div><b>{e(r["p"]["name"])}</b><span class="route">{e(r["why"])}</span></div></div></div>' for r in na)
    return h

def comparator(rr, cc="mx", A=1000):
    return f"""<section id="comparador" class="reveal" style="--d:3" aria-labelledby="h-comp" data-comp data-country="{cc}">
<div class="sh"><div><span class="kicker">Comparador</span><h2 id="h-comp">Cuánto te llega en <span data-cname>{e(COUNTRIES[cc]["name"])}</span></h2><p>Escribe cualquier monto: recalculamos al instante para los 8 proveedores. Comisiones revisadas el {CHECKED}; tipo de cambio de referencia del {fecha(RATES["mid"]["date"])}.</p></div>
<span class="status snap" data-status><i></i><span data-status-txt>Datos guardados · {fecha(RATES["mid"]["date"])}</span></span></div>
<div class="ctl-row">{flag_seg(cc)}</div>
<div class="res" data-results aria-live="polite">{results_static(cc, A, rr)}</div>
<p class="fine">“Te llega” = monto en moneda local después de las comisiones publicadas. Para proveedores que no publican su margen cambiario usamos el tipo medio de referencia, así que el neto real será menor (por eso “≤”). Wise: cotización oficial en vivo de su API pública. Payoneer publica un rango (1,2%–4%), por eso mostramos mínimo y máximo.</p>
{disc(rr)}</section>"""

def amount_box(rr, A=1000):
    return f"""<div class="reveal" style="--d:2"><label class="sr" for="amt">Monto que te pagan en dólares</label>
<div class="amount-box"><span class="cur">US$</span><input id="amt" type="text" inputmode="decimal" autocomplete="off" value="{fmt(A,0).replace(",","")}" data-amount aria-describedby="amt-err"><span class="dim xs mono">USD</span></div>
<div class="chips"><button type="button" class="chipbtn" data-quick="1000" aria-pressed="{"true" if A==1000 else "false"}">US$1.000</button><button type="button" class="chipbtn" data-quick="2000" aria-pressed="{"true" if A==2000 else "false"}">US$2.000</button><button type="button" class="chipbtn" data-quick="500" aria-pressed="false">US$500</button><button type="button" class="chipbtn" data-quick="375.20" aria-pressed="false">US$375,20</button></div>
<div class="err" id="amt-err" data-err></div></div>"""

def spark(vals, w=64, h=20, col=None):
    if len(vals) < 2: return ""
    lo, hi = min(vals), max(vals); rg = (hi - lo) or 1
    pts = " ".join(f"{i*(w/(len(vals)-1)):.1f},{h-2-(v-lo)/rg*(h-4):.1f}" for i, v in enumerate(vals))
    up = vals[-1] >= vals[0]; col = col or ("var(--up)" if up else "var(--dn)")
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><polygon fill="url(#sg-{"up" if up else "dn"})" points="0,{h} {pts} {w},{h}"/>'
            f'<polyline fill="none" stroke="{col}" stroke-width="1.6" vector-effect="non-scaling-stroke" points="{pts}"/></svg>')
def chg(p):
    cls = "flat" if abs(p) < 0.005 else ("up" if p > 0 else "dn"); ar = "→" if cls == "flat" else ("▲" if p > 0 else "▼")
    return f'<span class="chg {cls}">{ar} {abs(p):.2f}%</span>'
def market_data():
    m = HIST["mid"]; rows = []
    for c in ("MXN", "COP", "PEN", "CLP", "ARS"):
        s = m["rates"][c]; ch = (s[-1] / s[-2] - 1) * 100
        lab = "oficial · ref." if c == "ARS" else "medio · ref."
        rows.append((f"USD/{c}", lab, MID[c], ch, s, f"mid-{c}"))
    for casa, lab in (("blue", "blue · venta"), ("bolsa", "MEP · venta")):
        h = HIST["ar"].get(casa)
        if h and AR.get(casa): rows.append((f"USD/ARS", lab, AR[casa]["venta"], (h["venta"][-1] / h["venta"][-2] - 1) * 100, h["venta"], f"ar-{casa}"))
    return rows
def market_rows():
    return "".join(f'<tr data-mk="{k}"><td class="p">{p}<span class="lab">{l}</span></td><td class="v" data-v>{fmt(v, 2)}</td><td class="c" data-c>{chg(c)}</td><td class="rg30">{fmt(min(s), 2)}<span>–</span>{fmt(max(s), 2)}</td><td class="s">{spark(s, 150, 36)}</td></tr>' for p, l, v, c, s, k in market_data())
def ticker():
    one = "".join(f'<span class="tk" data-tk="{k}"><b>{p}</b> <em>{l.split(" · ")[0]}</em> <span data-v>{fmt(v, 2)}</span> <span data-c>{chg(c)}</span></span>' for p, l, v, c, s, k in market_data())
    return f'<div class="ticker" aria-hidden="true"><div class="tk-track">{one}{one}</div></div>'
def market_block():
    return f"""<section id="mercado" class="reveal" aria-labelledby="h-mk"><div class="sh"><div><span class="kicker">Mercado</span><h2 id="h-mk">El dólar ahora mismo</h2><p>Tipo medio de referencia y dólares de Argentina, con su cambio diario y los últimos 30 días.</p></div></div>
{ticker()}{terminal()}</section>"""
def terminal():
    return f"""<div class="term glass" data-market aria-label="Panel de mercado"><div class="term-bar"><i></i><i></i><i></i><span>cobraendolares ~ mercado --usd</span><span class="live-tag"><b class="live-dot"></b>EN VIVO</span></div>
<div class="term-body"><table class="mk"><thead><tr><th>Par</th><th class="v">Último</th><th class="c">Día</th><th class="rg30">Rango 30 d</th><th class="s">30 días</th></tr></thead><tbody>{market_rows()}</tbody></table></div>
<div class="term-foot"><span data-mk-time>Actualizado {fecha(RATES["mid"]["date"])} · DolarAPI {e(AR.get("blue",{}).get("t","")[:16].replace("T"," "))} UTC</span><span>currency-api · DolarAPI<span class="cursor" aria-hidden="true"></span></span></div></div>"""

def hero_card(cc, A=1000):
    comp, inc, mins, na = ranking(cc, A); cur = COUNTRIES[cc]["cur"]
    b = comp[0] if comp else None
    netv = ((b["netlo"] + b["nethi"]) / 2) if b else 0
    who = f'{badge(b["p"])}<span><b data-hc-name>{e(b["p"]["name"])}</b><small data-hc-usd>≈ {usd(b["nethi"]/b["mid"])} · costo {usd(max(0,b["costlo"]))}</small></span>' if b else ""
    return f"""<aside class="hcard2 glass reveal" style="--d:3" data-hero-card aria-label="Resumen del comparador">
<div class="hc-top"><span class="kicker">Te llega en <span data-cname>{e(COUNTRIES[cc]["name"])}</span></span><span class="status snap" data-status><i></i><span data-status-txt>Datos guardados · {fecha(RATES["mid"]["date"])}</span></span></div>
<p class="hc-lbl">Lo que más te llega con <span data-hc-amt>US$1.000</span>, entre opciones con costo publicado</p>
<div class="hc-net"><span class="hc-cur" data-hc-cur>{cur}</span><b data-hc-net>{fmt(netv, 0 if cur in ("COP","CLP","ARS") else 2)}</b></div>
<div class="hc-who" data-hc-who>{who}</div>
<div class="hc-plot" data-hc-plot></div>
<div class="hc-foot"><span>Comisiones {CHECKED} · tipo medio {fecha(RATES["mid"]["date"])}</span><a href="#comparador">Ver detalle ↓</a></div></aside>"""

def ahorrometro(cc="mx"):
    return f"""<section id="ahorrometro" class="ahorro glass reveal" aria-labelledby="h-ah" data-ahorro>
<div><span class="eyebrow"><i></i>Ahorrómetro</span><h2 id="h-ah">Lo que se queda en el camino en un año</h2>
<p class="ah-lead">Diferencia al año entre la opción más cara y la más barata con costo publicado</p><div class="big" data-ah-big>US$0</div><div class="sub" data-ah-sub>…</div>
<div class="ctl-row"><label class="l" for="ppy">Pagos al año</label><select id="ppy" data-ppy><option value="52">52 (semanal)</option><option value="26">26 (quincenal)</option><option value="12" selected>12 (mensual)</option><option value="4">4 (trimestral)</option><option value="1">1</option></select>
<button class="btn sec sm" type="button" data-share>Compartir resultado</button><span class="xs dim" data-share-msg></span></div></div>
<div class="ah-side"><div class="ah-gauge" data-ah-gauge aria-hidden="true"></div><div class="vs" data-ah-vs><p class="dim small">Calculando con los proveedores que publican su costo completo…</p></div></div>
<p class="xs dim" style="grid-column:1/-1;margin:0">Solo usamos proveedores con costo total publicado (incluido el rango de Payoneer: tomamos el extremo que <b>reduce</b> la diferencia, para no exagerar). Los que no publican su margen no entran en el cálculo.</p></section>"""

def thermo_block(rr, only=None):
    return f"""<section id="termometro" class="reveal" aria-labelledby="h-th"><div class="sh"><div><span class="kicker">Termómetro</span><h2 id="h-th">Termómetro del dólar</h2><p>Cómo está hoy el dólar frente a su promedio de los últimos 30 días, con datos reales.</p></div></div>
<div class="thermo" data-thermo{f' data-only="{only}"' if only else ""}></div>
<p class="fine">Es un dato, no una recomendación: el tipo de cambio de los últimos 30 días no predice el de mañana. Fuentes: currency-api (tipo medio diario) y ArgentinaDatos (oficial, blue y MEP, venta).</p></section>"""

def chart_block(cc=None):
    tabs = [("MXN","USD/MXN"),("COP","USD/COP"),("PEN","USD/PEN"),("CLP","USD/CLP"),("ARS","USD/ARS · oficial, blue, MEP")]
    sel = COUNTRIES[cc]["cur"] if cc else "MXN"
    t = "".join(f'<button class="tab" type="button" role="tab" data-cur="{c}" aria-selected="{"true" if c==sel else "false"}">{l}</button>' for c, l in tabs)
    return f"""<section id="grafico" class="reveal" aria-labelledby="h-ch"><div class="sh"><div><span class="kicker">Gráfico</span><h2 id="h-ch">El dólar en 30 días</h2><p>Valores diarios reales. Pasa el cursor para ver cada día.</p></div></div>
<div class="chart-card glass"><div class="tabs" role="tablist" data-ch-tabs data-sel="{sel}">{t}</div><div id="chart" style="margin-top:14px" data-chart></div>
<noscript><p class="dim">Activa JavaScript para ver el gráfico. Los datos están en <a href="data/history.json">history.json</a>.</p></noscript>
<p class="fine">Fuentes: <a href="https://github.com/fawazahmed0/exchange-api" rel="nofollow noopener" target="_blank">currency-api</a> (tipo medio) y <a href="https://argentinadatos.com" rel="nofollow noopener" target="_blank">ArgentinaDatos</a> (dólar oficial, blue y MEP en Argentina). Gráfico: uPlot (MIT).</p></div></section>"""

def ar_block():
    if not AR: return ""
    names = {"oficial":"Oficial","blue":"Blue","bolsa":"MEP (bolsa)","contadoconliqui":"CCL","mayorista":"Mayorista","cripto":"Cripto","tarjeta":"Tarjeta"}
    cards = "".join(f'<div class="pcard" data-ar="{k}"><span class="pp"><span>Dólar {names.get(k,k)}</span></span><span class="rate" data-ar-v>{fmt(x["venta"])}</span><span class="nm">Venta · compra <span data-ar-c>{fmt(x["compra"])}</span> ARS</span></div>' for k, x in AR.items())
    gap = (AR["blue"]["venta"] / AR["oficial"]["venta"] - 1) * 100 if "blue" in AR and "oficial" in AR else None
    return f"""<section id="dolares-ar" class="reveal" aria-labelledby="h-ar"><div class="sh"><div><h2 id="h-ar">Argentina: ¿a qué dólar te pagan?</h2><p>Si cobras en pesos, la plataforma convierte a un tipo cercano al oficial; si mantienes dólares, puedes compararlos con el MEP o el blue.{f" Brecha blue/oficial hoy: <b data-ar-gap>{gap:.1f}%</b>." if gap is not None else ""}</p></div></div>
<div class="pcards" data-ar-block>{cards}</div><p class="fine">Fuente: <a href="https://dolarapi.com" rel="nofollow noopener" target="_blank">DolarAPI</a>, en vivo desde tu navegador. Informativo.</p></section>"""

def coverage(rr):
    head = "".join(f'<th>{e(v["name"])}</th>' for v in COUNTRIES.values())
    rows = ""
    for p in PROV["providers"]:
        tds = ""
        for cc in COUNTRIES:
            v = p["countries"].get(cc)
            if not v or not v["ok"]: tds += '<td><span class="dot na"></span><span class="dim">No disp.</span></td>'; continue
            ks = [v[k]["k"] for k in ("rx","fx","wd")]
            if any(k in ("unpublished","unknown") for k in ks): tds += '<td><span class="dot pa"></span>Parcial</td>'
            elif "range_pct" in ks: tds += '<td><span class="dot rg"></span>Rango</td>'
            else: tds += '<td><span class="dot ok"></span>Completo</td>'
        rows += f'<tr><td><a href="{rr}proveedores/{p["slug"]}/index.html">{e(p["name"])}</a></td>{tds}</tr>'
    return f"""<section class="reveal" aria-labelledby="h-cov"><div class="sh"><div><h2 id="h-cov">Qué tan completos son los datos</h2><p><span class="dot ok"></span>costo completo publicado · <span class="dot rg"></span>publican un rango · <span class="dot pa"></span>falta el margen o una comisión · <span class="dot na"></span>no disponible</p></div></div>
<div class="tablewrap" style="max-height:none"><table class="cov"><thead><tr><th>Proveedor</th>{head}</tr></thead><tbody>{rows}</tbody></table></div></section>"""

CATN = {"dólar": "Dólar", "remesas": "Remesas", "fintech": "Fintech", "impuestos": "Impuestos"}
CTRN = {"AR": "Argentina", "MX": "México", "CO": "Colombia", "PE": "Perú", "CL": "Chile", "LatAm": "Región"}
def news_list(items, n, filters=False):
    li = "".join(f'<li data-cat="{e(x.get("category",""))}" data-country="{e(x.get("country",""))}"><a href="{e(x["link"])}" rel="nofollow noopener" target="_blank">{e(x["title"])}</a>'
                 f'<div class="meta"><b>{e(x["source"])}</b><span>{e(CTRN.get(x.get("country",""), x.get("country","")))}</span><span class="badge">{e(CATN.get(x.get("category",""), x.get("category","")))}</span><time datetime="{e(x["date"])}">{fecha(x["date"])}</time></div></li>' for x in items[:n])
    if not li: return '<p class="dim">No hay titulares recientes.</p>'
    flt = ""
    if filters:
        cats = [c for c in CATN if any(x.get("category") == c for x in items[:n])]
        ctrs = [c for c in CTRN if any(x.get("country") == c for x in items[:n])]
        flt = ('<div class="ctl-row" data-news-filter style="margin:0 0 14px"><span class="chips" style="margin:0" data-f="cat"><button type="button" class="chipbtn" data-v="" aria-pressed="true">Todas</button>'
               + "".join(f'<button type="button" class="chipbtn" data-v="{c}" aria-pressed="false">{CATN[c]}</button>' for c in cats)
               + '</span><span class="chips" style="margin:0" data-f="country"><button type="button" class="chipbtn" data-v="" aria-pressed="true">Todos los países</button>'
               + "".join(f'<button type="button" class="chipbtn" data-v="{c}" aria-pressed="false">{CTRN[c]}</button>' for c in ctrs) + '</span></div>')
    return f'{flt}<ul class="news" data-news>{li}</ul>'

# ---------- datos para app.js ----------
TC = {"prov": PROV, "wise": WISE, "rates": RATES, "hist": HIST, "slug": SLUG}

def layout(path, title, desc, body, kw="", active="", sticky=True, extra_head=""):
    depth = path.count("/"); r = "../"*depth
    canon = re.sub(r"index\.html$", "", f"{SITE_URL}/{path}")
    nav = [("index.html#comparador","Comparador"),("proveedores/index.html","Proveedores"),("guia/index.html","Guía"),("blog/index.html","Blog"),("noticias/index.html","Noticias")]
    navh = "".join(f'<a href="{r}{h}"{" class=on aria-current=page" if h==active else ""}>{t}</a>' for h,t in nav)
    sticky_html = (f'<div class="sticky-cta" role="complementary" aria-label="Suscripción"><span class="txt">📬 <b>Cambios de comisiones y del dólar, cada semana.</b> <span class="dim">Gratis.</span></span>'
                   f'<a class="btn pri sm" href="{r}suscribete/index.html">Únete</a><button class="x" type="button" aria-label="Cerrar">×</button></div>') if sticky else ""
    keywords = kw or "cobrar en dólares, recibir pagos del exterior, freelancer, Payoneer, Wise, DolarApp, Global66, Takenos, Littio, Deel, Airtm, comisiones, tipo de cambio"
    clinks = "".join(f'<li><a href="{r}{SLUG[k]}/index.html">Cobrar en dólares en {e(v["name"])}</a></li>' for k, v in COUNTRIES.items())
    doc = f"""<!doctype html><html lang="es-419"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="keywords" content="{e(keywords)}">
<link rel="canonical" href="{e(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{NAME}"><meta property="og:locale" content="es_419">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canon)}"><meta property="og:image" content="{SITE_URL}/assets/og.png">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#08090b"><meta name="color-scheme" content="dark">
<link rel="preload" href="{r}assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="{r}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{r}assets/style.css">{extra_head.replace("{r}", r)}
</head><body>
<div class="bgfx" aria-hidden="true"><i></i><i></i><i></i></div>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
<linearGradient id="sg-up" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#34e0a1" stop-opacity=".35"/><stop offset="1" stop-color="#34e0a1" stop-opacity="0"/></linearGradient>
<linearGradient id="sg-dn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff6b81" stop-opacity=".32"/><stop offset="1" stop-color="#ff6b81" stop-opacity="0"/></linearGradient>
<linearGradient id="sg-acc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#34e0a1" stop-opacity=".3"/><stop offset="1" stop-color="#34e0a1" stop-opacity="0"/></linearGradient>
</defs></svg>
<a class="skip" href="#main">Saltar al contenido</a>
<header class="top"><div class="wrap">
<a class="logo" href="{r}index.html" aria-label="{NAME}, inicio"><span class="mark">$↓</span><span>CobraEn<b>Dólares</b></span></a>
<nav class="main" aria-label="Principal">{navh}</nav>
<button class="btn sec sm menu-btn" type="button" aria-expanded="false" aria-label="Menú">☰</button>
<a class="btn pri sm" href="{r}suscribete/index.html">Únete a la lista</a>
</div></header>
<main id="main" class="wrap">{body}</main>
<footer><div class="wrap"><div class="fgrid">
<div><a class="logo" href="{r}index.html"><span class="mark">$↓</span><span>CobraEn<b>Dólares</b></span></a>
<p>Cuánto te llega de verdad cuando te pagan en dólares desde el exterior. Comisiones de páginas oficiales, con fuente y fecha. Independiente; sin enlaces de afiliado por ahora.</p></div>
<div><h4>Por país</h4><ul>{clinks}</ul></div>
<div><h4>Sitio</h4><ul><li><a href="{r}proveedores/index.html">Proveedores</a></li><li><a href="{r}guia/index.html">Guía práctica</a></li><li><a href="{r}blog/index.html">Blog</a></li><li><a href="{r}cambios/index.html">Historial de cambios</a></li><li><a href="{r}metodologia/index.html">Metodología</a></li><li><a href="{r}data/providers.json">Datos abiertos (JSON)</a></li></ul></div>
<div><h4>Cambios de comisiones, cada semana</h4>{nl_form(r, "footer", "footer")}</div>
</div>
<div class="fbottom"><span>Comisiones revisadas: {CHECKED} · Tipo de cambio: {fecha(RATES["mid"]["date"])}</span><span>No es asesoría financiera · Sin cookies de rastreo ni analíticas</span></div>
</div></footer>
{sticky_html}
<script>window.CED={json.dumps(TC, ensure_ascii=False, separators=(",",":"))};window.CED_ROOT="{r}";</script>
<script src="{r}assets/vendor/uPlot.iife.min.js" defer></script><script src="{r}assets/vendor/countUp.umd.js" defer></script><script src="{r}assets/app.js" defer></script>
</body></html>"""
    p = OUT/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(doc); pages.append(path)

UPLOT_CSS = '<link rel="stylesheet" href="{r}assets/vendor/uPlot.min.css">'
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()

# ---------- HOME ----------
comp_mx = ranking("mx", 1000)[0]
lead_ex = ""
if len(comp_mx) >= 2:
    a, b = comp_mx[0], comp_mx[-1]
    lead_ex = f" Ejemplo real con US$1.000 en México hoy: la diferencia entre opciones con costo publicado llega a {money(((a['netlo']+a['nethi'])/2) - b['netlo'], 'MXN')}."
home = f"""
<section class="hero fx v2" data-cta-trigger>
<div><div class="eyebrow reveal"><i></i>Comisiones revisadas {CHECKED} · 8 proveedores · 5 países</div>
<h1 class="reveal" style="--d:1">Te pagan en dólares. <span class="hl">¿Cuánto te llega de verdad?</span></h1>
<p class="lead reveal" style="--d:1">Payoneer, Wise, DolarApp, Global66, Takenos, Littio, Deel y Airtm, comparados en México, Colombia, Perú, Chile y Argentina: comisión por recibir, margen cambiario, retiro a tu banco y lo que te queda en pesos.{e(lead_ex)}</p>
{amount_box("")}
<div class="reveal" style="--d:3;margin-top:18px">{flag_seg("mx")}</div>
</div>
{hero_card("mx")}
</section>
{market_block()}
{comparator("")}
{ahorrometro()}
<div style="height:56px"></div>
{thermo_block("")}
{chart_block()}
{ar_block()}
<section class="cta-band reveal"><div><h2>Las comisiones cambian sin avisar. Nosotros te avisamos.</h2><p>Un correo por semana: qué proveedor cambió sus tarifas, cómo se movió el dólar en tu país y una idea práctica.</p>
<ul><li>Cambios de comisiones con fuente oficial</li><li>Termómetro del dólar de la semana</li><li>Gratis, sin spam</li></ul></div><div>{nl_form("", "band", "band")}</div></section>
<div style="height:56px"></div>
{coverage("")}
<section class="reveal" aria-labelledby="h-extra"><div class="sh"><div><h2 id="h-extra">Lo que nadie te cuenta al cobrar del exterior</h2><p>Guías con datos y fuentes oficiales.</p></div></div>
<div class="grid g3"><a class="hcard" href="guia/index.html"><span class="lbl">Guía</span><h3>Cómo evitar que te coman el tipo de cambio</h3><span class="mut small">7 hábitos concretos, con los números de cada proveedor.</span></a>
<a class="hcard" href="guia/index.html#cuando"><span class="lbl">Datos</span><h3>¿Cuándo conviene cobrar?</h3><span class="mut small">Cuánto se movió el dólar este mes frente a lo que cuestan las comisiones.</span></a>
<a class="hcard" href="blog/index.html"><span class="lbl">Blog</span><h3>Facturar, impuestos, MEP vs blue y más</h3><span class="mut small">4 artículos para trabajadores remotos, con fuentes oficiales.</span></a></div></section>
<section id="noticias" class="reveal"><div class="sh"><div><h2>Noticias de dólar y economía</h2><p>Titulares reales de 19 fuentes en español (Ámbito, Infobae, iProfesional, El Economista, Portafolio, Gestión, La Tercera y más). Enlazan a la nota original.</p></div><a class="btn sec sm" href="noticias/index.html">Ver todas →</a></div>{news_list(NEWS["items"], 12, True)}</section>
"""
layout("index.html", f"{NAME}: cuánto te llega de verdad al cobrar en dólares (Payoneer, Wise, DolarApp y más)",
       "Compara cuánto recibes al cobrar US$1.000 o cualquier monto del exterior en México, Colombia, Perú, Chile y Argentina con Payoneer, Wise, DolarApp, Global66, Takenos, Littio, Deel y Airtm. Comisiones oficiales con fuente y fecha.",
       home, extra_head=UPLOT_CSS)

# ---------- PAÍSES ----------
for cc, cv in COUNTRIES.items():
    comp, inc, mins, na = ranking(cc, 1000); cur = cv["cur"]
    summ = ""
    if comp:
        best, worst = comp[0], comp[-1]
        summ = (f"Con US$1.000 y datos del {CHECKED}, entre las opciones que publican su costo completo te llegan desde {money(worst['netlo'], cur)} hasta {money(best['nethi'], cur)}. "
                f"{len(inc)} proveedor(es) no publican su margen cambiario y {len(na)} no operan en {cv['name']}.")
    body = f"""<div class="crumbs"><a href="../index.html">Inicio</a> / {e(cv["name"])}</div>
<section class="hero fx v2" data-cta-trigger style="padding-top:24px"><div>
<div class="eyebrow reveal"><i></i>{e(cv["name"])} · {cur} · revisado {CHECKED}</div>
<h1 class="reveal" style="--d:1">Cobrar en dólares en {e(cv["name"])}: <span class="hl">cuánto te llega</span></h1>
<p class="lead reveal" style="--d:1">{e(summ)}</p>{amount_box("../")}<div class="reveal" style="--d:3;margin-top:18px">{flag_seg(cc)}</div></div>{hero_card(cc)}</section>
{market_block()}
{comparator("../", cc)}
{ahorrometro(cc)}
<div style="height:56px"></div>
{thermo_block("../", cc)}
{chart_block(cc)}
{ar_block() if cc == "ar" else ""}
<section class="cta-band reveal"><div><h2>¿Cobras desde {e(cv["name"])}?</h2><p>Te avisamos cuando un proveedor cambie sus comisiones en tu país.</p></div><div>{nl_form("../", "country", cc)}</div></section>"""
    layout(f"{SLUG[cc]}/index.html", f"Cobrar en dólares en {cv['name']}: Payoneer vs Wise vs DolarApp y más ({CHECKED}) | {NAME}",
           f"Cuánto recibes en {cur} al cobrar US$1.000 o cualquier monto desde el exterior en {cv['name']}: comisiones de recepción, margen cambiario y retiro, con fuente oficial.",
           body, kw=f"cobrar en dólares {cv['name']}, recibir dólares {cv['name']}, Payoneer {cv['name']}, Wise {cv['name']}, freelancer {cv['name']}, {cur}", extra_head=UPLOT_CSS)

# ---------- PROVEEDORES ----------
cards = "".join(f'<a class="hcard reveal" style="--d:{i}" href="{p["slug"]}/index.html"><span class="lbl">{e(p["type"])}</span><h3>{e(p["name"])}</h3><span class="mut small">{e(p["summary"])}</span><span class="how">Disponible en: {", ".join(COUNTRIES[c]["name"] for c, v in p["countries"].items() if v["ok"])}</span></a>' for i, p in enumerate(PROV["providers"]))
layout("proveedores/index.html", f"Proveedores para cobrar en dólares desde Latinoamérica | {NAME}", "Comisiones de Payoneer, Wise, DolarApp, Global66, Takenos, Littio, Deel y Airtm por país, con fuente oficial y fecha.",
       f'<div class="page-hero"><span class="eyebrow"><i></i>8 proveedores</span><h1>Proveedores</h1><p class="lead">Qué cobra cada uno por recibir, convertir y retirar, país por país. Cada dato con su fuente oficial.</p></div><section class="grid g3">{cards}</section>{coverage("../")}', active="proveedores/index.html")
for p in PROV["providers"]:
    blocks = ""
    for cc, cv in COUNTRIES.items():
        v = p["countries"][cc]
        if not v["ok"]:
            blocks += f'<div class="card"><h3>{e(cv["name"])}</h3><p><span class="badge">No disponible</span></p><p class="small">{e(v["why"])} {src_link(v["src"])} <span class="dim xs">({fecha(v["date"])})</span></p></div>'; continue
        r1, r2 = calc(p, cc, 1000), calc(p, cc, 2000)
        def nets(r):
            if r["st"] != "ok": return "—"
            return (f'{money(r["netlo"], cv["cur"])} – {money(r["nethi"], cv["cur"])}' if r["range"] else ("≤ " if not r["complete"] else "") + money(r["nethi"], cv["cur"]))
        lis = "".join(f'<li><b>{lab}:</b> {e(v[k]["txt"])} {src_link(v[k]["src"])} <span class="dim xs">({fecha(v[k]["date"])})</span></li>' for k, lab in (("rx","Recepción"),("fx","Cambio"),("wd","Retiro")))
        notes = "".join(f"<li>{e(n)}</li>" for n in v.get("notes", []))
        blocks += f'<div class="card"><h3>{e(cv["name"])}</h3><p class="small dim">{e(v["route"])}</p><ul class="small">{lis}{notes}</ul><table class="qtable"><tr><td>US$1.000 →</td><td>{nets(r1)}</td></tr><tr><td>US$2.000 →</td><td>{nets(r2)}</td></tr></table></div>'
    body = f"""<div class="crumbs"><a href="../../index.html">Inicio</a> / <a href="../index.html">Proveedores</a> / {e(p["name"])}</div>
<div class="page-hero"><div style="display:flex;gap:14px;align-items:center;margin-bottom:12px">{badge(p, ' style="width:48px;height:48px;font-size:16px"')}<span class="eyebrow" style="margin:0"><i></i>Revisado {CHECKED}</span></div>
<h1>{e(p["name"])}: comisiones para cobrar en dólares</h1><p class="lead">{e(p["summary"])}</p><p class="todo">Enlace de afiliado: TODO (pendiente). Cuando exista irá marcado como “enlace de afiliado” y no cambiará el orden de la comparación.</p></div>
<section class="grid g2" style="align-items:start">{blocks}</section>{disc("../../")}
<section class="cta-band"><div><h2>¿{e(p["name"])} cambia sus tarifas?</h2><p>Revisamos sus páginas oficiales a diario y te avisamos en el correo semanal.</p></div><div>{nl_form("../../", "prov", p["slug"])}</div></section>"""
    layout(f"proveedores/{p['slug']}/index.html", f"{p['name']}: comisiones para cobrar en dólares en México, Colombia, Perú, Chile y Argentina | {NAME}",
           f"Cuánto cobra {p['name']} por recibir pagos del exterior, convertir y retirar a tu banco en cada país. Fuentes oficiales con fecha.", body, kw=f"{p['name']} comisiones, {p['name']} tarifas, {p['name']} México, {p['name']} Colombia, {p['name']} Argentina")

# ---------- GUÍA ----------
def vol(c):
    s = HIST["mid"]["rates"][c]; return (max(s) / min(s) - 1) * 100, (s[-1] / (sum(s) / len(s)) - 1) * 100
vol_rows = "".join(f'<tr><td>USD/{c}</td><td>{vol(c)[0]:.2f}%</td><td>{"+" if vol(c)[1]>=0 else ""}{vol(c)[1]:.2f}%</td></tr>' for c in ("MXN","COP","PEN","CLP","ARS"))
if HIST["ar"].get("blue"):
    s = HIST["ar"]["blue"]["venta"]; vol_rows += f'<tr><td>USD/ARS blue</td><td>{(max(s)/min(s)-1)*100:.2f}%</td><td>{(s[-1]/(sum(s)/len(s))-1)*100:+.2f}%</td></tr>'
spread_rows = ""
for cc, cv in COUNTRIES.items():
    comp = ranking(cc, 1000)[0]
    if len(comp) >= 2:
        hi_cost = max(r["costhi"] for r in comp); lo_cost = min(r["costlo"] for r in comp)
        spread_rows += f'<tr><td>{e(cv["name"])}</td><td>{usd(lo_cost)} ({lo_cost/10:.2f}%)</td><td>{usd(hi_cost)} ({hi_cost/10:.2f}%)</td></tr>'
fixed_rows = ""
for name, f in (("DolarApp (recepción)", 3), ("Littio (recepción < US$5.000/día)", 2.99), ("Wise (parte fija de la comisión a MXN)", WISE["cur"].get("MXN", {}).get("fixed", 0))):
    fixed_rows += f'<tr><td>{e(name)}</td><td>US${fmt(f)}</td><td>{f/200*100:.2f}%</td><td>{f/1000*100:.2f}%</td><td>{f/2000*100:.2f}%</td></tr>'
gap_txt = ""
if "blue" in AR and "oficial" in AR and "bolsa" in AR:
    gap_txt = f"Hoy (DolarAPI) el oficial vende a ARS {fmt(AR['oficial']['venta'])}, el MEP a ARS {fmt(AR['bolsa']['venta'])} y el blue a ARS {fmt(AR['blue']['venta'])}: entre el oficial y el blue hay {(AR['blue']['venta']/AR['oficial']['venta']-1)*100:.1f}% de diferencia."
guide = f"""<div class="page-hero"><span class="eyebrow"><i></i>Guía práctica · datos del {CHECKED}</span><h1>Cómo evitar que te coman el tipo de cambio</h1>
<p class="lead">Lo que pierdes al cobrar del exterior casi nunca es “la comisión”: es la suma de lo que te cobran al recibir, el margen escondido en el tipo de cambio y el retiro a tu banco. Estos hábitos salen de las tarifas oficiales que comparamos.</p></div>
<div class="article">
<div class="toc"><b>En esta guía</b><ol><li><a href="#h1">Compara siempre contra el tipo medio</a></li><li><a href="#h2">Pide ACH, no wire ni SWIFT</a></li><li><a href="#h3">Cuidado con las comisiones fijas en montos chicos</a></li><li><a href="#h4">Mira mínimos y máximos</a></li><li><a href="#h5">“Sin comisión” no es “gratis”</a></li><li><a href="#h6">En Argentina, pregunta a qué dólar te pagan</a></li><li><a href="#h7">Cuenta los costos del año, no del mes</a></li><li><a href="#cuando">¿Cuándo conviene cobrar? Lo que dicen los datos</a></li></ol></div>
<h2 id="h1">1. Compara siempre contra el tipo medio</h2>
<p>El tipo medio (mid-market) es el punto entre compra y venta en el mercado mayorista. Cualquier diferencia entre ese valor y el tipo que te aplican es un costo, aunque no figure como “comisión”. La cuenta es simple: <b>margen = 1 − (tipo que te dan ÷ tipo medio)</b>. Si el tipo medio USD/MXN es {fmt(MID["MXN"],4)} y te ofrecen 18,10, el margen es {(1-18.10/MID["MXN"])*100:.2f}%: en US$1.000 son unos {money(MID["MXN"]*1000-18100,"MXN")}.</p>
<p>De los 8 proveedores que comparamos, solo Wise publica una cotización consultable (su API pública indica margen 0 sobre el tipo medio y una comisión visible), y Payoneer publica un rango de 1,2% a 4% para retiros con conversión. Los demás muestran el tipo en la app pero no publican su margen.</p>
<h2 id="h2">2. Pide que te paguen por ACH, no por wire ni SWIFT</h2>
<p>Casi todas las cuentas con datos de EE. UU. reciben ACH gratis o con un cargo pequeño, pero cobran bastante más por wire o SWIFT:</p>
<table><thead><tr><th>Proveedor</th><th>ACH</th><th>Wire / SWIFT</th></tr></thead><tbody>
<tr><td>Wise</td><td>Gratis</td><td>US$6,11 (wire/Swift en USD)</td></tr><tr><td>Global66</td><td>Gratis</td><td>US$10</td></tr>
<tr><td>Takenos</td><td>Gratis</td><td>Wire US$25 · SWIFT US$35</td></tr><tr><td>Airtm</td><td>0,5% a 1,75% según país</td><td>Wire: 10 USDC + 0,5% (mín. US$1.501)</td></tr>
<tr><td>Littio</td><td colspan="2">US$2,99 por transferencia (ACH o US Wire) bajo US$5.000/día</td></tr><tr><td>DolarApp</td><td colspan="2">US$3 por pago recibido con datos de EE. UU.</td></tr></tbody></table>
<p class="src">Fuentes: páginas oficiales de cada proveedor, revisadas el {CHECKED} (enlaces en <a href="../proveedores/index.html">Proveedores</a>).</p>
<h2 id="h3">3. Cuidado con las comisiones fijas en montos chicos</h2>
<p>Una comisión fija pesa mucho más en un pago chico. Si te pagan por proyecto, agrupar facturas reduce el porcentaje que pierdes:</p>
<table><thead><tr><th>Comisión fija</th><th>Monto</th><th>en US$200</th><th>en US$1.000</th><th>en US$2.000</th></tr></thead><tbody>{fixed_rows}</tbody></table>
<h2 id="h4">4. Mira mínimos y máximos antes de pasar tus datos</h2>
<ul><li>Airtm: por ACH de terceros acepta hasta US$2.000 por transferencia, y el retiro directo tiene un máximo de US$1.800 por operación.</li><li>Littio: desde cuentas de terceros, hasta US$4.000 cada 24 horas.</li><li>Deel: retiro mínimo de US$10 por transferencia local (US$5 por Bre-B en Colombia).</li><li>Payoneer: cargo anual de US$29,95 si recibes menos de US$6.000 en 12 meses.</li></ul>
<h2 id="h5">5. “Sin comisión” no es lo mismo que “gratis”</h2>
<p>Varias apps anuncian retiros a tu banco sin comisión. Es cierto, pero la conversión de dólares a pesos ocurre antes y ahí está el margen. En el comparador, esos proveedores aparecen como “Datos incompletos” y su neto se muestra con “≤”: es lo máximo que podrías recibir; lo real será menor.</p>
<h2 id="h6">6. En Argentina, pregunta a qué dólar te pagan</h2>
<p>{e(gap_txt)} Si una plataforma te liquida en pesos, normalmente lo hace a un tipo cercano al oficial. Mantener dólares y convertir por otra vía cambia mucho el resultado. Lo explicamos en <a href="../blog/dolar-mep-vs-blue/index.html">MEP vs blue</a>.</p>
<h2 id="h7">7. Cuenta los costos del año, no del mes</h2>
<p>Una diferencia de 1% parece poco, pero son 12 cobros al año. Usa el <a href="../index.html#ahorrometro">Ahorrómetro</a> para ver la diferencia anual entre la opción más cara y la más barata con costo publicado, en tu país y con tu monto.</p>
<h2 id="cuando">¿Cuándo conviene cobrar? Lo que dicen los datos</h2>
<p>No podemos decirte cuándo va a subir o bajar el dólar, y nadie puede hacerlo con certeza. Lo que sí podemos mostrar es <b>cuánto se movió en los últimos 30 días</b> comparado con lo que cuestan las comisiones:</p>
<table><thead><tr><th>Par</th><th>Rango 30 días (máx./mín.)</th><th>Hoy vs. promedio 30 días</th></tr></thead><tbody>{vol_rows}</tbody></table>
<table><thead><tr><th>País (US$1.000)</th><th>Costo más bajo publicado</th><th>Costo más alto publicado</th></tr></thead><tbody>{spread_rows}</tbody></table>
<ul><li><b>Lo que sí controlas son las comisiones:</b> elegir método y proveedor es una decisión que tomas una vez y se repite en cada cobro. El tipo de cambio puede ir a favor o en contra.</li>
<li><b>Si tu cuenta te deja guardar dólares,</b> puedes separar el momento de cobrar del momento de convertir. Eso no garantiza un mejor tipo; solo te da la opción de convertir cuando necesites los pesos.</li>
<li><b>Los fines de semana</b> muchas apps amplían su margen porque el mercado mayorista está cerrado. Ninguno de los 8 proveedores lo publica; compara el tipo que te muestran con la referencia antes de confirmar.</li>
<li>Revisa el <a href="../index.html#termometro">Termómetro del dólar</a> para ver cómo está hoy frente a su promedio de 30 días.</li></ul>
<p class="disc"><span>Datos pasados, no predicciones. Esto no es asesoría financiera ni de inversión.</span></p>
</div>
<section class="cta-band"><div><h2>Recibe esta guía actualizada cada semana</h2><p>Con los cambios de comisiones y el termómetro del dólar.</p></div><div>{nl_form("../", "guia", "guia")}</div></section>"""
layout("guia/index.html", f"Cómo evitar que te coman el tipo de cambio al cobrar en dólares | {NAME}",
       "Guía práctica con datos: tipo medio vs tipo aplicado, ACH vs wire, comisiones fijas, mínimos, Argentina oficial vs MEP vs blue y cuándo conviene cobrar.", body=guide, active="guia/index.html")

# ---------- BLOG ----------
import articles
for a in articles.ARTICLES:
    body = f"""<div class="crumbs"><a href="../../index.html">Inicio</a> / <a href="../index.html">Blog</a></div>
<div class="page-hero"><span class="eyebrow"><i></i>{e(a["tag"])} · {fecha(a["date"])}</span><h1>{e(a["title"])}</h1><p class="lead">{e(a["lead"])}</p></div>
<div class="article">{articles.render(a, {"AR": AR, "fmt": fmt, "CHECKED": CHECKED, "MID": MID})}
<p class="disc"><span>Contenido informativo y general, no asesoría legal, tributaria ni financiera. Las normas cambian: confirma en las fuentes oficiales enlazadas o con un contador.</span></p></div>
<section class="cta-band"><div><h2>¿Te sirvió?</h2><p>Cada semana mandamos un correo corto con novedades para quienes cobran del exterior.</p></div><div>{nl_form("../../", "blog", a["slug"])}</div></section>"""
    layout(f"blog/{a['slug']}/index.html", f"{a['title']} | {NAME}", a["lead"], body, kw=a["kw"], active="blog/index.html")
bl = "".join(f'<a class="hcard reveal" style="--d:{i}" href="{a["slug"]}/index.html"><span class="lbl">{e(a["tag"])}</span><h3>{e(a["title"])}</h3><span class="mut small">{e(a["lead"])}</span><span class="how">{fecha(a["date"])} · fuentes oficiales</span></a>' for i, a in enumerate(articles.ARTICLES))
layout("blog/index.html", f"Blog para trabajadores remotos que cobran en dólares | {NAME}", "Facturación como contractor, impuestos por país, dólar MEP vs blue y formas de cobrar, con fuentes oficiales.",
       f'<div class="page-hero"><span class="eyebrow"><i></i>Blog</span><h1>Para quienes cobran del exterior</h1><p class="lead">Artículos cortos, con fuentes oficiales y sin promesas.</p></div><section class="grid g2">{bl}</section>', active="blog/index.html")

# ---------- NOTICIAS / CAMBIOS / METODOLOGÍA ----------
layout("noticias/index.html", f"Noticias del dólar y la economía | {NAME}", "Titulares recientes sobre dólar, remesas, fintech e impuestos en México, Colombia, Perú, Chile y Argentina, de 19 medios en español.",
       f'<div class="page-hero"><span class="eyebrow"><i></i>Actualizado {fecha(NEWS.get("generated_at", NEWS.get("generated_utc", PROV["checked"])))}</span><h1>Noticias del dólar y la economía</h1><p class="lead">Titulares de los últimos 7 días sobre dólar, remesas, fintech e impuestos, de 19 fuentes RSS en español (Ámbito, Infobae, iProfesional, El Cronista, La Nación, El Economista, El Financiero, Expansión, Portafolio, La República, El Tiempo, Gestión, El Comercio, La Tercera, Bloomberg Línea, BBC Mundo y Google News). Solo título y enlace: el contenido pertenece a cada medio.</p></div>{news_list(NEWS["items"], 60, True)}', active="noticias/index.html")
def ch_item(c):
    lab = {"detectado": "Detectado automáticamente", "base": "Registro", "documentado": "Documentado"}.get(c["type"], c["type"])
    rev = "" if c.get("reviewed", True) else '<span class="badge warn">pendiente de revisión</span>'
    src = f' · <a href="{e(c["url"])}" rel="nofollow noopener" target="_blank">fuente ↗</a>' if c.get("url") else ""
    return f'<li><time>{fecha(c["date"])}</time><span class="badge acc">{e(lab)}</span>{rev}<div><b>{e(c["title"])}</b></div><div class="dim small">{e(c["provider"])}{src}</div><p>{e(c["detail"])}</p></li>'
layout("cambios/index.html", f"Historial de cambios de comisiones | {NAME}", "Historial fechado de cambios en las comisiones de Payoneer, Wise, DolarApp, Global66, Takenos, Littio, Deel y Airtm.",
       f'<div class="page-hero"><span class="eyebrow"><i></i>Se revisa a diario</span><h1>Historial de cambios</h1><p class="lead">Un robot descarga las páginas oficiales de comisiones y compara su texto con la versión anterior. Si algo cambia, lo marcamos aquí y lo revisamos a mano antes de tocar los datos.</p></div><section class="grid g2" style="grid-template-columns:1.5fr 1fr;align-items:start"><ul class="timeline">{"".join(ch_item(c) for c in CHANGES)}</ul><div class="card" style="position:sticky;top:84px"><h3>Recibe cada cambio</h3>{nl_form("../", "cambios", "cambios")}</div></section>')
srcs = "".join(f'<li><a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(u)}</a></li>' for u in SRC.values())
meth = f"""<div class="page-hero"><span class="eyebrow"><i></i>Transparencia</span><h1>Metodología y fuentes</h1><p class="lead">Cómo calculamos cuánto te llega y de dónde sale cada dato.</p></div>
<section class="grid g2" style="align-items:start">
<div class="card"><h3>El cálculo</h3><ol class="mut small"><li>Monto que te pagan (USD) − comisión de recepción.</li><li>− costo de conversión: comisión de Wise según su cotización en vivo; rango publicado de Payoneer; comisión publicada (Deel en Colombia). Si el proveedor no publica su margen, no lo inventamos: lo marcamos “margen no publicado” y el neto se muestra como máximo posible (“≤”).</li><li>− comisión de retiro a tu banco.</li><li>× tipo de cambio: el de la cotización de Wise para Wise; el tipo medio de referencia para el resto.</li></ol>
<p class="small">Aplicamos comisiones fijas, porcentuales, mínimos, máximos y tramos tal como los publica cada proveedor. Si el monto no alcanza un mínimo, mostramos “monto mínimo no alcanzado”; si supera un máximo publicado, lo señalamos.</p></div>
<div class="card"><h3>Tipos de cambio</h3><p class="small"><b>Referencia (tipo medio):</b> <a href="https://github.com/fawazahmed0/exchange-api" rel="nofollow noopener" target="_blank">currency-api de fawazahmed0</a> (CC0, diario), respaldo <a href="https://www.exchangerate-api.com/docs/free" rel="nofollow noopener" target="_blank">open.er-api.com</a>. <b>Argentina:</b> <a href="https://dolarapi.com" rel="nofollow noopener" target="_blank">DolarAPI</a> (oficial, blue, MEP, CCL, cripto, tarjeta) e histórico de <a href="https://argentinadatos.com" rel="nofollow noopener" target="_blank">ArgentinaDatos</a>. <b>México, Chile y Colombia:</b> DolarAPI como dato complementario. <b>Wise:</b> API pública de comparaciones (sin clave).</p></div>
<div class="card"><h3>Comisiones</h3><p class="small">Revisadas a mano el {CHECKED} en estas páginas oficiales (cada campo del comparador enlaza a la suya):</p><ul class="xs">{srcs}</ul></div>
<div class="card"><h3>Lo que no hacemos</h3><ul class="mut small"><li>No inventamos márgenes ni comisiones: si no están publicados, lo decimos.</li><li>No decimos cuál es “el mejor”.</li><li>No usamos enlaces de afiliado por ahora (están marcados como TODO).</li><li>No usamos cookies de rastreo ni analíticas.</li></ul></div></section>{disc("../")}"""
layout("metodologia/index.html", f"Metodología y fuentes | {NAME}", "Cómo calcula CobraEnDólares lo que te llega al cobrar en dólares y de qué páginas oficiales salen los datos.", meth)

# ---------- SUSCRIPCIÓN ----------
layout("suscribete/index.html", f"Suscríbete: cambios de comisiones y del dólar cada semana | {NAME}", "Un correo por semana con cambios de comisiones de Payoneer, Wise, DolarApp y más, y cómo se movió el dólar en tu país. Gratis.",
       f"""<section class="hero" style="grid-template-columns:1.1fr .9fr"><div><span class="eyebrow"><i></i>Newsletter semanal · gratis</span>
<h1>Lo que cambió esta semana para quienes <span class="hl">cobran en dólares</span>.</h1><p class="lead">Comisiones que subieron o bajaron, el termómetro del dólar en México, Colombia, Perú, Chile y Argentina, y una idea práctica. En 3 minutos.</p>
{nl_form("../", "suscribete", "suscribete")}<p class="dim xs" style="margin-top:14px">Te enviaremos un correo para confirmar la suscripción (doble opt-in). Solo usamos tu correo para mandarte el newsletter.</p></div>
<div class="card"><h3>Qué recibes cada semana</h3><ol class="steps"><li><div><b>Cambios de comisiones</b><div class="dim small">Con fuente oficial y fecha.</div></div></li><li><div><b>Termómetro del dólar</b><div class="dim small">Cómo está tu moneda frente a su promedio de 30 días.</div></div></li><li><div><b>Una idea práctica</b><div class="dim small">Facturación, impuestos, métodos de cobro.</div></div></li></ol></div></section>""", sticky=False)
layout("gracias/index.html", f"Revisa tu correo para confirmar | {NAME}", "Confirma tu suscripción al newsletter de CobraEnDólares.",
       """<div class="page-hero center" style="max-width:640px"><div class="big-emoji" aria-hidden="true">📬</div><h1>Revisa tu correo para confirmar</h1><p class="lead center">Te acabamos de enviar un correo. Tu suscripción se activa cuando haces clic en el enlace de confirmación.</p>
<p class="demo-note" id="demo-flag" hidden>Modo demo: el formulario no está conectado, así que no se envió ningún correo.</p>
<ol class="steps" style="text-align:left"><li><div><b>Abre el correo de confirmación</b><div class="dim small">Llega en 1–2 minutos.</div></div></li><li><div><b>Haz clic en “Confirmar”</b><div class="dim small">Sin ese clic no te llegará nada (doble opt-in).</div></div></li><li><div><b>¿No llegó?</b><div class="dim small">Revisa spam y la pestaña Promociones.</div></div></li></ol>
<a class="btn sec" href="../index.html">Volver al comparador</a></div><script>if(/[?&]demo=1/.test(location.search))document.getElementById("demo-flag").hidden=false;</script>""", sticky=False)
layout("confirmado/index.html", f"Suscripción confirmada | {NAME}", "Tu suscripción al newsletter de CobraEnDólares está confirmada.",
       """<div class="page-hero center" style="max-width:680px"><div class="big-emoji" aria-hidden="true">✅</div><h1>¡Listo, ya estás dentro!</h1><p class="lead center">El próximo correo te llega esta semana.</p>
<div class="grid g3" style="text-align:left;margin-top:24px"><a class="hcard" href="../index.html#comparador"><span class="lbl">Ahora</span><h3>Comparador</h3><span class="dim small">Escribe tu monto.</span></a><a class="hcard" href="../guia/index.html"><span class="lbl">Guía</span><h3>Evita que te coman el tipo de cambio</h3><span class="dim small">7 hábitos con datos.</span></a><a class="hcard" href="../blog/index.html"><span class="lbl">Blog</span><h3>Facturar e impuestos</h3><span class="dim small">Con fuentes oficiales.</span></a></div></div>""", sticky=False)

# ---------- 404 ----------
p404 = (OUT/"index.html").read_text()
nf = '<div class="page-hero center"><div class="big-emoji">🔍</div><h1>Esta página no existe</h1><p class="lead center">Puede que el enlace esté mal o que la página se haya movido.</p><a class="btn pri" href="index.html">Ir al comparador</a></div>'
p404 = re.sub(r'<main id="main" class="wrap">.*</main>', lambda m: f'<main id="main" class="wrap">{nf}</main>', p404, flags=re.S)
p404 = p404.replace('<head><meta charset="utf-8">', f'<head><meta charset="utf-8"><base href="{BASE_PATH}"><meta name="robots" content="noindex">', 1)
(OUT/"404.html").write_text(p404)

# ---------- assets, datos, sitemap ----------
shutil.copytree(ASSETS, OUT/"assets")
(OUT/"data").mkdir()
for f in ("providers.json", "rates.json", "history.json", "wise.json", "news.json", "changes.json"):
    if (DATA/f).exists(): shutil.copy(DATA/f, OUT/"data"/f)
(OUT/".nojekyll").write_text("")
today = datetime.date.today().isoformat()
sm = "".join(f"<url><loc>{SITE_URL}/{re.sub(r'index[.]html$','',p)}</loc><lastmod>{today}</lastmod></url>" for p in pages)
(OUT/"sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
(OUT/"robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
print(f"Sitio generado en {OUT} — {len(pages)} páginas · newsletter: {'Buttondown/'+NL_USER if NL_USER else 'MODO DEMO'}")
