(function(){
"use strict";
var D = window.CED, ROOT = window.CED_ROOT || "";
var REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
var P = D.prov, C = P.countries, SRC = P.sources;
var MID = Object.assign({}, D.rates.mid.rates), MIDDATE = D.rates.mid.date;
var AR = {}; (D.rates.ar || []).forEach(function(x){ AR[x.casa] = x; });
var WISE = (D.wise && D.wise.cur) || {}, LIVEW = {};
var MES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
function fecha(iso){ var p = iso.slice(0,10).split("-"); return (+p[2]) + " " + MES[+p[1]-1] + " " + p[0]; }
function esc(s){ return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
function nf(v, d){ return new Intl.NumberFormat("es-419",{minimumFractionDigits:d,maximumFractionDigits:d}).format(v); }
function money(v, cur){ var d = (cur==="COP"||cur==="CLP"||cur==="ARS") ? 0 : 2; return cur + " " + nf(v, d); }
function usd(v){ return "US$" + nf(v, 2); }
function $(s, el){ return (el||document).querySelector(s); }
function $$(s, el){ return Array.prototype.slice.call((el||document).querySelectorAll(s)); }

// ---- monto: acepta 375.20, 375,20, 1.000, 1,000, 1.234,56 ----
function parseAmount(s){
  s = String(s||"").replace(/[\sUS$usd]/gi, "");
  if(!s) return NaN;
  if(!/^[\d.,]+$/.test(s)) return NaN;
  var hasC = s.indexOf(",") >= 0, hasD = s.indexOf(".") >= 0;
  if(hasC && hasD){ var dec = s.lastIndexOf(",") > s.lastIndexOf(".") ? "," : "."; var th = dec === "," ? "." : ",";
    s = s.split(th).join("").replace(dec, "."); }
  else if(hasC || hasD){ var sep = hasC ? "," : "."; var parts = s.split(sep);
    if(parts.length > 2 || (parts.length === 2 && parts[1].length === 3 && parts[0].length >= 1 && parts[0] !== "0")) s = parts.join("");
    else s = parts.join("."); }
  var v = parseFloat(s); return isFinite(v) ? v : NaN;
}

// ---- motor de cálculo (igual que scripts/build.py) ----
function fee(c, A){
  var k = c.k, v;
  if(k === "fixed") return [c.fixed, c.fixed, true];
  if(k === "pct"){ v = A*c.pct/100; v = Math.max(v, c.min||0); if(c.max) v = Math.min(v, c.max); return [v, v, true]; }
  if(k === "fixed_pct"){ v = c.fixed + A*c.pct/100; if(c.max) v = Math.min(v, c.max); return [v, v, true]; }
  if(k === "range_pct") return [A*c.lo/100, A*c.hi/100, true];
  if(k === "tiered"){ for(var i=0;i<c.tiers.length;i++){ var t = c.tiers[i]; if(t.upto === undefined || A < t.upto){ v = t.fixed !== undefined ? t.fixed : A*(t.pct||0)/100; return [v, v, true]; } } }
  if(k === "included") return [0, 0, true];
  return [0, 0, false];
}
function calc(p, cc, A){
  var v = p.countries[cc], cur = C[cc].cur, mid = MID[cur];
  if(!v || !v.ok) return {st:"na", why: v ? v.why : "", p:p};
  var r = {p:p, v:v, st:"ok", flags:[], cur:cur, mid:mid};
  if(v.min && A < v.min){ r.st = "min"; return r; }
  if(v.max && A > v.max) r.flags.push("max");
  var rx = fee(v.rx, A), A1 = A - rx[0], A1h = A - rx[1], rate = mid, fx, live = false;
  if(v.fx.k === "wise"){
    var w = WISE[cur], L = LIVEW[cur];
    if(L && Math.abs(L.A - A1) < 0.005){ fx = [L.fee, L.fee, true]; rate = L.rate; live = true; }
    else if(w){ var f = w.fixed + w.pct*A1/100; fx = [f, f, true]; rate = w.rate; }
    else fx = [0, 0, false];
  } else fx = fee(v.fx, A1);
  var A2lo = A1h - fx[1], A2hi = A1 - fx[0], wd = fee(v.wd, A2hi), A3lo = A2lo - wd[1], A3hi = A2hi - wd[0];
  r.rx = rx; r.fx = fx; r.wd = wd; r.rate = rate; r.live = live;
  r.netlo = A3lo*rate; r.nethi = A3hi*rate; r.complete = rx[2] && fx[2] && wd[2];
  r.range = rx[0] !== rx[1] || fx[0] !== fx[1] || wd[0] !== wd[1];
  r.costlo = A - r.nethi/mid; r.costhi = A - r.netlo/mid;
  if(A3lo <= 0) r.st = "min";
  return r;
}
function ranking(cc, A){
  var rs = P.providers.map(function(p){ return calc(p, cc, A); });
  var comp = rs.filter(function(r){ return r.st==="ok" && r.complete; }).sort(function(a,b){ return (b.netlo+b.nethi) - (a.netlo+a.nethi); });
  var inc = rs.filter(function(r){ return r.st==="ok" && !r.complete; }).sort(function(a,b){ return b.nethi - a.nethi; });
  return {comp:comp, inc:inc, min: rs.filter(function(r){ return r.st==="min"; }), na: rs.filter(function(r){ return r.st==="na"; })};
}

// ---- render del comparador ----
function srcLink(key){ var u = SRC[key] || ""; var host = u.replace(/^https?:\/\/(www\.)?/, "").split("/")[0];
  return '<a href="'+esc(u)+'" rel="nofollow noopener" target="_blank">'+esc(host)+' ↗</a>'; }
function compHtml(c, A, r, which){
  if(c.k === "unpublished") return '<span class="f unk" data-l="'+which+'">Margen no publicado</span>';
  if(c.k === "unknown") return '<span class="f unk" data-l="'+which+'">Sin verificar</span>';
  var inner;
  if(c.k === "wise") inner = usd(r.fx[0]) + '<small>Comisión Wise · tipo ' + nf(r.rate, 4) + (r.live ? " · en vivo" : "") + '</small>';
  else if(c.k === "range_pct") inner = nf(c.lo,1).replace(",0","") + "%–" + nf(c.hi,0) + "%<small>Rango publicado</small>";
  else if(c.k === "included") inner = "Incluido";
  else { var v = fee(c, A)[0]; inner = v === 0 ? "US$0" : usd(v); }
  return '<span class="f" data-l="'+which+'">'+inner+'</span>';
}
function rowHtml(r, i, A){
  var p = r.p, v = r.v, cur = r.cur, top = (i === 0 && r.complete) ? " top" : "";
  var st = r.complete ? (r.range ? '<span class="badge">Rango publicado</span>' : '<span class="badge acc">Costo verificado</span>') : '<span class="badge warn">Datos incompletos</span>';
  if(r.flags.indexOf("max") >= 0) st += '<span class="badge dn">'+esc(v.max_txt||"Supera el máximo publicado")+'</span>';
  var mid = (r.netlo + r.nethi)/2;
  var net = r.range ? '<b data-count="'+mid+'" data-cur="'+cur+'">'+money(mid,cur)+'</b><small>'+money(r.netlo,cur)+' – '+money(r.nethi,cur)+'</small>'
                    : '<b>'+(r.complete ? "" : "≤ ")+money(r.nethi,cur)+'</b>';
  net += '<small>≈ '+usd(r.nethi/r.mid)+' · costo '+(r.complete ? "" : "≥ ")+usd(Math.max(0, r.costlo))+'</small>';
  if(cur === "ARS" && AR.bolsa) net += '<small>≈ '+usd(mid/AR.bolsa.venta)+' al dólar MEP</small>';
  var srcs = [["rx","Recepción"],["fx","Cambio"],["wd","Retiro"]].map(function(x){ var c = v[x[0]];
    return '<li><b>'+x[1]+':</b> '+esc(c.txt)+' — '+srcLink(c.src)+' <span class="dim">('+fecha(c.date)+')</span></li>'; }).join("");
  var notes = (v.notes||[]).map(function(n){ return "<li>"+esc(n)+"</li>"; }).join("");
  return '<div class="rrow'+top+'" data-p="'+p.slug+'"><span class="rk">'+(r.complete ? i+1 : "–")+'</span>' +
    '<div class="pv"><span class="mono-badge">'+esc(p.mono)+'</span><div><a href="'+ROOT+'proveedores/'+p.slug+'/index.html">'+esc(p.name)+'</a><span class="route">'+esc(v.route)+'</span><div>'+st+'</div></div></div>' +
    compHtml(v.rx, A, r, "Recepción") + compHtml(v.fx, A, r, "Cambio") + compHtml(v.wd, A, r, "Retiro") +
    '<div class="net">'+net+'</div><details><summary>Fuentes y notas</summary><ul>'+srcs+notes+'</ul></details></div>';
}
function naRow(r, txt){ return '<div class="rrow na"><span class="rk">–</span><div class="pv"><span class="mono-badge">'+esc(r.p.mono)+'</span><div><b>'+esc(r.p.name)+'</b><span class="route">'+esc(txt)+'</span></div></div></div>'; }
function renderResults(el, cc, A){
  var R = ranking(cc, A), h = '<div class="rhead"><span>#</span><span>Proveedor</span><span>Recepción</span><span>Cambio</span><span>Retiro</span><span>Te llega</span></div>';
  h += '<div class="grp">Costo total publicado · ordenado por lo que te llega</div>' + R.comp.map(function(r,i){ return rowHtml(r, i, A); }).join("");
  if(R.inc.length) h += '<div class="grp">Datos incompletos · neto antes del margen o comisión que no publican</div>' + R.inc.map(function(r){ return rowHtml(r, -1, A); }).join("");
  if(R.min.length) h += '<div class="grp">Monto mínimo no alcanzado</div>' + R.min.map(function(r){ return naRow(r, "Monto mínimo no alcanzado" + (r.v && r.v.min_txt ? " · " + r.v.min_txt : "")); }).join("");
  if(R.na.length) h += '<div class="grp">No disponible en '+esc(C[cc].name)+'</div>' + R.na.map(function(r){ return naRow(r, r.why); }).join("");
  el.innerHTML = h;
  return R;
}

// ---- estado + URL compartible ----
var compEl = $("[data-comp]"), amtEl = $("[data-amount]"), errEl = $("[data-err]"), ppyEl = $("[data-ppy]");
var qs = new URLSearchParams(location.search);
var CODE = {mx:"mx", co:"co", pe:"pe", cl:"cl", ar:"ar"};
var state = {cc: compEl ? compEl.dataset.country : "mx", A: 1000, ppy: 12};
if(qs.get("pais") && CODE[qs.get("pais").toLowerCase()]) state.cc = qs.get("pais").toLowerCase();
if(qs.get("monto")){ var qa = parseAmount(qs.get("monto")); if(qa > 0) state.A = qa; }
if(qs.get("pagos") && +qs.get("pagos") > 0) state.ppy = Math.min(365, Math.round(+qs.get("pagos")));
function syncURL(){
  var u = new URL(location.href); u.searchParams.set("monto", String(Math.round(state.A*100)/100)); u.searchParams.set("pais", state.cc);
  if(state.ppy !== 12) u.searchParams.set("pagos", state.ppy); else u.searchParams.delete("pagos");
  history.replaceState(null, "", u.pathname + u.search + u.hash);
}
function shareURL(){ var u = new URL(location.href); u.hash = "ahorrometro"; return u.toString(); }

var lastR = null;
function update(){
  if(!compEl) return;
  var res = $("[data-results]", compEl);
  lastR = renderResults(res, state.cc, state.A);
  $$("[data-cname]").forEach(function(n){ n.textContent = C[state.cc].name; });
  $$(".seg button[data-c]").forEach(function(b){ b.setAttribute("aria-pressed", b.dataset.c === state.cc ? "true" : "false"); });
  $$("[data-quick]").forEach(function(b){ b.setAttribute("aria-pressed", Math.abs(parseAmount(b.dataset.quick) - state.A) < 0.001 ? "true" : "false"); });
  renderAhorro(); syncURL(); scheduleWise();
}
if(compEl){
  if(amtEl){
    amtEl.value = String(state.A % 1 ? state.A.toFixed(2) : state.A);
    amtEl.addEventListener("input", function(){
      var v = parseAmount(amtEl.value);
      if(!(v > 0)){ errEl.textContent = amtEl.value.trim() ? "Escribe un monto válido, por ejemplo 375,20 o 1500." : "Escribe un monto en dólares."; return; }
      if(v > 1000000){ errEl.textContent = "Monto demasiado alto para este comparador (máx. US$1.000.000)."; return; }
      errEl.textContent = ""; state.A = v; update();
    });
  }
  $$("[data-quick]").forEach(function(b){ b.addEventListener("click", function(){ state.A = parseAmount(b.dataset.quick); if(amtEl) amtEl.value = b.dataset.quick.replace(".", ","); errEl.textContent = ""; update(); }); });
  $$(".seg button[data-c]").forEach(function(b){ b.addEventListener("click", function(){ state.cc = b.dataset.c; update(); }); });
  if(ppyEl){ ppyEl.value = String(state.ppy); if(ppyEl.value !== String(state.ppy)){ var o = document.createElement("option"); o.value = o.textContent = state.ppy; ppyEl.appendChild(o); ppyEl.value = String(state.ppy); }
    ppyEl.addEventListener("change", function(){ state.ppy = +ppyEl.value; renderAhorro(); syncURL(); }); }
}

// ---- animación de números (countUp.js + Intl) ----
function animateTo(el, value, fmtFn){
  if(REDUCED || !window.countUp){ el.textContent = fmtFn(value); return; }
  var from = el._v || 0; el._v = value;
  var cu = new countUp.CountUp(el, value, {startVal: from, duration: 1.1, decimalPlaces: 2, formattingFn: fmtFn});
  if(!cu.error) cu.start(); else el.textContent = fmtFn(value);
}

// ---- Ahorrómetro ----
function renderAhorro(){
  var box = $("[data-ahorro]"); if(!box || !lastR) return;
  var comp = lastR.comp, cur = C[state.cc].cur, big = $("[data-ah-big]", box), sub = $("[data-ah-sub]", box), vs = $("[data-ah-vs]", box);
  var unverified = lastR.inc.length;
  if(comp.length < 2){ big.textContent = "—"; sub.textContent = "Necesitamos al menos dos proveedores con costo publicado para este país y monto.";
    vs.innerHTML = '<p class="small dim">'+unverified+' proveedor(es) no publican su margen cambiario, así que no entran en el cálculo.</p>'; return; }
  // opción más cara (usamos su costo mínimo) vs más barata (usamos su costo máximo): no exagera la diferencia
  var exp = comp.reduce(function(a,b){ return b.costlo > a.costlo ? b : a; });
  var chp = comp.reduce(function(a,b){ return b.costhi < a.costhi ? b : a; });
  var per = Math.max(0, exp.costlo - chp.costhi); var year = per * state.ppy;
  animateTo(big, year, function(v){ return "US$" + nf(v, 2); });
  sub.textContent = "al año · " + money(year * MID[cur], cur) + " · " + state.ppy + " pagos de " + usd(state.A);
  vs.innerHTML = '<div>Más cara con costo publicado: <b>'+esc(exp.p.name)+'</b> · costo desde '+usd(exp.costlo)+' por pago</div>' +
    '<div>Más barata con costo publicado: <b>'+esc(chp.p.name)+'</b> · costo hasta '+usd(chp.costhi)+' por pago</div>' +
    '<div>Diferencia por pago: <b>'+usd(per)+'</b> ('+nf(per/state.A*100, 2)+'% del monto)</div>' +
    (per <= 0 ? '<div class="small">Los costos publicados se superponen (por ejemplo, un margen publicado como rango): con datos verificados no se puede afirmar una diferencia mínima a este monto.</div>' : "") +
    (unverified ? '<div class="xs dim">'+unverified+' proveedor(es) con margen no publicado o comisiones sin verificar quedan fuera.</div>' : "");
  box._share = "Si cobro " + usd(state.A) + " " + state.ppy + " veces al año en " + C[state.cc].name + ", entre la opción más cara y la más barata con costo publicado se van " + usd(year) + " al año (" + exp.p.name + " vs " + chp.p.name + ", datos de CobraEnDólares).";
}
var shareBtn = $("[data-share]");
if(shareBtn) shareBtn.addEventListener("click", function(){
  var box = $("[data-ahorro]"), txt = (box && box._share) || "", url = shareURL(), msg = $("[data-share-msg]");
  if(navigator.share){ navigator.share({title:"CobraEnDólares · Ahorrómetro", text: txt, url: url}).catch(function(){}); return; }
  var full = txt + " " + url;
  (navigator.clipboard ? navigator.clipboard.writeText(full) : Promise.reject()).then(function(){ msg.textContent = "Copiado al portapapeles."; }, function(){ prompt("Copia este texto:", full); });
});

// ---- Wise: cotización en vivo para el monto exacto (API pública, CORS) ----
var wiseT = null;
function scheduleWise(){
  if(!compEl) return; clearTimeout(wiseT);
  wiseT = setTimeout(function(){
    var cur = C[state.cc].cur, A = state.A;
    if(A < 1 || (LIVEW[cur] && Math.abs(LIVEW[cur].A - A) < 0.005)) return;
    fetch("https://api.wise.com/v4/comparisons/?sourceCurrency=USD&targetCurrency="+cur+"&sendAmount="+A.toFixed(2)).then(function(r){ return r.json(); }).then(function(d){
      var w = (d.providers||[]).filter(function(p){ return p.alias === "wise"; })[0]; var q = w && w.quotes && w.quotes[0];
      if(q && isFinite(q.fee) && isFinite(q.rate)){ LIVEW[cur] = {A: A, fee: q.fee, rate: q.rate}; if(Math.abs(state.A - A) < 0.005 && C[state.cc].cur === cur){ lastR = renderResults($("[data-results]", compEl), state.cc, state.A); renderAhorro(); } }
    }).catch(function(){});
  }, 650);
}

// ---- datos en vivo: currency-api (tipo medio) + DolarAPI ----
function setStatus(ok, txt){ $$("[data-status]").forEach(function(s){ s.classList.toggle("live", ok); s.classList.toggle("snap", !ok); var t = $("[data-status-txt]", s); if(t) t.textContent = txt; }); }
function fetchJSON(urls){ var i = 0; return new Promise(function(res, rej){ (function next(){ if(i >= urls.length) return rej(); fetch(urls[i++]).then(function(r){ if(!r.ok) throw 0; return r.json(); }).then(res, next); })(); }); }
var H = D.hist;
function live(){
  var p1 = fetchJSON(["https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.min.json", "https://latest.currency-api.pages.dev/v1/currencies/usd.min.json"]).then(function(d){
    ["MXN","COP","PEN","CLP","ARS"].forEach(function(c){ var v = d.usd[c.toLowerCase()]; if(v) MID[c] = v; }); MIDDATE = d.date; return true; }).catch(function(){ return false; });
  var p2 = fetch("https://dolarapi.com/v1/dolares").then(function(r){ return r.json(); }).then(function(a){ a.forEach(function(x){ AR[x.casa] = {casa:x.casa, nombre:x.nombre, compra:x.compra, venta:x.venta, t:x.fechaActualizacion}; }); return true; }).catch(function(){ return false; });
  Promise.all([p1, p2]).then(function(ok){
    var t = new Date();
    setStatus(ok[0], ok[0] ? "En vivo · tipo medio del " + fecha(MIDDATE) : "Datos guardados · " + fecha(MIDDATE));
    paintMarket(ok[0] || ok[1]); paintAR(); renderThermo(); if(compEl){ lastR = renderResults($("[data-results]", compEl), state.cc, state.A); renderAhorro(); }
  });
}

// ---- panel de mercado (terminal) ----
function chgHtml(p){ var cls = Math.abs(p) < 0.005 ? "flat" : (p > 0 ? "up" : "dn"); var ar = cls === "flat" ? "→" : (p > 0 ? "▲" : "▼"); return '<span class="chg '+cls+'">'+ar+' '+nf(Math.abs(p),2)+'%</span>'; }
function prevMid(c){ var s = H.mid.rates[c], d = H.mid.dates; if(MIDDATE > d[d.length-1]) return s[s.length-1]; return s[s.length-2]; }
function paintMarket(flash){
  $$("[data-mk]").forEach(function(tr){
    var k = tr.dataset.mk, v, prev;
    if(k.indexOf("mid-") === 0){ var c = k.slice(4); v = MID[c]; prev = prevMid(c); }
    else { var casa = k.slice(3), h = H.ar[casa]; if(!AR[casa] || !h) return; v = AR[casa].venta; var last = h.dates[h.dates.length-1];
      prev = (AR[casa].t && AR[casa].t.slice(0,10) > last) ? h.venta[h.venta.length-1] : h.venta[h.venta.length-2]; }
    var cell = $("[data-v]", tr), old = cell.textContent; cell.textContent = nf(v, 2); $("[data-c]", tr).innerHTML = chgHtml((v/prev - 1)*100);
    if(flash && old !== cell.textContent && !REDUCED){ tr.classList.remove("flash"); void tr.offsetWidth; tr.classList.add("flash"); }
  });
  var t = $("[data-mk-time]");
  if(t){ var hm = new Intl.DateTimeFormat("es-419",{hour:"2-digit",minute:"2-digit"}).format(new Date());
    t.textContent = "Consultado " + hm + " (tu hora) · tipo medio " + fecha(MIDDATE) + (AR.blue && AR.blue.t ? " · DolarAPI " + new Intl.DateTimeFormat("es-419",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(AR.blue.t)) : ""); }
}
function paintAR(){
  $$("[data-ar]").forEach(function(c){ var x = AR[c.dataset.ar]; if(!x) return; $("[data-ar-v]", c).textContent = nf(x.venta, 2); $("[data-ar-c]", c).textContent = nf(x.compra, 2); });
  var g = $("[data-ar-gap]"); if(g && AR.blue && AR.oficial) g.textContent = nf((AR.blue.venta/AR.oficial.venta - 1)*100, 1) + "%";
}

// ---- Termómetro del dólar ----
function sparkSVG(vals, w, h){
  if(!vals || vals.length < 2) return ""; var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), rg = (hi - lo) || 1;
  var pts = vals.map(function(v, i){ return (i*(w/(vals.length-1))).toFixed(1) + "," + (h - 2 - (v - lo)/rg*(h - 4)).toFixed(1); }).join(" ");
  var avg = vals.reduce(function(a,b){ return a+b; }, 0)/vals.length, ay = (h - 2 - (avg - lo)/rg*(h - 4)).toFixed(1);
  return '<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" aria-hidden="true"><line x1="0" x2="'+w+'" y1="'+ay+'" y2="'+ay+'" stroke="var(--line2)" stroke-dasharray="3 3"/><polyline fill="none" stroke="var(--acc)" stroke-width="1.6" points="'+pts+'"/></svg>';
}
function gauge(pct){
  var cl = Math.max(-5, Math.min(5, pct)), ang = Math.PI * (1 - (cl + 5)/10), cx = 60, cy = 58, r = 46;
  var x = cx + r*Math.cos(ang), y = cy - r*Math.sin(ang);
  return '<svg class="gauge" viewBox="0 0 120 68" role="img" aria-label="'+nf(pct,2)+'% frente al promedio de 30 días">' +
    '<defs><linearGradient id="gg" x1="0" x2="1"><stop offset="0" stop-color="#8ab4ff"/><stop offset=".5" stop-color="#3a4150"/><stop offset="1" stop-color="#34e0a1"/></linearGradient></defs>' +
    '<path d="M14 58 A46 46 0 0 1 106 58" fill="none" stroke="url(#gg)" stroke-width="9" stroke-linecap="round"/>' +
    '<line x1="'+cx+'" y1="'+cy+'" x2="'+x.toFixed(1)+'" y2="'+y.toFixed(1)+'" stroke="var(--t1)" stroke-width="2.5" stroke-linecap="round"/><circle cx="'+cx+'" cy="'+cy+'" r="4" fill="var(--t1)"/>' +
    '<text x="12" y="67" font-size="8" fill="var(--t3)" font-family="monospace">−5%</text><text x="96" y="67" font-size="8" fill="var(--t3)" font-family="monospace">+5%</text></svg>';
}
function thermoItems(){
  var out = [], names = {MXN:["mx","México"], COP:["co","Colombia"], PEN:["pe","Perú"], CLP:["cl","Chile"], ARS:["ar","Argentina · oficial (ref.)"]};
  Object.keys(names).forEach(function(c){ var s = H.mid.rates[c].slice(); s[s.length-1] = MID[c] || s[s.length-1]; out.push({cc:names[c][0], label:names[c][1], pair:"USD/"+c, s:s}); });
  [["blue","Argentina · blue"],["bolsa","Argentina · MEP"]].forEach(function(x){ var h = H.ar[x[0]]; if(!h) return; var s = h.venta.slice(); if(AR[x[0]]) s[s.length-1] = AR[x[0]].venta; out.push({cc:"ar", label:x[1], pair:"USD/ARS", s:s}); });
  return out;
}
function renderThermo(){
  $$("[data-thermo]").forEach(function(box){
    var only = box.dataset.only;
    box.innerHTML = thermoItems().filter(function(it){ return !only || it.cc === only || (only !== "ar" && false); }).map(function(it, i){
      var avg = it.s.reduce(function(a,b){ return a+b; }, 0)/it.s.length, now = it.s[it.s.length-1], pct = (now/avg - 1)*100;
      var word = Math.abs(pct) < 0.05 ? "prácticamente igual a" : (pct > 0 ? "por encima de" : "por debajo de");
      return '<div class="tcard reveal" style="--d:'+i+'"><div class="hd"><span>'+esc(it.label)+'</span><span>'+it.pair+'</span></div>' +
        '<div class="val">'+nf(now, 2)+'</div>'+gauge(pct)+
        '<div class="msg">Hoy el dólar está <b class="'+(pct>0?"up":"dn")+'">'+nf(Math.abs(pct),2)+'%</b> '+word+' su promedio de 30 días ('+nf(avg,2)+').</div>' +
        '<div class="sp">'+sparkSVG(it.s, 200, 34)+'</div></div>';
    }).join("");
  });
}

// ---- gráfico 30 días (uPlot) ----
var chartEl = $("[data-chart]"), plot = null;
function ts(d){ return Date.parse(d + "T12:00:00Z")/1000; }
function chartData(cur){
  if(cur !== "ARS"){ return {x: H.mid.dates.map(ts), series: [{label:"USD/"+cur+" (medio)", data: H.mid.rates[cur], stroke:"#34e0a1"}]}; }
  var dates = H.mid.dates, mp = {}; dates.forEach(function(d, i){ mp[d] = i; });
  var pick = function(h){ var arr = dates.map(function(){ return null; }); if(!h) return arr; h.dates.forEach(function(d, i){ if(mp[d] !== undefined) arr[mp[d]] = h.venta[i]; }); return arr; };
  return {x: dates.map(ts), series: [{label:"Oficial (venta)", data: pick(H.ar.oficial), stroke:"#8ab4ff"}, {label:"MEP (venta)", data: pick(H.ar.bolsa), stroke:"#f5c451"}, {label:"Blue (venta)", data: pick(H.ar.blue), stroke:"#34e0a1"}]};
}
function drawChart(cur){
  if(!chartEl || !window.uPlot) return;
  var cd = chartData(cur), w = chartEl.clientWidth || 800, h = window.innerWidth < 760 ? 240 : 320;
  var opts = {width: w, height: h, cursor: {drag: {x: false, y: false}}, legend: {show: true},
    scales: {x: {time: true}}, axes: [
      {stroke: "#8790a2", grid: {stroke: "rgba(255,255,255,.05)"}, ticks: {stroke: "rgba(255,255,255,.08)"}, font: "11px JetBrains Mono, monospace"},
      {stroke: "#8790a2", grid: {stroke: "rgba(255,255,255,.05)"}, ticks: {stroke: "rgba(255,255,255,.08)"}, font: "11px JetBrains Mono, monospace", size: 70,
       values: function(u, v){ return v.map(function(x){ return nf(x, x >= 100 ? 0 : 2); }); }}],
    series: [{value: function(u, v){ return v == null ? "" : new Intl.DateTimeFormat("es-419",{day:"numeric",month:"short"}).format(new Date(v*1000)); }}].concat(cd.series.map(function(s){
      return {label: s.label, stroke: s.stroke, width: 2, spanGaps: true, points: {show: false}, fill: cd.series.length === 1 ? "rgba(52,224,161,.08)" : undefined,
              value: function(u, v){ return v == null ? "—" : nf(v, v >= 100 ? 2 : 4); }}; }))};
  if(plot) plot.destroy();
  chartEl.innerHTML = ""; plot = new uPlot(opts, [cd.x].concat(cd.series.map(function(s){ return s.data; })), chartEl);
}
var tabs = $("[data-ch-tabs]"), curTab = tabs ? tabs.dataset.sel : "MXN";
if(tabs){ $$(".tab", tabs).forEach(function(b){ b.addEventListener("click", function(){ $$(".tab", tabs).forEach(function(x){ x.setAttribute("aria-selected", x === b ? "true" : "false"); }); curTab = b.dataset.cur; drawChart(curTab); }); }); }
var rzT; window.addEventListener("resize", function(){ clearTimeout(rzT); rzT = setTimeout(function(){ drawChart(curTab); }, 200); });

// ---- filtros de noticias ----
$$("[data-news-filter]").forEach(function(f){
  var list = f.nextElementSibling, sel = {cat: "", country: ""};
  $$("[data-f]", f).forEach(function(g){ $$("button", g).forEach(function(b){ b.addEventListener("click", function(){
    sel[g.dataset.f] = b.dataset.v; $$("button", g).forEach(function(x){ x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    $$("li", list).forEach(function(li){ li.hidden = (sel.cat && li.dataset.cat !== sel.cat) || (sel.country && li.dataset.country !== sel.country); });
  }); }); });
});

// ---- formularios en modo demo, menú, CTA fijo ----
$$("form[data-placeholder]").forEach(function(f){ f.addEventListener("submit", function(e){ e.preventDefault(); if(f.dataset.thanks){ location.href = f.dataset.thanks + "?demo=1"; return; } var m = $(".form-msg", f); if(m) m.textContent = "Gracias. (Versión de prueba: no se guardó nada.)"; }); });
var mb = $(".menu-btn"), nav = $("nav.main"); if(mb && nav) mb.addEventListener("click", function(){ var o = nav.classList.toggle("open"); mb.setAttribute("aria-expanded", o); });
var sc = $(".sticky-cta");
if(sc && !sessionStorage.getItem("ced-cta-cerrado")){
  var trig = $("[data-cta-trigger]"); var chk = function(){ sc.classList.toggle("show", trig ? trig.getBoundingClientRect().bottom < 0 : scrollY > 600); };
  addEventListener("scroll", chk, {passive: true}); chk();
  $(".x", sc).addEventListener("click", function(){ sc.classList.remove("show"); sessionStorage.setItem("ced-cta-cerrado", "1"); removeEventListener("scroll", chk); });
}

// ---- arranque ----
update(); renderThermo(); paintMarket(false);
if(document.readyState === "complete") drawChart(curTab); else addEventListener("load", function(){ drawChart(curTab); });
live();
})();
