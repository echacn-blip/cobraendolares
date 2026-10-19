#!/usr/bin/env python3
"""CobraEnDólares – datos de comisiones verificados A MANO en páginas oficiales (fecha en CHECKED).
Regla: si la fuente oficial no publica un dato, va como "unpublished" (margen no publicado) o "unknown" (sin verificar). Nunca se inventa.
Tipos de componente (k):
  fixed      monto fijo en USD                 {fixed}
  pct        porcentaje con mín./máx. opcional {pct, min, max}
  fixed_pct  fijo + porcentaje, máx. opcional  {fixed, pct, max}
  range_pct  rango publicado de %              {lo, hi}
  tiered     tramos por monto                  {tiers:[{upto, fixed|pct}...]}
  wise       cotización oficial en vivo (API pública de Wise)  -> data/wise.json
  included   incluido en otro componente (US$0 adicional)
  unpublished  el proveedor no publica el margen cambiario
  unknown    sin verificar (no encontramos el dato en una fuente oficial)
Uso: python3 scripts/seed_providers.py  -> data/providers.json"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKED = "2026-10-19"
S = {
 "payoneer_pricing": "https://www.payoneer.com/about/pricing/",
 "wise_receive": "https://wise.com/us/pricing/receive",
 "wise_api": "https://api.wise.com/v4/comparisons/?sourceCurrency=USD&targetCurrency=MXN&sendAmount=1000",
 "wise_hold": "https://wise.com/help/articles/2813542/where-do-i-need-to-live-to-hold-money-with-wise",
 "dolarapp_costs": "https://help.dolarapp.com/en/articles/7109639-dolarapp-costs-and-fees",
 "dolarapp_times": "https://help.dolarapp.com/es/articles/10327550-tiempos-estimados-para-completar-operaciones-o-transferencias-en-dolarapp",
 "g66_receive": "https://ayuda.global66.com/docs/primeros-pasos/recibe-dinero-directamente-a-tu-cuenta-en-usd-eur-y-gbp-con-global66/",
 "g66_load": "https://ayuda.global66.com/docs/informacion-importante/como-cargar-mi-cuenta-en-usd/",
 "g66_co_pdf": "https://bases.global66.com/wp-content/uploads/2026/02/Tarifario-Global66-SEDPE-B2C-04-02-v2.pdf",
 "takenos_receive": "https://help.takenos.com/en/articles/9981728-en-que-monedas-puedo-recibir-dinero-en-takenos",
 "takenos_send": "https://help.takenos.com/en/articles/9820507-cuanto-cuesta-enviar-fondos-en-takenos",
 "takenos_countries": "https://help.takenos.com/en/articles/9745376-en-que-paises-esta-disponible-takenos",
 "takenos_mx": "https://help.takenos.com/en/articles/9714053-como-puedo-enviar-pesos-mexicanos-en-mexico",
 "takenos_blog_paises": "https://takenos.com/blog/blog-takenos-paises-habilitados",
 "takenos_blog_fees": "https://takenos.com/blog/takenos-y-sus-comisiones-cu%C3%A1les-son-los-costos-y-comisiones-de-takenos",
 "littio_us": "https://intercom.help/littio/es/articles/9161786-como-solicito-los-datos-de-mi-cuenta-ee-uu",
 "littio_blog": "https://littio.co/blog/como-traer-dolares-a-colombia",
 "littio_withdraw": "https://intercom.help/littio/es/articles/6443593-cuales-son-las-comisiones-por-retirar-o-transferir-desde-mi-cuenta-littio",
 "littio_landing": "https://littio.co/cuenta-en-dolares",
 "deel_cost": "https://help.letsdeel.com/hc/en-gb/articles/4407737725201-How-Much-Does-Deel-Cost",
 "deel_withdraw": "https://help.letsdeel.com/hc/en-gb/articles/14391381019537-About-Withdrawal-Fees-and-Withdrawal-Minimums",
 "deel_how": "https://help.letsdeel.com/hc/en-gb/articles/7338494928913-How-Contractors-Can-Withdraw-Money-From-Deel",
 "deel_breb": "https://help.letsdeel.com/hc/en-gb/articles/43892925141905-Instant-Withdrawals-in-Colombia-with-Bre-B",
 "airtm_ach": "https://help.airtm.com/es-LA/support/solutions/articles/47001265604-c%C3%B3mo-recibir-fondos-en-tu-cuenta-virtual-usa",
 "airtm_direct": "https://help.airtm.com/es-LA/support/solutions/articles/47001198154--c%C3%B3mo-puedo-retirar-directamente-no-p2p-de-mi-cuenta-airtm-a-un-banco-",
}
C = lambda k, src, txt, **kw: {"k": k, "src": src, "txt": txt, "date": CHECKED, **kw}
UNPUB = lambda src, txt="El proveedor no publica el margen sobre el tipo de cambio; lo ves en la app antes de confirmar.": C("unpublished", src, txt)
UNK = lambda src, txt: C("unknown", src, txt)
NA = lambda src, why: {"ok": False, "why": why, "src": src, "date": CHECKED}
COUNTRIES = {"mx": ("México", "MXN"), "co": ("Colombia", "COP"), "pe": ("Perú", "PEN"), "cl": ("Chile", "CLP"), "ar": ("Argentina", "ARS")}

P = []
# ---------------- Payoneer ----------------
pay = {}
for c in COUNTRIES:
    pay[c] = {"ok": True, "src": "payoneer_pricing", "date": CHECKED, "route": "Cuenta receptora en USD (tu cliente paga por transferencia local en EE. UU.) → retiro a tu banco en moneda local",
        "rx": C("pct", "payoneer_pricing", "1% (mínimo US$1) por recibir en una cuenta receptora en una moneda que no es la de tu país.", pct=1, min=1),
        "fx": C("range_pct", "payoneer_pricing", "Retiro a un banco en otra moneda, con conversión: 1,2%–4% según país y corredor. Payoneer publica solo el rango.", lo=1.2, hi=4),
        "wd": C("included", "payoneer_pricing", "Incluido en el 1,2%–4% del retiro con conversión."),
        "notes": ["Cargo anual de US$29,95 si recibes menos de US$6.000 en 12 meses seguidos (no incluido en el cálculo)."]}
P.append({"slug": "payoneer", "name": "Payoneer", "mono": "Py", "type": "Cuenta de cobros internacional", "affiliate": "TODO",
          "summary": "Te da cuentas receptoras en USD y otras monedas para cobrar a clientes y marketplaces; luego retiras a tu banco.", "countries": pay})
# ---------------- Wise ----------------
wise = {}
for c in COUNTRIES:
    wise[c] = {"ok": True, "src": "wise_hold", "date": CHECKED, "route": "Datos de cuenta en USD de Wise (ACH gratis) → conversión y envío a tu banco en moneda local",
        "rx": C("fixed", "wise_receive", "Recibir pagos domésticos en USD (ACH, no wire): gratis. Wire/Swift en USD: US$6,11 (no incluido).", fixed=0),
        "fx": C("wise", "wise_api", "Comisión de Wise según su cotización pública en vivo (API de comparaciones); Wise informa margen 0 sobre el tipo medio."),
        "wd": C("included", "wise_api", "El envío a tu banco local está incluido en la cotización."),
        "notes": ["Wise permite tener saldo a residentes de los 5 países (centro de ayuda de Wise).",
                  "La cotización de Wise corresponde a una transferencia USD → moneda local; el costo real dentro de la cuenta puede variar levemente."]}
P.append({"slug": "wise", "name": "Wise", "mono": "Wi", "type": "Cuenta multidivisa", "affiliate": "TODO",
          "summary": "Cuenta con datos bancarios en USD para recibir y conversión al tipo de cambio medio con comisión visible.", "countries": wise})
# ---------------- DolarApp (ARQ) ----------------
da = {}
for c in ("mx", "co", "ar"):
    da[c] = {"ok": True, "src": "dolarapp_times", "date": CHECKED, "route": "Datos de cuenta en EE. UU. (ACH/wire) → venta de dólares digitales → retiro en moneda local",
        "rx": C("fixed", "dolarapp_costs", "US$3 (USDc) por recibir pagos usando tus datos de cuenta de EE. UU. (plan Standard).", fixed=3),
        "fx": UNPUB("dolarapp_costs", "DolarApp no publica el margen de compra/venta de sus dólares digitales; el precio se ve en la app."),
        "wd": C("fixed", "dolarapp_costs", "Depósitos y transferencias en moneda local: sin comisión.", fixed=0), "notes": ["Desde 2026 la marca también aparece como ARQ."]}
for c in ("pe", "cl"):
    da[c] = NA("dolarapp_times", "Su centro de ayuda solo menciona operaciones en ARS, COP, MXN y BRL.")
P.append({"slug": "dolarapp", "name": "DolarApp (ARQ)", "mono": "DA", "type": "App de dólares digitales", "affiliate": "TODO",
          "summary": "Cuenta en dólares digitales (USDc) con datos bancarios de EE. UU. para México, Colombia y Argentina.", "countries": da})
# ---------------- Global66 ----------------
g = {}
for c in ("co", "pe", "cl", "ar"):
    g[c] = {"ok": True, "src": "g66_receive", "date": CHECKED, "route": "Cuenta Global en USD (ACH gratis) → conversión a moneda local → retiro a tu banco",
        "rx": C("fixed", "g66_receive", "ACH: recepción gratuita. Wire o SWIFT: US$10 (no incluido).", fixed=0),
        "fx": UNPUB("g66_receive", "Global66 no publica el margen de conversión de USD a moneda local; se ve al cotizar en la app."),
        "wd": UNK("g66_receive", "No encontramos la comisión de retiro a banco nacional en una fuente oficial para este país."), "notes": []}
g["co"]["wd"] = C("fixed", "g66_co_pdf", "Retiro a cuenta bancaria nacional: US$0,60 + IVA (19%) = US$0,714, cobrado en COP (tarifario oficial, feb. 2026).", fixed=0.714)
g["co"]["notes"].append("Manejo mensual de COP 8.403 solo si no hubo operaciones el mes anterior (no incluido).")
g["mx"] = NA("g66_receive", "La cuenta en USD con datos de EE. UU. está disponible en Chile, Colombia, Ecuador, Argentina y Perú; México no aparece.")
P.append({"slug": "global66", "name": "Global66", "mono": "G6", "type": "Cuenta global multidivisa", "affiliate": "TODO",
          "summary": "Cuenta Global con Routing Number de EE. UU. e IBAN europeo para personas en Chile, Colombia, Perú y Argentina.", "countries": g})
# ---------------- Takenos ----------------
t = {}
for c, (src, txt) in {"mx": ("takenos_mx", "Envío de pesos mexicanos a cuenta propia: sin comisión (solo usuarios con INE o pasaporte mexicano)."),
                      "pe": ("takenos_send", "Soles (PEN): sin costo."), "cl": ("takenos_send", "Pesos chilenos (CLP): sin costo."),
                      "ar": ("takenos_send", "Pesos argentinos (ARS): sin costo.")}.items():
    t[c] = {"ok": True, "src": "takenos_countries", "date": CHECKED, "route": "Datos de cuenta en EE. UU. (ACH gratis) → conversión → retiro en moneda local",
        "rx": C("fixed", "takenos_receive", "Transferencia ACH: sin comisión. Wire: US$25; SWIFT: US$35 (no incluidos).", fixed=0),
        "fx": UNPUB("takenos_mx" if c == "mx" else "takenos_send", "Takenos muestra el tipo de cambio antes de enviar, pero no publica su margen."),
        "wd": C("fixed", src, txt, fixed=0), "notes": []}
t["ar"]["notes"].append("Alternativa en Argentina: retirar dólares a tu cuenta bancaria argentina en USD con 1% de comisión (blog oficial de Takenos).")
t["co"] = NA("takenos_blog_paises", "En Colombia Takenos permite recibir USD/EUR y pagar con QR, pero no ofrece retiro a banco en pesos colombianos.")
P.append({"slug": "takenos", "name": "Takenos", "mono": "Tk", "type": "Billetera en dólares digitales", "affiliate": "TODO",
          "summary": "Billetera con datos bancarios de EE. UU. (ACH sin comisión) y retiros en moneda local en varios países.", "countries": t})
# ---------------- Littio ----------------
l = {}
l["co"] = {"ok": True, "src": "littio_us", "date": CHECKED, "route": "Cuenta Littio EE. UU. (ACH/US Wire) → USDC → pesos → retiro a tu banco",
    "rx": C("tiered", "littio_blog", "US$2,99 por transferencia si recibes menos de US$5.000 en 24 h; 0,6% del total si superas US$5.000.", tiers=[{"upto": 5000, "fixed": 2.99}, {"pct": 0.6}]),
    "fx": UNPUB("littio_landing", "Littio no publica el margen al convertir USDC a pesos."),
    "wd": C("fixed", "littio_withdraw", "Retiros a cuenta bancaria propia en Colombia: sin comisión (retiros menores a COP 20.000: US$0,50).", fixed=0),
    "notes": ["Su centro de ayuda indica US$2,99 fijo sin importar el monto; su blog agrega el 0,6% sobre US$5.000 diarios. Usamos la regla del blog.",
              "Desde cuentas de terceros: hasta US$4.000 cada 24 h."], "max": 4000, "max_txt": "Límite para pagos de terceros: US$4.000 cada 24 h"}
for c in ("mx", "ar"):
    l[c] = {"ok": True, "src": "littio_us", "date": CHECKED, "route": "Cuenta Littio EE. UU. → transferencia a banco local",
        "rx": l["co"]["rx"], "fx": UNPUB("littio_landing", "Littio no publica el margen de conversión."),
        "wd": C("fixed", "littio_landing", "Transferencias a bancos en Colombia, México y Argentina: US$0 (página oficial).", fixed=0),
        "notes": ["Littio acepta documentos mexicanos y argentinos para la cuenta EE. UU.; la operación principal de Littio es en Colombia."] + l["co"]["notes"][1:], "max": 4000, "max_txt": l["co"]["max_txt"]}
for c in ("pe", "cl"):
    l[c] = NA("littio_landing", "Littio no ofrece transferencias a bancos de este país (solo Colombia, México y Argentina).")
P.append({"slug": "littio", "name": "Littio", "mono": "Li", "type": "Cuenta en dólares digitales (Colombia)", "affiliate": "TODO",
          "summary": "Cuenta en dólares y euros digitales con datos de EE. UU.; enfocada en Colombia.", "countries": l})
# ---------------- Deel ----------------
d = {}
for c in COUNTRIES:
    d[c] = {"ok": True, "src": "deel_withdraw", "date": CHECKED, "route": "Tu cliente te paga por Deel → retiro por transferencia bancaria local",
        "rx": C("fixed", "deel_cost", "Deel no cobra al contratista por recibir; la empresa paga la suscripción (desde US$49 por contrato al mes).", fixed=0),
        "fx": UNPUB("deel_how", "Si retiras en una moneda distinta a la de tu contrato se aplican tipo de cambio y comisión de cambio, que Deel muestra antes de confirmar pero no publica."),
        "wd": C("fixed", "deel_withdraw", "Transferencia bancaria local: US$0 de Deel (pueden aplicar comisiones del proveedor en algunas monedas).", fixed=0),
        "min": 10, "min_txt": "Retiro mínimo por transferencia local: US$10", "notes": ["Solo aplica si tu cliente te contrata y paga a través de Deel."]}
d["co"]["fx"] = C("fixed_pct", "deel_breb", "USD → COP por Bre-B: comisión cambiaria de US$3 + 1,5% (aplicada por su proveedor).", fixed=3, pct=1.5)
d["co"]["wd"] = C("fixed", "deel_breb", "Bre-B: COP → COP gratis. Mínimo US$5; máximo COP 11.500.000 por retiro.", fixed=0)
d["co"]["min"] = 5; d["co"]["min_txt"] = "Mínimo por Bre-B: US$5"
P.append({"slug": "deel", "name": "Deel", "mono": "De", "type": "Plataforma de pagos a contratistas", "affiliate": "TODO",
          "summary": "Plataforma con la que muchas empresas pagan a contratistas; tú eliges cómo y en qué moneda retirar.", "countries": d})
# ---------------- Airtm ----------------
a = {}
rx = {"ar": C("pct", "airtm_ach", "ACH a la Cuenta Virtual USA (Argentina): 0,50%.", pct=0.5),
      "co": C("fixed_pct", "airtm_ach", "ACH (Colombia): 0,50 USDC + 0,50%, máximo 10 USDC.", fixed=0.5, pct=0.5, max=10),
      "mx": C("pct", "airtm_ach", "ACH (otros países, incluye México): 1,75%.", pct=1.75),
      "pe": C("pct", "airtm_ach", "ACH (otros países, incluye Perú): 1,75%.", pct=1.75),
      "cl": C("pct", "airtm_ach", "ACH (otros países, incluye Chile): 1,75%.", pct=1.75)}
for c in COUNTRIES:
    a[c] = {"ok": True, "src": "airtm_direct", "date": CHECKED, "route": "Cuenta Virtual USA (ACH) → retiro directo a tu banco",
        "rx": rx[c], "fx": UNPUB("airtm_direct", "Airtm no publica el tipo de cambio ni el costo del retiro directo; los ves en la app."),
        "wd": UNK("airtm_direct", "Airtm dice que el retiro directo tiene 'costos más bajos según el método', sin publicar la tarifa."),
        "max": 2000, "max_txt": "ACH de terceros: máximo US$2.000 por transferencia",
        "notes": ["Retiro directo: máximo US$1.800 por operación y US$8.000 al mes" + (" (US$2.000 al mes en Argentina)." if c == "ar" else ".")]}
P.append({"slug": "airtm", "name": "Airtm", "mono": "At", "type": "Billetera en dólares digitales + P2P", "affiliate": "TODO",
          "summary": "Billetera en USDC con Cuenta Virtual USA para recibir ACH y retiros directos o P2P a bancos locales.", "countries": a})

out = {"checked": CHECKED, "countries": {k: {"name": v[0], "cur": v[1]} for k, v in COUNTRIES.items()}, "sources": S, "providers": P,
       "disclaimer": "Información de comisiones publicada por cada proveedor, revisada en la fecha indicada. Puede cambiar sin aviso. No es asesoría financiera: confirma siempre el costo final en la app del proveedor antes de operar."}
(ROOT/"data").mkdir(exist_ok=True)
(ROOT/"data"/"providers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("data/providers.json:", len(P), "proveedores")
