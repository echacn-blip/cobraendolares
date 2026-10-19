"""Mini-blog de CobraEnDólares. Contenido general con enlaces a fuentes oficiales. Sin promesas ni asesoría."""
import html
e = lambda s: html.escape(str(s), quote=True)
def L(url, txt): return f'<a href="{e(url)}" rel="nofollow noopener" target="_blank">{e(txt)} ↗</a>'

ARTICLES = [
 {"slug": "facturar-como-contractor", "tag": "Facturación", "date": "2026-10-19",
  "title": "Facturar al exterior como contractor: lo básico en México, Colombia, Perú, Chile y Argentina",
  "lead": "Qué comprobante emites cuando un cliente de otro país te paga por tu trabajo, y dónde está la información oficial de cada país.",
  "kw": "facturar al exterior, exportación de servicios, contractor, freelancer, CFDI, factura electrónica, recibo por honorarios, boleta de honorarios, factura E"},
 {"slug": "impuestos-freelancer-latam", "tag": "Impuestos", "date": "2026-10-19",
  "title": "Impuestos de quien cobra en dólares desde Latinoamérica: panorama y enlaces oficiales",
  "lead": "Cobrar del exterior no te saca del sistema tributario de tu país. Un mapa de qué preguntas hacerte y a qué autoridad acudir.",
  "kw": "impuestos freelancer, SAT, DIAN, SUNAT, SII, ARCA, ingresos del exterior, declarar dólares"},
 {"slug": "dolar-mep-vs-blue", "tag": "Argentina", "date": "2026-10-19",
  "title": "Dólar MEP vs blue vs oficial: qué son y por qué importan si cobrás del exterior",
  "lead": "En Argentina conviven varios tipos de cambio. Si te pagan en dólares, el que te apliquen cambia cuánto te queda.",
  "kw": "dólar MEP, dólar blue, dólar oficial, brecha cambiaria, cobrar del exterior Argentina, CCL"},
 {"slug": "ach-wire-swift", "tag": "Cómo cobrar", "date": "2026-10-19",
  "title": "ACH, wire o SWIFT: cuánto cuesta cada forma de cobrar en dólares",
  "lead": "La misma factura puede costarte US$0 o US$35 según cómo te transfieran. Las tarifas publicadas, proveedor por proveedor.",
  "kw": "ACH, wire, SWIFT, recibir dólares, routing number, cuenta en Estados Unidos, comisiones"},
]

def render(a, ctx):
    s = a["slug"]
    if s == "facturar-como-contractor": return f"""
<p>Cuando trabajas como contratista independiente para un cliente del exterior, en general sigues siendo contribuyente en tu país y debes documentar el ingreso con el comprobante que exige tu autoridad tributaria. Muchas veces el servicio puede calificar como <b>exportación de servicios</b>, que suele tener un tratamiento distinto en IVA o IGV, siempre que cumplas los requisitos de cada país.</p>
<h2>México</h2><p>Las personas físicas que prestan servicios profesionales o tienen actividad empresarial emiten un CFDI (factura electrónica). La Ley del IVA contempla tasa 0% para ciertos servicios que se aprovechan en el extranjero (exportación de servicios), con condiciones. Información oficial: {L("https://www.sat.gob.mx", "SAT")}.</p>
<h2>Colombia</h2><p>Necesitas el RUT y, si estás obligado, emitir factura electrónica o documento soporte. La exportación de servicios puede estar exenta de IVA si se cumplen los requisitos del Estatuto Tributario. Información oficial: {L("https://www.dian.gov.co", "DIAN")}.</p>
<h2>Perú</h2><p>Los trabajadores independientes suelen emitir recibo por honorarios electrónico (rentas de cuarta categoría). Si facturas como empresa o con negocio, aplican otras reglas, incluida la exportación de servicios para el IGV. Información oficial: {L("https://www.sunat.gob.pe", "SUNAT")}.</p>
<h2>Chile</h2><p>Lo habitual es emitir boleta de honorarios electrónica. Si el cliente es extranjero no hay retención automática, así que la persona paga sus pagos provisionales y los declara. La tasa de retención cambia cada año según la ley vigente. Información oficial: {L("https://www.sii.cl", "SII")}.</p>
<h2>Argentina</h2><p>Puedes facturar como monotributista o responsable inscripto. Para clientes del exterior se usa la factura de exportación (tipo E). Además, las reglas sobre ingreso y liquidación de divisas las fija el Banco Central y cambian seguido. Información oficial: {L("https://www.arca.gob.ar", "ARCA (ex AFIP)")} y {L("https://www.bcra.gob.ar", "BCRA")}.</p>
<h2>Antes de facturar, chequea</h2><ul><li>Que el comprobante tenga los datos del cliente extranjero como pide tu autoridad (algunos países usan un identificador genérico para extranjeros).</li><li>Qué tipo de cambio exige tu país para registrar el ingreso en moneda local.</li><li>Que el monto facturado coincida con lo que recibes antes de comisiones: las comisiones de la plataforma suelen ser un gasto aparte.</li></ul>"""
    if s == "impuestos-freelancer-latam": return f"""
<p>Una cuenta en dólares o una billetera digital no cambia de dónde eres residente fiscal. Si vives en uno de estos países, en general tus ingresos del exterior se declaran allí. Estas son las preguntas que conviene llevar a tu contador, con la autoridad oficial de cada país:</p>
<table><thead><tr><th>País</th><th>Autoridad</th><th>Preguntas clave</th></tr></thead><tbody>
<tr><td>México</td><td>{L("https://www.sat.gob.mx", "SAT")}</td><td>¿Régimen de actividad profesional o RESICO? ¿Mi servicio califica como exportación (IVA 0%)? ¿Cómo hago los pagos provisionales?</td></tr>
<tr><td>Colombia</td><td>{L("https://www.dian.gov.co", "DIAN")}</td><td>¿Debo facturar electrónicamente? ¿Cumplo requisitos de exportación de servicios? ¿Cómo declaro renta y si aplica régimen simple?</td></tr>
<tr><td>Perú</td><td>{L("https://www.sunat.gob.pe", "SUNAT")}</td><td>¿Rentas de cuarta categoría? ¿Debo hacer pagos a cuenta? ¿Qué pasa si supero los límites para suspender retenciones?</td></tr>
<tr><td>Chile</td><td>{L("https://www.sii.cl", "SII")}</td><td>¿Cómo pago los PPM si el cliente no retiene? ¿Qué tasa de retención aplica este año? ¿Cómo se refleja en la Operación Renta?</td></tr>
<tr><td>Argentina</td><td>{L("https://www.arca.gob.ar", "ARCA")} · {L("https://www.bcra.gob.ar", "BCRA")}</td><td>¿Monotributo o responsable inscripto? ¿Qué categoría me corresponde? ¿Qué obligaciones cambiarias tengo al cobrar exportaciones de servicios?</td></tr></tbody></table>
<h2>Tres errores comunes</h2><ul><li><b>Pensar que una cuenta en EE. UU. “no se ve”.</b> Los países comparten información financiera y los proveedores piden tu identificación tributaria.</li><li><b>Declarar el neto en vez del bruto.</b> Las comisiones de cobro suelen tratarse como gasto; el ingreso es lo que facturaste.</li><li><b>Usar cualquier tipo de cambio.</b> Cada país indica qué tipo usar para convertir el ingreso a moneda local.</li></ul>
<p class="src">Revisado el {ctx["CHECKED"]}. Solo enlazamos a las autoridades oficiales; no citamos tasas porque cambian año a año.</p>"""
    if s == "dolar-mep-vs-blue":
        AR, fmt = ctx["AR"], ctx["fmt"]
        rows = "".join(f'<tr><td>{e(n)}</td><td>{fmt(AR[k]["compra"])}</td><td>{fmt(AR[k]["venta"])}</td></tr>' for k, n in (("oficial","Oficial"),("mayorista","Mayorista"),("bolsa","MEP (bolsa)"),("contadoconliqui","Contado con liquidación"),("blue","Blue"),("cripto","Cripto"),("tarjeta","Tarjeta")) if k in AR)
        gap = f'{(AR["blue"]["venta"]/AR["oficial"]["venta"]-1)*100:.1f}%' if "blue" in AR and "oficial" in AR else "—"
        gapm = f'{(AR["bolsa"]["venta"]/AR["oficial"]["venta"]-1)*100:.1f}%' if "bolsa" in AR and "oficial" in AR else "—"
        return f"""
<p>Hoy, según DolarAPI (datos del {ctx["CHECKED"]}), estas son las cotizaciones en pesos por dólar:</p>
<table><thead><tr><th>Tipo</th><th>Compra</th><th>Venta</th></tr></thead><tbody>{rows}</tbody></table>
<p>La diferencia entre el blue y el oficial (venta) es de <b>{gap}</b>; entre el MEP y el oficial, <b>{gapm}</b>.</p>
<h2>Qué es cada uno</h2><ul><li><b>Oficial:</b> el que publican los bancos. Es el que suelen usar las plataformas cuando te liquidan en pesos.</li><li><b>Mayorista:</b> el del mercado entre bancos y empresas; la referencia del Banco Central.</li><li><b>MEP (bolsa):</b> resulta de comprar un bono en pesos y venderlo en dólares (o al revés) a través de un broker o banco. Es legal y queda registrado.</li><li><b>Contado con liquidación (CCL):</b> parecido al MEP, pero los dólares quedan en una cuenta del exterior.</li><li><b>Blue:</b> el del mercado informal. Lo publican medios y agregadores, pero no es un mercado regulado.</li><li><b>Tarjeta:</b> el oficial más impuestos y percepciones para consumos en dólares.</li></ul>
<h2>Por qué importa si cobrás del exterior</h2><p>Si una plataforma convierte tus dólares a pesos al tipo oficial, el resultado puede ser distinto a si mantenés los dólares y luego los vendés por otra vía. Por eso, en el <a href="../../argentina/index.html">comparador de Argentina</a> mostramos también la referencia de MEP y blue. Además, las normas del {L("https://www.bcra.gob.ar", "BCRA")} sobre cobro de exportaciones de servicios cambian seguido: revisalas o consultá a un contador.</p>
<p class="src">Fuente de cotizaciones: {L("https://dolarapi.com", "DolarAPI")}. Histórico: {L("https://argentinadatos.com", "ArgentinaDatos")}.</p>"""
    if s == "ach-wire-swift": return f"""
<p>Tu cliente puede mandarte dólares de varias maneras. La diferencia de costo es enorme y casi siempre la eliges tú al pasar tus datos.</p>
<h2>Las tres vías</h2><ul><li><b>ACH:</b> transferencia local dentro de EE. UU. Lenta (1 a 5 días hábiles) pero barata. Requiere routing number y número de cuenta en EE. UU.</li><li><b>Wire (Fedwire):</b> transferencia rápida dentro de EE. UU. Más cara para quien envía y, a veces, para quien recibe.</li><li><b>SWIFT:</b> transferencia internacional entre bancos. Puede pasar por bancos intermediarios que descuentan sus propias comisiones.</li></ul>
<h2>Lo que cobra cada proveedor por recibir</h2>
<table><thead><tr><th>Proveedor</th><th>ACH</th><th>Wire</th><th>SWIFT</th></tr></thead><tbody>
<tr><td>Wise</td><td>Gratis</td><td colspan="2">US$6,11 (wire y Swift en USD)</td></tr>
<tr><td>Global66</td><td>Gratis</td><td>US$10</td><td>US$10</td></tr>
<tr><td>Takenos</td><td>Gratis</td><td>US$25</td><td>US$35 (mín. US$100)</td></tr>
<tr><td>Littio</td><td colspan="2">US$2,99 (bajo US$5.000/día); 0,6% por encima</td><td>—</td></tr>
<tr><td>DolarApp</td><td colspan="2">US$3 por pago con datos de EE. UU.</td><td>—</td></tr>
<tr><td>Airtm</td><td>0,5% (AR) · 0,50 + 0,5% máx. 10 (CO) · 1,75% (otros)</td><td>10 USDC + % (mín. US$1.501)</td><td>—</td></tr>
<tr><td>Payoneer</td><td colspan="3">1% (mín. US$1) en cuenta receptora en USD si no es tu moneda local</td></tr>
<tr><td>Deel</td><td colspan="3">Sin cargo para el contratista al recibir; SWIFT de retiro: US$5 a US$10</td></tr></tbody></table>
<p class="src">Fuentes: páginas oficiales de cada proveedor, revisadas el {ctx["CHECKED"]}. Enlaces en <a href="../../proveedores/index.html">Proveedores</a>.</p>
<h2>Qué pedirle a tu cliente</h2><ul><li>Pasa tus datos de ACH (routing + cuenta) y pide explícitamente “ACH”, no “wire”.</li><li>Si te paga por una plataforma (Deel, Upwork, etc.), revisa qué métodos de retiro tiene y cuánto cobra cada uno.</li><li>Para montos grandes, verifica los máximos por transferencia: por ejemplo, Airtm acepta hasta US$2.000 por ACH de terceros.</li></ul>"""
    return ""
