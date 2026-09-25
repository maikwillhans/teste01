"use strict";
/* Sistema Vendas x Metas — interface web. Consome a API em /api. */

/* ============================================================ utilidades */
const $ = id => document.getElementById(id);
const nf = c => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
const FMT = [nf(0), nf(1), nf(2), nf(3)];
const num = (v, c = 0) => v == null || !isFinite(v) ? "–" : FMT[c].format(v);
const brl = (v, c = 0) => v == null || !isFinite(v) ? "–" : "R$ " + num(v, c);
const brlC = v => v == null || !isFinite(v) ? "–" : Math.abs(v) >= 1e6 ? "R$ " + num(v / 1e6, 2) + " mi" : Math.abs(v) >= 1e4 ? "R$ " + num(v / 1e3, 1) + " mil" : brl(v);
const ton = kg => kg == null || !isFinite(kg) ? "–" : num(kg / 1000, 1) + " t";
const pct = (v, c = 1) => v == null || !isFinite(v) ? "–" : num(v * 100, c) + "%";
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const perLabel = p => p ? p.slice(5) + "/" + p.slice(0, 4) : "–";
const ddmm = iso => iso.slice(8, 10) + "/" + iso.slice(5, 7);
const dataBR = iso => iso ? iso.slice(0, 10).split("-").reverse().join("/") : "–";
const div = (a, b) => b ? a / b : null;
const qs = o => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== "" && v != null)).toString();

async function api(metodo, url, corpo) {
  const op = { method: metodo, headers: {} };
  if (corpo instanceof FormData) op.body = corpo;
  else if (corpo !== undefined) { op.headers["Content-Type"] = "application/json"; op.body = JSON.stringify(corpo); }
  const r = await fetch(url, op);
  const txt = await r.text();
  let dados = null; try { dados = txt ? JSON.parse(txt) : null; } catch (_) { dados = txt; }
  if (!r.ok) throw new Error(dados?.erro || dados?.detail || `Erro ${r.status}`);
  return dados;
}

function toast(msg, erro = false) {
  const t = document.createElement("div"); t.className = "toast" + (erro ? " err" : ""); t.textContent = msg;
  $("toasts").appendChild(t); setTimeout(() => t.remove(), erro ? 6000 : 3200);
}

function confirmar(titulo, texto, rotulo = "Confirmar", perigo = true) {
  return new Promise(ok => {
    const bg = document.createElement("div"); bg.className = "modal-bg";
    bg.innerHTML = `<div class="modal" role="dialog" aria-modal="true"><h3>${esc(titulo)}</h3><p>${esc(texto)}</p>
      <div class="acts"><button class="btn ghost" data-r="0">Cancelar</button><button class="btn ${perigo ? "danger" : ""}" data-r="1">${esc(rotulo)}</button></div></div>`;
    bg.onclick = e => { const r = e.target.dataset?.r; if (r != null || e.target === bg) { bg.remove(); ok(r === "1"); } };
    document.body.appendChild(bg); bg.querySelector('[data-r="1"]').focus();
  });
}

/* gaveta lateral para formulários */
function gaveta({ titulo, sub = "", corpo, salvar, excluir, rotuloSalvar = "Salvar" }) {
  const bg = document.createElement("div"); bg.className = "drawer-bg";
  const d = document.createElement("section"); d.className = "drawer"; d.setAttribute("role", "dialog");
  d.innerHTML = `<header><div style="flex:1"><h2>${esc(titulo)}</h2>${sub ? `<p>${esc(sub)}</p>` : ""}</div><button class="x" aria-label="Fechar">×</button></header>
    <div class="body"><div class="errbox" hidden></div>${corpo}</div>
    <footer>${excluir ? `<button class="btn ghost" data-a="excluir" style="color:var(--crit-ink)">Excluir</button>` : ""}<span class="grow"></span>
      <button class="btn ghost" data-a="fechar">Cancelar</button>${salvar ? `<button class="btn" data-a="salvar">${esc(rotuloSalvar)}</button>` : ""}</footer>`;
  const fechar = () => { bg.remove(); d.remove(); document.removeEventListener("keydown", esc_); };
  const esc_ = e => { if (e.key === "Escape") fechar(); };
  document.addEventListener("keydown", esc_);
  bg.onclick = fechar; d.querySelector(".x").onclick = fechar; d.querySelector('[data-a="fechar"]').onclick = fechar;
  const erro = m => { const b = d.querySelector(".errbox"); b.hidden = !m; b.textContent = m || ""; if (m) b.scrollIntoView({ block: "nearest" }); };
  const botao = d.querySelector('[data-a="salvar"]');
  if (salvar) botao.onclick = async () => {
    botao.disabled = true; erro("");
    try { await salvar(d); fechar(); } catch (e) { erro(e.message); } finally { botao.disabled = false; }
  };
  if (excluir) d.querySelector('[data-a="excluir"]').onclick = async () => {
    try { if (await excluir(d)) fechar(); } catch (e) { erro(e.message); }
  };
  document.body.append(bg, d);
  setTimeout(() => d.querySelector(".body input:not([readonly]), .body select")?.focus(), 30);
  return d;
}

/* ============================================================ estado */
const S = { inicio: null, periodo: null, gerente: "", supervisor: "", vendedor: "", pagina: "geral", opcoes: {} };
const PAGINAS = {
  geral: ["Visão geral", "Resultado do mês contra a meta", "equipe"],
  "analise-metas": ["Metas", "Meta, vendido e carteira por equipe, categoria e produto", "equipe"],
  "analise-vendas": ["Vendas", "Faturamento líquido por cliente, produto, região e mais", "equipe"],
  notas: ["Notas de venda", "Lance, altere ou consulte as notas (cabeçalho + itens)", "periodo"],
  metas: ["Metas do mês", "Lance e ajuste as metas por região, vendedor e produto", "periodo"],
  importar: ["Importar planilhas", "Atualize a base com os relatórios exportados do Sankhya", ""],
  cargas: ["Histórico e exportação", "Importações feitas, desfazer uma carga e exportar dados", "periodo"],
  validacao: ["Validação", "Conferência da base contra as planilhas importadas", "periodo"],
};
const ICONE_CAD = {
  vendedores: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
  clientes: '<path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-6h6v6"/>',
  produtos: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
  regioes: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  tops: '<path d="M4 7h16M4 12h10M4 17h7"/>',
  empresas: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/>',
};

/* cache de opções dos cadastros (para os campos de seleção) */
const CACHE = {};
async function opcoesCad(nome, recarregar = false) {
  if (!CACHE[nome] || recarregar) CACHE[nome] = await api("GET", `/api/cadastros/${nome}/opcoes`);
  return CACHE[nome];
}
const nomeDe = (nome, cod) => CACHE[nome]?.find(o => o.codigo === cod)?.nome;

/* ============================================================ gráficos (mesmos do painel) */
const tip = $("tip");
function showTip(html, ev) {
  tip.innerHTML = html; tip.hidden = false;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
}
const hideTip = () => { tip.hidden = true; };
function bindTips(root) {
  root.querySelectorAll("[data-tip]").forEach(el => { el.addEventListener("mousemove", e => showTip(el.dataset.tip, e)); el.addEventListener("mouseleave", hideTip); });
}
function niceTicks(max, n = 4) {
  if (!(max > 0)) return [0, 1];
  const raw = max / n, p = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(s => s * p).find(s => s >= raw);
  const t = []; for (let v = 0; v <= max + step * 0.001; v += step) t.push(v);
  if (t.at(-1) < max) t.push(t.at(-1) + step);
  return t;
}
const eixo = v => Math.abs(v) >= 1e6 ? num(v / 1e6, v % 1e6 ? 1 : 0) + " mi" : Math.abs(v) >= 1e3 ? num(v / 1e3, 0) + " mil" : num(v);

function svgBarras(d) {
  if (!d.length) return `<div class="empty">Sem vendas no período.</div>`;
  const W = 640, H = 250, pl = 52, pr = 8, pt = 10, pb = 26;
  const ticks = niceTicks(Math.max(...d.map(x => x.faturado), 0)), ymax = ticks.at(-1), iw = W - pl - pr, ih = H - pt - pb;
  const bw = iw / d.length, gap = Math.min(4, bw * 0.3), y = v => pt + ih - (Math.max(v, 0) / ymax) * ih, every = Math.ceil(d.length / 8);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Faturamento por dia">`;
  for (const t of ticks) s += `<line x1="${pl}" x2="${W - pr}" y1="${y(t)}" y2="${y(t)}" stroke="var(--grid)"/><text x="${pl - 6}" y="${y(t) + 4}" text-anchor="end">${eixo(t)}</text>`;
  d.forEach((p, i) => {
    const x = pl + i * bw + gap / 2, w = Math.max(bw - gap, 1), yy = y(p.faturado), h = pt + ih - yy, r = Math.min(4, w / 2, h);
    const path = h > 0 ? `M${x},${pt + ih} V${yy + r} Q${x},${yy} ${x + r},${yy} H${x + w - r} Q${x + w},${yy} ${x + w},${yy + r} V${pt + ih} Z` : "";
    s += `<g data-tip="<b>${ddmm(p.data)}</b><br>${brl(p.faturado, 2)}<br><span class=k>${num(p.kg)} kg</span>"><rect x="${pl + i * bw}" y="${pt}" width="${bw}" height="${ih}" fill="transparent"/>${path ? `<path d="${path}" fill="var(--accent)"/>` : ""}</g>`;
    if (i % every === 0) s += `<text x="${x + w / 2}" y="${H - 8}" text-anchor="middle">${ddmm(p.data)}</text>`;
  });
  return s + `<line x1="${pl}" x2="${W - pr}" y1="${pt + ih}" y2="${pt + ih}" stroke="var(--axis)"/></svg>`;
}
function svgAcumulado(d, meta) {
  if (!d.length) return `<div class="empty">Sem vendas no período.</div>`;
  const W = 640, H = 250, pl = 52, pr = 12, pt = 18, pb = 26;
  let acc = 0; const pts = d.map(p => ({ data: p.data, v: (acc += p.faturado) }));
  const ticks = niceTicks(Math.max(acc, meta || 0)), ymax = ticks.at(-1), iw = W - pl - pr, ih = H - pt - pb;
  const x = i => pl + (pts.length === 1 ? iw / 2 : (i / (pts.length - 1)) * iw), y = v => pt + ih - (v / ymax) * ih, every = Math.ceil(pts.length / 8);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Faturamento acumulado contra a meta">`;
  for (const t of ticks) s += `<line x1="${pl}" x2="${W - pr}" y1="${y(t)}" y2="${y(t)}" stroke="var(--grid)"/><text x="${pl - 6}" y="${y(t) + 4}" text-anchor="end">${eixo(t)}</text>`;
  if (meta) s += `<line x1="${pl}" x2="${W - pr}" y1="${y(meta)}" y2="${y(meta)}" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="6 4"/><text x="${W - pr}" y="${y(meta) - 6}" text-anchor="end" style="fill:var(--ink-2)">Meta ${brlC(meta)}</text>`;
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.v)}`).join(" ");
  s += `<path d="${line} L${x(pts.length - 1)},${pt + ih} L${x(0)},${pt + ih} Z" fill="var(--accent)" opacity=".08"/><path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round"/>`;
  pts.forEach((p, i) => {
    s += `<g data-tip="<b>${ddmm(p.data)}</b><br>Acumulado: ${brl(p.v)}${meta ? `<br><span class=k>${pct(p.v / meta)} da meta</span>` : ""}"><rect x="${x(i) - iw / pts.length / 2}" y="${pt}" width="${iw / pts.length}" height="${ih}" fill="transparent"/><circle cx="${x(i)}" cy="${y(p.v)}" r="${i === pts.length - 1 ? 5 : 3.5}" fill="var(--accent)" stroke="var(--surface)" stroke-width="2"/></g>`;
    if (i % every === 0) s += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${ddmm(p.data)}</text>`;
  });
  s += `<text x="${x(pts.length - 1) - 8}" y="${y(acc) - 10}" text-anchor="end" style="fill:var(--ink);font-weight:600">${brlC(acc)}</text>`;
  return s + `<line x1="${pl}" x2="${W - pr}" y1="${pt + ih}" y2="${pt + ih}" stroke="var(--axis)"/></svg>`;
}
function bullet(rows, limite = 40) {
  rows = rows.filter(r => r.meta_kg > 0).slice(0, limite).sort((a, b) => (b.perc_meta ?? 0) - (a.perc_meta ?? 0));
  if (!rows.length) return `<div class="empty">Sem metas no período.</div>`;
  const max = Math.max(...rows.map(r => Math.max(r.meta_kg, r.vendido_kg + Math.max(r.carteira_kg, 0)))), p = v => Math.max(0, (v / max) * 100);
  return `<div class="legend"><span><i class="sw" style="background:var(--accent)"></i>Vendido</span><span><i class="sw" style="background:var(--accent-soft)"></i>Carteira</span><span><i class="sw tick"></i>Meta</span><span style="margin-left:auto;color:var(--muted)">% vendido ÷ meta, em kg</span></div>
  <div class="hbars">${rows.map(r => `<div class="hrow" data-tip="<b>${esc(r.grupo)}</b><br>Meta: ${num(r.meta_kg)} kg<br>Vendido: ${num(r.vendido_kg)} kg (${pct(r.perc_meta)})<br>Carteira: ${num(r.carteira_kg)} kg<br><span class=k>Com carteira: ${pct(r.perc_prev)}</span><br>Faturado: ${brl(r.vendido_valor)} de ${brl(r.meta_valor)}">
    <span class="lab" title="${esc(r.grupo)}">${esc(r.grupo)}</span>
    <span class="track"><span class="b c" style="width:${p(r.vendido_kg + Math.max(r.carteira_kg, 0))}%"></span><span class="b v" style="width:${p(r.vendido_kg)}%"></span><span class="t" style="left:${p(r.meta_kg)}%"></span></span>
    <span class="val">${pct(r.perc_meta, 0)}</span></div>`).join("")}</div>`;
}
function ranking(rows, n = 10) {
  rows = rows.slice(0, n);
  if (!rows.length) return `<div class="empty">Sem vendas no período.</div>`;
  const max = Math.max(...rows.map(r => r.faturado), 1);
  return `<div class="hbars">${rows.map(r => `<div class="hrow" data-tip="<b>${esc(r.grupo)}</b><br>${brl(r.faturado, 2)}<br>${num(r.kg)} kg · ${num(r.clientes)} clientes<br><span class=k>Preço médio ${brl(r.preco_medio, 2)}/kg</span>">
    <span class="lab" title="${esc(r.grupo)}">${esc(r.grupo ?? "(vazio)")}</span><span class="track"><span class="b v" style="width:${Math.max(0, r.faturado / max * 100)}%"></span></span>
    <span class="val">${brlC(r.faturado).replace("R$ ", "")}</span></div>`).join("")}</div>`;
}
function tabela(el, colunas, linhas, ordem, onClick) {
  let sortKey = ordem?.[0] ?? null, dir = ordem?.[1] ?? -1;
  const draw = () => {
    const rows = sortKey == null ? linhas : [...linhas].sort((a, b) => {
      const x = a[sortKey], y = b[sortKey]; if (x == null) return 1; if (y == null) return -1;
      return (typeof x === "number" ? x - y : String(x).localeCompare(String(y), "pt-BR")) * dir;
    });
    el.innerHTML = `<table><thead><tr>${colunas.map(c => `<th class="${c.n ? "n" : ""}" data-k="${c.k}" aria-sort="${c.k === sortKey ? (dir > 0 ? "ascending" : "descending") : "none"}">${c.t}</th>`).join("")}</tr></thead>
      <tbody>${rows.length ? rows.map((r, i) => `<tr data-i="${linhas.indexOf(r)}" class="${onClick ? "click" : ""}">${colunas.map(c => `<td class="${c.n ? "n" : ""}">${c.f ? c.f(r[c.k], r) : esc(r[c.k])}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${colunas.length}" class="empty">Nada para mostrar.</td></tr>`}</tbody></table>`;
    el.querySelectorAll("th").forEach(th => th.onclick = () => { const k = th.dataset.k; dir = k === sortKey ? -dir : -1; sortKey = k; draw(); });
    if (onClick) el.querySelectorAll("tbody tr[data-i]").forEach(tr => tr.onclick = () => onClick(linhas[+tr.dataset.i]));
  };
  draw();
}
const kpi = (l, v, d = "", cls = "", extra = "") => `<div class="kpi ${cls}"><span class="l">${l}</span><span class="v num">${v}</span>${extra}${d ? `<span class="d">${d}</span>` : ""}</div>`;
const STATUS = { good: ["✔", "Atingiu"], warn: ["▲", "No ritmo"], crit: ["✖", "Abaixo do ritmo"], none: ["–", "Sem meta"] };
let ESPERADO = 0;
const situacao = p => p == null ? "none" : p >= 1 ? "good" : p >= ESPERADO * 0.9 ? "warn" : "crit";
const pill = s => `<span class="pill ${s}">${STATUS[s][0]} ${STATUS[s][1]}</span>`;
function ritmoEsperado(periodo, ultima) {
  if (!periodo) return 0;
  const [a, m] = periodo.split("-").map(Number), fim = new Date(Date.UTC(a, m, 0)).getUTCDate();
  let total = 0, feitos = 0;
  for (let d = 1; d <= fim; d++) { const dt = new Date(Date.UTC(a, m - 1, d)); if (dt.getUTCDay() === 0) continue; total++; if (ultima && dt.toISOString().slice(0, 10) <= ultima) feitos++; }
  return total ? feitos / total : 0;
}
const filtroQS = () => qs({ periodo: S.periodo, gerente: S.gerente, supervisor: S.supervisor, vendedor: S.vendedor });
const semPeriodo = () => `<div class="card"><h3>Nenhum dado ainda</h3><div class="hint">Importe as planilhas do Sankhya em <b>Dados › Importar planilhas</b> ou lance notas e metas manualmente em <b>Lançamentos</b>.</div><div class="toolbar"><button class="btn" onclick="ir('importar')">Importar planilhas</button><button class="btn ghost" onclick="ir('notas')">Lançar nota</button></div></div>`;

/* ============================================================ análise */
async function telaGeral(el) {
  if (!S.periodo) { el.innerHTML = semPeriodo(); return; }
  const d = await api("GET", "/api/painel?" + filtroQS()), k = d.indicadores;
  ESPERADO = ritmoEsperado(S.periodo, k.ultima_data);
  const meter = (perc, prev) => perc == null ? "" : `<div class="meter"><i class="soft" style="width:${Math.min(100, (prev ?? perc) * 100)}%"></i><i style="width:${Math.min(100, perc * 100)}%"></i><s style="left:${Math.min(100, ESPERADO * 100)}%"></s></div>`;
  el.innerHTML = `
    <div class="meta-line">Movimento até <b>${dataBR(k.ultima_data)}</b> · ${pct(ESPERADO, 0)} dos dias úteis (seg–sáb) do mês decorridos · realizado = vendas − devoluções, calculado das notas</div>
    <section class="panel">
    <div class="kpis">
      ${kpi("Faturado líquido", brlC(k.faturado), `${ton(k.kg)} · preço médio ${brl(k.preco_medio, 2)}/kg`, "hero")}
      ${kpi("Meta em kg", pct(k.perc_meta_kg), k.tem_meta ? `${pill(situacao(k.perc_meta_kg))} ${pct(k.perc_prev_kg)} com carteira` : "sem metas no mês", "", meter(k.perc_meta_kg, k.perc_prev_kg))}
      ${kpi("Meta em R$", pct(k.perc_meta_valor), k.tem_meta ? `${brlC(k.vendido_valor)} de ${brlC(k.meta_valor)}` : "", "", meter(k.perc_meta_valor))}
      ${kpi("Falta para a meta", k.tem_meta ? brlC(Math.max(k.meta_valor - k.vendido_valor, 0)) : "–", k.tem_meta ? `${ton(Math.max(k.meta_kg - k.vendido_kg, 0))} a vender` : "")}
      ${kpi("Carteira", brlC(k.carteira_valor), `${ton(k.carteira_kg)} em pedidos fechados`)}
      ${kpi("Clientes positivados", num(k.clientes), `${num(k.notas)} notas · ticket ${brlC(k.ticket_medio)}`)}
      ${kpi("Devoluções", brlC(k.devolucao), `${pct(k.perc_devolucao)} da venda bruta · bonificação ${brlC(k.bonificacao)}`)}
    </div>
    <div class="grid2">
      <div class="card chart"><h3>Faturamento por dia</h3><div class="hint">R$ líquido por data de movimento</div>${svgBarras(d.diarias)}</div>
      <div class="card chart"><h3>Faturamento acumulado x meta</h3><div class="hint">R$ acumulados no mês; linha tracejada = meta em R$</div>${svgAcumulado(d.diarias, k.meta_valor)}</div>
    </div>
    <div class="grid2">
      <div class="card"><h3>Meta por supervisor</h3><div class="hint">Vendido e carteira em kg contra a meta</div>${bullet(d.por_supervisor)}</div>
      <div class="card"><h3>Meta por categoria</h3><div class="hint">Vendido e carteira em kg contra a meta</div>${bullet(d.por_categoria)}</div>
    </div>
    <div class="grid2">
      <div class="card"><h3>Maiores clientes</h3><div class="hint">Faturamento líquido, R$</div>${ranking(d.clientes)}</div>
      <div class="card"><h3>Produtos mais vendidos</h3><div class="hint">Faturamento líquido, R$</div>${ranking(d.produtos)}</div>
    </div>
    <div class="grid2">
      <div class="card"><h3>Por perfil de cliente</h3><div class="hint">Faturamento líquido, R$</div>${ranking(d.perfis)}</div>
      <div class="card"><h3>Por UF</h3><div class="hint">Faturamento líquido, R$</div>${ranking(d.ufs)}</div>
    </div></section>`;
  bindTips(el);
}

const DIM_META = { vendedor: "Vendedor", supervisor: "Supervisor", gerente: "Gerente", categoria: "Categoria", descrprod: "Produto", nomereg: "Região" };
let dimMeta = "vendedor";
async function telaAnaliseMetas(el) {
  if (!S.periodo) { el.innerHTML = semPeriodo(); return; }
  const rows = (await api("GET", `/api/metas/resumo?dimensao=${dimMeta}&` + filtroQS()))
    .map(r => ({ ...r, pm_meta: div(r.meta_valor, r.meta_kg), pm_real: div(r.vendido_valor, r.vendido_kg), diferenca: r.meta_kg - r.vendido_kg, previa: r.meta_kg - r.vendido_kg - r.carteira_kg }));
  el.innerHTML = `<section class="panel">
    <div class="toolbar"><span class="summary">Agrupar por</span><div class="seg">${Object.entries(DIM_META).map(([k, t]) => `<button data-dim="${k}" aria-pressed="${k === dimMeta}">${t}</button>`).join("")}</div></div>
    <div class="card"><h3>Meta x vendido por ${DIM_META[dimMeta].toLowerCase()}</h3><div class="hint">${pill("good")} atingiu · ${pill("warn")} dentro do ritmo (${pct(ESPERADO, 0)} do mês) · ${pill("crit")} abaixo do ritmo</div>${bullet(rows, 60)}</div>
    <div class="tbl" id="t-am"></div></section>`;
  el.querySelectorAll("[data-dim]").forEach(b => b.onclick = () => { dimMeta = b.dataset.dim; telaAnaliseMetas(el); });
  tabela($("t-am"), [
    { k: "grupo", t: DIM_META[dimMeta] }, { k: "perc_meta", t: "Situação", f: v => pill(situacao(v)) },
    { k: "meta_kg", t: "Meta kg", n: 1, f: v => num(v) }, { k: "vendido_kg", t: "Vendido kg", n: 1, f: v => num(v) },
    { k: "perc_meta", t: "% Meta", n: 1, f: v => pct(v) }, { k: "carteira_kg", t: "Carteira kg", n: 1, f: v => num(v) },
    { k: "perc_prev", t: "% c/ carteira", n: 1, f: v => pct(v) }, { k: "meta_valor", t: "Meta R$", n: 1, f: v => brl(v) },
    { k: "vendido_valor", t: "Faturado R$", n: 1, f: v => brl(v) }, { k: "perc_meta_valor", t: "% Meta R$", n: 1, f: v => pct(v) },
    { k: "pm_meta", t: "P.M. meta", n: 1, f: v => brl(v, 2) }, { k: "pm_real", t: "P.M. real", n: 1, f: v => brl(v, 2) },
    { k: "diferenca", t: "Diferença kg", n: 1, f: v => num(v) }, { k: "previa", t: "Prévia kg", n: 1, f: v => num(v) },
  ], rows, ["meta_kg", -1]);
  bindTips(el);
}

const DIM_VENDA = { nomeparc: "Cliente", descrprod: "Produto", vendedor: "Vendedor", supervisor: "Supervisor", gerente: "Gerente", nomereg: "Região", uf: "UF", cidade: "Cidade", regiao_pais: "Região do país", perfil: "Perfil", rede: "Rede", mix_comercial: "Mix comercial", mix_biblia: "Mix bíblia", linha: "Linha", familia: "Família", grupoprod: "Conta estoque", descroper: "TOP", operacao: "Operação (V/D/B)", nomeempresa: "Empresa", dtmov: "Data", origem: "Origem do lançamento" };
let dimVenda = "nomeparc", topN = 15;
async function telaAnaliseVendas(el) {
  if (!S.periodo) { el.innerHTML = semPeriodo(); return; }
  const rows = await api("GET", `/api/vendas/resumo?dimensao=${dimVenda}&` + filtroQS()), total = rows.reduce((s, r) => s + r.faturado, 0);
  rows.forEach(r => r.share = div(r.faturado, total));
  el.innerHTML = `<section class="panel">
    <div class="toolbar"><label for="dv" class="summary">Agrupar por</label><select id="dv">${Object.entries(DIM_VENDA).map(([k, t]) => `<option value="${k}" ${k === dimVenda ? "selected" : ""}>${t}</option>`).join("")}</select>
      <label for="tn" class="summary">Mostrar</label><select id="tn">${[10, 15, 25, 50].map(n => `<option ${n === topN ? "selected" : ""}>${n}</option>`).join("")}</select></div>
    <div class="card"><h3>Faturamento líquido por ${DIM_VENDA[dimVenda].toLowerCase()}</h3><div class="hint">Top ${topN} de ${num(rows.length)} · R$</div>${ranking(rows, topN)}</div>
    <div class="tbl" id="t-av"></div></section>`;
  $("dv").onchange = e => { dimVenda = e.target.value; telaAnaliseVendas(el); };
  $("tn").onchange = e => { topN = +e.target.value; telaAnaliseVendas(el); };
  tabela($("t-av"), [
    { k: "grupo", t: DIM_VENDA[dimVenda], f: v => esc(dimVenda === "dtmov" ? dataBR(v) : v) }, { k: "faturado", t: "Faturado R$", n: 1, f: v => brl(v, 2) },
    { k: "share", t: "% do total", n: 1, f: v => pct(v) }, { k: "kg", t: "Volume kg", n: 1, f: v => num(v, 1) },
    { k: "preco_medio", t: "R$/kg", n: 1, f: v => brl(v, 2) }, { k: "devolucao", t: "Devolução R$", n: 1, f: v => brl(v, 2) },
    { k: "clientes", t: "Clientes", n: 1, f: v => num(v) }, { k: "notas", t: "Notas", n: 1, f: v => num(v) },
  ], rows, ["faturado", -1]);
  bindTips(el);
}

/* ============================================================ campos de formulário */
async function campoLookup(id, rotulo, cad, valor, obrig = false, ajuda = "") {
  const ops = await opcoesCad(cad);
  const atual = valor != null ? `${valor} — ${nomeDe(cad, valor) ?? ""}` : "";
  return `<div class="f"><label for="${id}">${esc(rotulo)}${obrig ? ' <span class="req">*</span>' : ""}</label>
    <input id="${id}" list="${id}-l" value="${esc(atual)}" placeholder="Digite o código ou o nome" autocomplete="off" data-cad="${cad}">
    <datalist id="${id}-l">${ops.map(o => `<option value="${esc(o.codigo + " — " + o.nome)}">`).join("")}</datalist>${ajuda ? `<small>${esc(ajuda)}</small>` : ""}</div>`;
}
function lerLookup(input) {
  const v = input.value.trim(); if (!v) return null;
  const m = v.match(/^(-?\d+)/); if (m) return +m[1];
  const achado = CACHE[input.dataset.cad]?.find(o => String(o.nome).toLowerCase() === v.toLowerCase());
  if (achado) return achado.codigo;
  throw new Error(`"${v}" não encontrado. Escolha da lista ou cadastre antes.`);
}
const campo = (id, rotulo, valor, { tipo = "text", obrig = false, ajuda = "", readonly = false, cls = "", attrs = "" } = {}) =>
  `<div class="f ${cls}"><label for="${id}">${esc(rotulo)}${obrig ? ' <span class="req">*</span>' : ""}</label><input id="${id}" type="${tipo}" value="${esc(valor ?? "")}" ${readonly ? "readonly" : ""} ${attrs}>${ajuda ? `<small>${esc(ajuda)}</small>` : ""}</div>`;
const numBR = s => { s = String(s ?? "").trim(); if (!s) return null; if (s.includes(",")) s = s.replace(/\./g, "").replace(",", "."); const n = Number(s); if (!isFinite(n)) throw new Error(`Número inválido: ${s}`); return n; };

/* ============================================================ cadastros (genérico) */
const estadoCad = {};
async function telaCadastro(el, nome) {
  const spec = S.inicio.cadastros[nome], st = (estadoCad[nome] ||= { busca: "", pagina: 0 });
  const fks = spec.campos.filter(c => c.tipo.startsWith("fk:"));
  await Promise.all(fks.map(c => opcoesCad(c.tipo.slice(3))));
  const d = await api("GET", `/api/cadastros/${nome}?` + qs({ busca: st.busca, pagina: st.pagina, por_pagina: 50 }));
  const pags = Math.max(1, Math.ceil(d.total / 50));
  el.innerHTML = `<section class="panel">
    <div class="toolbar"><input class="search" id="cb" type="search" placeholder="Buscar ${esc(spec.titulo.toLowerCase())}…" value="${esc(st.busca)}"><span class="grow"></span>
      <span class="summary"><b>${num(d.total)}</b> ${esc(spec.titulo.toLowerCase())} · tabela Sankhya ${spec.sankhya}</span><button class="btn" id="cn">+ Novo ${esc(spec.item)}</button></div>
    <div class="tbl" id="t-cad"></div>
    <div class="pager"><button class="btn ghost small" id="pa" ${st.pagina ? "" : "disabled"}>‹ Anterior</button>Página ${st.pagina + 1} de ${pags}<button class="btn ghost small" id="pp" ${st.pagina < pags - 1 ? "" : "disabled"}>Próxima ›</button></div></section>`;
  const cols = spec.lista.map(k => {
    const c = spec.campos.find(x => x.campo === k);
    return { k, t: esc(c.rotulo), n: c.tipo === "int" || c.tipo === "float", f: c.tipo.startsWith("fk:") ? v => v == null ? "" : `${v} — ${esc(nomeDe(c.tipo.slice(3), v) ?? "")}` : c.tipo === "sn01" ? v => v ? '<span class="tag prov">provisório</span>' : "" : c.tipo === "sn" ? v => v === "N" ? "Não" : "Sim" : null };
  });
  tabela($("t-cad"), cols, d.linhas, null, r => formCadastro(nome, r));
  let t; $("cb").oninput = e => { clearTimeout(t); t = setTimeout(async () => { st.busca = e.target.value; st.pagina = 0; await telaCadastro(el, nome); const i = $("cb"); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }, 300); };
  $("cn").onclick = () => formCadastro(nome, null);
  $("pa").onclick = () => { st.pagina--; telaCadastro(el, nome); };
  $("pp").onclick = () => { st.pagina++; telaCadastro(el, nome); };
}
async function formCadastro(nome, reg) {
  const spec = S.inicio.cadastros[nome], novo = !reg;
  const partes = [];
  for (const c of spec.campos) {
    const id = "c-" + c.campo, v = reg?.[c.campo];
    if (c.tipo.startsWith("fk:")) partes.push(await campoLookup(id, c.rotulo, c.tipo.slice(3), v, c.obrigatorio, c.ajuda || ""));
    else if (c.tipo === "sn") partes.push(`<div class="f"><label for="${id}">${esc(c.rotulo)}</label><select id="${id}"><option value="S" ${v !== "N" ? "selected" : ""}>Sim</option><option value="N" ${v === "N" ? "selected" : ""}>Não</option></select></div>`);
    else if (c.tipo === "sn01") { if (!novo && v) partes.push(`<div class="f"><label>${esc(c.rotulo)}</label><div class="note">Código criado pelo sistema porque o resumo de metas não traz o código do vendedor. Troque pelo código do Sankhya: notas e metas acompanham.</div></div>`); }
    else if (c.tipo === "op") partes.push(`<div class="f"><label for="${id}">${esc(c.rotulo)} <span class="req">*</span></label><select id="${id}">${[["V", "Venda"], ["D", "Devolução"], ["B", "Bonificação"]].map(([k, t]) => `<option value="${k}" ${v === k ? "selected" : ""}>${k} — ${t}</option>`).join("")}</select></div>`);
    else partes.push(campo(id, c.rotulo, v, { tipo: c.tipo === "int" || c.tipo === "float" ? "text" : "text", obrig: c.obrigatorio, ajuda: c.campo === spec.chave && !novo ? "Alterar o código atualiza notas e metas vinculadas." : c.ajuda || "", attrs: c.tipo === "int" ? 'inputmode="numeric"' : "" }));
  }
  gaveta({
    titulo: novo ? `Novo ${spec.item}` : `${spec.item[0].toUpperCase() + spec.item.slice(1)} ${reg[spec.chave]}`,
    sub: `${spec.titulo} · ${spec.sankhya}`, corpo: `<div class="form">${partes.join("")}</div>`,
    salvar: async d => {
      const dados = {};
      for (const c of spec.campos) {
        const inp = d.querySelector("#c-" + c.campo); if (!inp) continue;
        dados[c.campo] = c.tipo.startsWith("fk:") ? lerLookup(inp) : inp.value;
      }
      if (novo) await api("POST", `/api/cadastros/${nome}`, dados); else await api("PUT", `/api/cadastros/${nome}/${reg[spec.chave]}`, dados);
      delete CACHE[nome]; toast(novo ? `${spec.item[0].toUpperCase() + spec.item.slice(1)} cadastrado.` : "Alterações salvas."); render();
    },
    excluir: novo ? null : async () => {
      if (!await confirmar(`Excluir ${spec.item}?`, `${reg[spec.chave]} — ${reg[spec.campos[1].campo]}. Esta ação não pode ser desfeita.`, "Excluir")) return false;
      await api("DELETE", `/api/cadastros/${nome}/${reg[spec.chave]}`); delete CACHE[nome]; toast("Excluído."); render(); return true;
    },
  });
}

/* ============================================================ notas */
const estNotas = { busca: "", origem: "", pagina: 0 };
async function telaNotas(el) {
  const d = await api("GET", "/api/notas?" + qs({ periodo: S.periodo || "", busca: estNotas.busca, origem: estNotas.origem, pagina: estNotas.pagina, por_pagina: 50 }));
  const pags = Math.max(1, Math.ceil(d.total / 50));
  el.innerHTML = `<section class="panel">
    <div class="toolbar"><input class="search" id="nb" type="search" placeholder="Buscar cliente, vendedor, nº da nota, cidade…" value="${esc(estNotas.busca)}">
      <select id="no"><option value="">Todas as origens</option><option value="manual" ${estNotas.origem === "manual" ? "selected" : ""}>Lançadas no sistema</option><option value="planilha" ${estNotas.origem === "planilha" ? "selected" : ""}>Importadas de planilha</option></select>
      <span class="grow"></span><button class="btn" id="nn">+ Nova nota</button></div>
    <div class="summary"><b>${num(d.total)}</b> notas em ${perLabel(S.periodo)} · <b>${brl(d.valor_total, 2)}</b> em itens (devoluções e bonificações negativas)</div>
    <div class="tbl" id="t-notas"></div>
    <div class="pager"><button class="btn ghost small" id="pa" ${estNotas.pagina ? "" : "disabled"}>‹ Anterior</button>Página ${estNotas.pagina + 1} de ${pags}<button class="btn ghost small" id="pp" ${estNotas.pagina < pags - 1 ? "" : "disabled"}>Próxima ›</button></div></section>`;
  tabela($("t-notas"), [
    { k: "nunota", t: "Nº único", n: 1 }, { k: "numnota", t: "Nota fiscal", n: 1 }, { k: "dtmov", t: "Data", f: dataBR },
    { k: "codtipoper", t: "TOP", f: (v, r) => `${v} <span class="summary">${esc(r.operacao)}</span>` }, { k: "nomeparc", t: "Cliente" },
    { k: "cidade", t: "Cidade", f: (v, r) => `${esc(v ?? "")}${r.uf ? "/" + esc(r.uf) : ""}` }, { k: "vendedor", t: "Vendedor" },
    { k: "itens", t: "Itens", n: 1 }, { k: "qtd_kg", t: "Kg", n: 1, f: v => num(v, 1) }, { k: "vlrtot", t: "Valor R$", n: 1, f: v => brl(v, 2) },
    { k: "origem", t: "Origem", f: v => `<span class="tag ${v === "manual" ? "manual" : ""}">${v === "manual" ? "sistema" : esc(v)}</span>` },
  ], d.linhas, null, r => formNota(r.nunota));
  let t; $("nb").oninput = e => { clearTimeout(t); t = setTimeout(async () => { estNotas.busca = e.target.value; estNotas.pagina = 0; await telaNotas(el); const i = $("nb"); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }, 300); };
  $("no").onchange = e => { estNotas.origem = e.target.value; estNotas.pagina = 0; telaNotas(el); };
  $("nn").onclick = () => formNota(null);
  $("pa").onclick = () => { estNotas.pagina--; telaNotas(el); };
  $("pp").onclick = () => { estNotas.pagina++; telaNotas(el); };
}
async function formNota(nunota) {
  const n = nunota ? await api("GET", `/api/notas/${nunota}`) : { dtmov: new Date().toISOString().slice(0, 10), codemp: 1, codtipoper: 500, itens: [{}] };
  await Promise.all(["produtos", "tops", "empresas", "clientes", "vendedores", "regioes"].map(c => opcoesCad(c)));
  const prodOps = `<datalist id="prod-l">${CACHE.produtos.map(o => `<option value="${esc(o.codigo + " — " + o.nome)}">`).join("")}</datalist>`;
  const linhaItem = it => `<tr>
    <td class="cell" style="min-width:260px"><input list="prod-l" data-cad="produtos" data-k="codprod" value="${it.codprod != null ? esc(it.codprod + " — " + (it.descrprod ?? nomeDe("produtos", it.codprod) ?? "")) : ""}" placeholder="Produto"></td>
    <td class="cell n" style="width:110px"><input data-k="qtd_kg" inputmode="decimal" value="${it.qtd_kg != null ? num(Math.abs(it.qtd_kg), 3) : ""}"></td>
    <td class="cell n" style="width:130px"><input data-k="vlrtot" inputmode="decimal" value="${it.vlrtot != null ? num(Math.abs(it.vlrtot), 2) : ""}"></td>
    <td class="cell n" style="width:100px"><input data-k="vlrsubst" inputmode="decimal" value="${it.vlrsubst ? num(Math.abs(it.vlrsubst), 2) : ""}"></td>
    <td class="cell n" style="width:110px"><input data-k="nucte" inputmode="numeric" value="${it.nucte ?? ""}"></td>
    <td><button class="btn link" data-rm title="Remover item">✕</button></td></tr>`;
  const corpo = `
    <div class="form">
      ${campo("n-nunota", "Nº único", nunota ?? "gerado ao salvar", { readonly: true })}
      ${campo("n-numnota", "Nota fiscal", n.numnota, { attrs: 'inputmode="numeric"' })}
      ${campo("n-dtmov", "Data do movimento", n.dtmov, { tipo: "date", obrig: true })}
      ${await campoLookup("n-emp", "Empresa", "empresas", n.codemp, true)}
      ${await campoLookup("n-top", "TOP", "tops", n.codtipoper, true, "Devolução e bonificação ficam negativas automaticamente")}
      ${await campoLookup("n-parc", "Cliente", "clientes", n.codparc, true)}
      ${await campoLookup("n-vend", "Vendedor", "vendedores", n.codvend, true)}
      ${await campoLookup("n-reg", "Região", "regioes", n.codreg, false, "Vazio = região do vendedor")}
      ${campo("n-rvv", "Ref. RVV", n.ref_rvv, { ajuda: "MM/AAAA; vazio = mês da data" })}
    </div>
    <div><div class="toolbar" style="margin-bottom:8px"><h3 style="font-size:15px">Itens</h3><span class="grow"></span><button class="btn ghost small" id="n-add">+ Adicionar item</button></div>
      <div class="itens"><table><thead><tr><th>Produto</th><th class="n">Qtde kg</th><th class="n">Valor total R$</th><th class="n">Valor ST R$</th><th class="n">Nº CT-e</th><th></th></tr></thead>
      <tbody id="n-itens">${(n.itens.length ? n.itens : [{}]).map(linhaItem).join("")}</tbody><tfoot><tr class="tot"><td>Total</td><td class="n" id="n-tkg">–</td><td class="n" id="n-tvl">–</td><td class="n" id="n-tst">–</td><td colspan="2"></td></tr></tfoot></table></div>
      ${prodOps}<p class="summary" style="margin:8px 0 0">Digite valores positivos. O sinal segue a TOP.${n.origem && n.origem !== "manual" ? " Esta nota veio de planilha: ao salvar, passa a ser um lançamento do sistema e não é apagada na próxima importação do mês." : ""}</p></div>`;
  const d = gaveta({
    titulo: nunota ? `Nota ${n.numnota ?? ""} · nº único ${nunota}` : "Nova nota de venda", sub: "Cabeçalho (TGFCAB) e itens (TGFITE)", corpo,
    salvar: async d => {
      const itens = [...d.querySelectorAll("#n-itens tr")].map(tr => {
        const g = k => tr.querySelector(`[data-k="${k}"]`);
        if (!g("codprod").value.trim() && !g("qtd_kg").value.trim() && !g("vlrtot").value.trim()) return null;
        return { codprod: lerLookup(g("codprod")), qtd_kg: numBR(g("qtd_kg").value), vlrtot: numBR(g("vlrtot").value), vlrsubst: numBR(g("vlrsubst").value), nucte: g("nucte").value.trim() || null };
      }).filter(Boolean);
      const dados = { numnota: d.querySelector("#n-numnota").value, dtmov: d.querySelector("#n-dtmov").value, codemp: lerLookup(d.querySelector("#n-emp")),
        codtipoper: lerLookup(d.querySelector("#n-top")), codparc: lerLookup(d.querySelector("#n-parc")), codvend: lerLookup(d.querySelector("#n-vend")),
        codreg: lerLookup(d.querySelector("#n-reg")), ref_rvv: d.querySelector("#n-rvv").value, itens };
      const r = nunota ? await api("PUT", `/api/notas/${nunota}`, dados) : await api("POST", "/api/notas", dados);
      toast(nunota ? "Nota alterada." : `Nota ${r.nunota} lançada.`);
      if (!S.periodo || !S.inicio.periodos.includes(r.dtmov.slice(0, 7))) { S.periodo = r.dtmov.slice(0, 7); await carregarInicio(); }
      render();
    },
    excluir: nunota ? async () => {
      if (!await confirmar("Excluir nota?", `Nº único ${nunota} e todos os itens. Esta ação não pode ser desfeita.`, "Excluir")) return false;
      await api("DELETE", `/api/notas/${nunota}`); toast("Nota excluída."); render(); return true;
    } : null,
  });
  const totais = () => {
    let kg = 0, vl = 0, st = 0;
    d.querySelectorAll("#n-itens tr").forEach(tr => { try { kg += numBR(tr.querySelector('[data-k="qtd_kg"]').value) || 0; vl += numBR(tr.querySelector('[data-k="vlrtot"]').value) || 0; st += numBR(tr.querySelector('[data-k="vlrsubst"]').value) || 0; } catch (_) {} });
    $("n-tkg").textContent = num(kg, 3); $("n-tvl").textContent = brl(vl, 2); $("n-tst").textContent = brl(st, 2);
  };
  const ligar = () => { d.querySelectorAll("[data-rm]").forEach(b => b.onclick = () => { b.closest("tr").remove(); totais(); }); };
  d.querySelector("#n-itens").addEventListener("input", totais);
  d.querySelector("#n-add").onclick = () => { d.querySelector("#n-itens").insertAdjacentHTML("beforeend", linhaItem({})); ligar(); d.querySelector("#n-itens tr:last-child input").focus(); };
  ligar(); totais();
}

/* ============================================================ metas do mês */
const estMetas = { busca: "", pagina: 0 };
async function telaMetas(el) {
  if (!S.periodo) { el.innerHTML = semPeriodo(); return; }
  const rows = await api("GET", "/api/metas?" + qs({ periodo: S.periodo, busca: estMetas.busca }));
  const tot = rows.reduce((a, r) => ({ meta: a.meta + r.qtd_meta, prev: a.prev + r.vlr_previsto, vend: a.vend + r.qtd_vendida, cart: a.cart + r.qtd_fechada }), { meta: 0, prev: 0, vend: 0, cart: 0 });
  const POR = 100, pags = Math.max(1, Math.ceil(rows.length / POR)); estMetas.pagina = Math.min(estMetas.pagina, pags - 1);
  el.innerHTML = `<section class="panel">
    <div class="toolbar"><input class="search" id="mb" type="search" placeholder="Buscar vendedor, produto, categoria, região…" value="${esc(estMetas.busca)}"><span class="grow"></span>
      <button class="btn ghost" id="mc">Copiar metas de outro mês</button><button class="btn" id="mn">+ Nova meta</button></div>
    <div class="summary"><b>${num(rows.length)}</b> linhas em ${perLabel(S.periodo)} · meta <b>${num(tot.meta)} kg</b> (${brl(tot.prev)}) · vendido nas notas <b>${num(tot.vend)} kg</b> (${pct(div(tot.vend, tot.meta))}) · carteira ${num(tot.cart)} kg</div>
    <div class="tbl" id="t-metas" style="max-height:640px"></div>
    <div class="pager"><button class="btn ghost small" id="pa" ${estMetas.pagina ? "" : "disabled"}>‹ Anterior</button>Página ${estMetas.pagina + 1} de ${pags}<button class="btn ghost small" id="pp" ${estMetas.pagina < pags - 1 ? "" : "disabled"}>Próxima ›</button></div></section>`;
  tabela($("t-metas"), [
    { k: "nomereg", t: "Região" }, { k: "vendedor", t: "Vendedor" }, { k: "descrprod", t: "Produto", f: (v, r) => `${r.codprod} — ${esc(v)}` }, { k: "categoria", t: "Categoria" },
    { k: "qtd_meta", t: "Meta kg", n: 1, f: v => num(v) }, { k: "pm_meta", t: "P.M. meta", n: 1, f: v => brl(v, 2) }, { k: "vlr_previsto", t: "Previsto R$", n: 1, f: v => brl(v) },
    { k: "qtd_fechada", t: "Carteira kg", n: 1, f: v => num(v) }, { k: "vlr_fechado", t: "Carteira R$", n: 1, f: v => brl(v) },
    { k: "qtd_vendida", t: "Vendido kg", n: 1, f: v => num(v, 1) }, { k: "perc_meta", t: "% Meta", n: 1, f: v => pct(v) },
    { k: "origem", t: "Origem", f: v => `<span class="tag ${v === "manual" ? "manual" : ""}">${v === "manual" ? "sistema" : esc(v)}</span>` },
  ], rows.slice(estMetas.pagina * POR, (estMetas.pagina + 1) * POR), null, r => formMeta(r));
  let t; $("mb").oninput = e => { clearTimeout(t); t = setTimeout(async () => { estMetas.busca = e.target.value; estMetas.pagina = 0; await telaMetas(el); const i = $("mb"); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }, 300); };
  $("mn").onclick = () => formMeta(null);
  $("mc").onclick = () => formCopiar();
  $("pa").onclick = () => { estMetas.pagina--; telaMetas(el); };
  $("pp").onclick = () => { estMetas.pagina++; telaMetas(el); };
}
async function formMeta(m) {
  const novo = !m; m = m || { periodo: S.periodo };
  const corpo = `<div class="form">
    ${campo("m-per", "Mês", m.periodo, { tipo: "month", obrig: true })}
    ${await campoLookup("m-vend", "Vendedor", "vendedores", m.codvend, true)}
    ${await campoLookup("m-reg", "Região", "regioes", m.codreg, false, "Vazio = região do vendedor")}
    ${await campoLookup("m-prod", "Produto", "produtos", m.codprod, true)}
    ${campo("m-meta", "Meta (kg)", m.qtd_meta != null ? num(m.qtd_meta, 3) : "", { obrig: true, attrs: 'inputmode="decimal"' })}
    ${campo("m-pm", "Preço médio da meta (R$/kg)", m.pm_meta != null ? num(m.pm_meta, 2) : "", { obrig: true, attrs: 'inputmode="decimal"' })}
    ${campo("m-cart", "Carteira (kg)", m.qtd_fechada ? num(m.qtd_fechada, 3) : "", { ajuda: "Pedidos fechados ainda não faturados", attrs: 'inputmode="decimal"' })}
    ${campo("m-vcart", "Carteira (R$)", m.vlr_fechado ? num(m.vlr_fechado, 2) : "", { attrs: 'inputmode="decimal"' })}
  </div>${!novo ? `<div class="note">Realizado nas notas: <b>${num(m.qtd_vendida, 1)} kg</b> · ${brl(m.vlr_faturado, 2)} · ${pct(m.perc_meta)} da meta${m.vendido_rel != null ? ` · no resumo importado: ${num(m.vendido_rel, 1)} kg` : ""}</div>` : ""}`;
  gaveta({
    titulo: novo ? "Nova meta" : `Meta · ${m.vendedor} · ${m.descrprod}`, sub: "TGFMET · meta por região, vendedor e produto no mês", corpo,
    salvar: async d => {
      const g = id => d.querySelector("#" + id);
      const dados = { periodo: g("m-per").value, codvend: lerLookup(g("m-vend")), codreg: lerLookup(g("m-reg")), codprod: lerLookup(g("m-prod")),
        qtd_meta: numBR(g("m-meta").value), pm_meta: numBR(g("m-pm").value), qtd_fechada: numBR(g("m-cart").value), vlr_fechado: numBR(g("m-vcart").value) };
      if (novo) await api("POST", "/api/metas", dados); else await api("PUT", `/api/metas/${m.id}`, dados);
      toast(novo ? "Meta lançada." : "Meta alterada.");
      if (!S.inicio.periodos.includes(dados.periodo)) { S.periodo = dados.periodo; await carregarInicio(); }
      render();
    },
    excluir: novo ? null : async () => {
      if (!await confirmar("Excluir meta?", `${m.vendedor} · ${m.descrprod} em ${perLabel(m.periodo)}.`, "Excluir")) return false;
      await api("DELETE", `/api/metas/${m.id}`); toast("Meta excluída."); render(); return true;
    },
  });
}
function formCopiar() {
  const [a, m] = (S.periodo || new Date().toISOString().slice(0, 7)).split("-").map(Number);
  const prox = `${m === 12 ? a + 1 : a}-${String(m === 12 ? 1 : m + 1).padStart(2, "0")}`;
  gaveta({
    titulo: "Copiar metas de um mês para outro", sub: "Copia meta e preço médio; carteira e realizado começam zerados", rotuloSalvar: "Copiar",
    corpo: `<div class="form">${campo("cp-de", "Copiar de", S.periodo, { tipo: "month", obrig: true })}${campo("cp-para", "Para", prox, { tipo: "month", obrig: true })}</div><div class="note">Linhas que já existem no mês de destino não são alteradas.</div>`,
    salvar: async d => {
      const r = await api("POST", "/api/metas/copiar", { de: d.querySelector("#cp-de").value, para: d.querySelector("#cp-para").value });
      toast(`${num(r.copiadas)} metas copiadas.`); S.periodo = d.querySelector("#cp-para").value; await carregarInicio(); render();
    },
  });
}

/* ============================================================ importar */
function telaImportar(el) {
  el.innerHTML = `<section class="panel">
    <div class="drop" id="drop" tabindex="0" role="button" aria-label="Escolher planilhas">
      <span class="up"><svg class="i" viewBox="0 0 24 24"><path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/></svg></span>
      <strong>Arraste as planilhas aqui ou clique para escolher</strong>
      <p>Demonstrativo Mensal das Vendas Efetuadas e/ou Resumo Geral das Metas/Vendas, do jeito que saem do Sankhya (.xls, .xlsx ou .csv). O tipo é reconhecido sozinho.</p>
      <input type="file" id="file" accept=".xls,.xlsx,.csv" multiple hidden></div>
    <div class="opts"><div class="f" style="max-width:240px"><label for="pm">Mês das metas</label><input type="month" id="pm"><small>Vazio = mês da data de emissão do resumo</small></div>
      <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="fz"> Reimportar mesmo se o arquivo já foi importado</label></div>
    <div class="card"><h3>O que acontece numa importação</h3><div class="hint" style="margin:0;max-width:95ch">
      Vendedores, clientes, produtos, regiões, TOPs e empresas da planilha são criados ou atualizados nos cadastros. As notas e metas importadas antes para o mesmo mês são substituídas pelas da planilha. Lançamentos feitos no sistema (origem "sistema") continuam, a não ser que a planilha traga uma nota com o mesmo nº único. Cada importação pode ser desfeita em Histórico e exportação.</div></div>
    <div class="log" id="log"></div></section>`;
  const drop = $("drop"), inp = $("file");
  drop.onclick = () => inp.click();
  drop.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inp.click(); } };
  drop.ondragover = e => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove("over"); enviar([...e.dataTransfer.files]); };
  inp.onchange = () => { enviar([...inp.files]); inp.value = ""; };
  async function enviar(files) {
    files.sort((a, b) => /metas/i.test(b.name) - /metas/i.test(a.name));   // resumo de metas antes; o demonstrativo corrige os códigos provisórios
    for (const f of files) {
      const item = document.createElement("div"); item.className = "msg info"; item.textContent = `Enviando ${f.name}…`; $("log").prepend(item);
      const fd = new FormData(); fd.append("arquivo", f); fd.append("periodo_meta", $("pm").value); fd.append("forcar", $("fz").checked ? "true" : "false");
      try {
        const r = await api("POST", "/api/importar", fd);
        if (r.ignorada) { item.innerHTML = `<b>${esc(f.name)}</b>: igual ao último importado. Nada mudou.`; continue; }
        item.className = "msg ok";
        item.innerHTML = `<b>${esc(f.name)}</b> → ${r.tipo === "vendas" ? "Demonstrativo de vendas" : "Resumo de metas"} de ${r.periodos.map(perLabel).join(", ")}: ${num(r.linhas)} linhas${r.substituidas ? ` (substituíram ${num(r.substituidas)} importadas antes)` : ""}.${r.avisos.map(a => `<br>⚠ ${esc(a)}`).join("")}`;
        S.periodo = r.periodos.at(-1);
      } catch (e) { item.className = "msg err"; item.innerHTML = `<b>${esc(f.name)}</b>: ${esc(e.message)}`; }
    }
    Object.keys(CACHE).forEach(k => delete CACHE[k]);
    await carregarInicio(); preencherFiltros(); atualizarContadores();
  }
}

/* ============================================================ histórico e exportação */
async function telaCargas(el) {
  const rows = await api("GET", "/api/cargas");
  el.innerHTML = `<section class="panel">
    <div class="card"><h3>Exportar</h3><div class="hint">CSV com as colunas no padrão Sankhya, separado por ponto e vírgula, respeitando os filtros do topo. A base completa sai como arquivo SQLite.</div>
      <div class="toolbar"><a class="btn ghost small" href="/api/exportar/vendas.csv?${filtroQS()}" ${S.periodo ? "" : 'aria-disabled="true"'}>Itens de venda ${perLabel(S.periodo)} (CSV)</a>
      <a class="btn ghost small" href="/api/exportar/metas.csv?${filtroQS()}">Metas ${perLabel(S.periodo)} (CSV)</a>
      <a class="btn ghost small" href="/api/exportar/base.db">Base completa (SQLite)</a></div></div>
    <div class="card"><h3>Importações</h3><div class="hint">Desfazer remove as notas e metas que vieram daquela planilha. Cadastros criados por ela continuam.</div><div class="tbl" id="t-cargas"></div></div></section>`;
  tabela($("t-cargas"), [
    { k: "id", t: "#", n: 1 }, { k: "tipo", t: "Relatório", f: v => v === "vendas" ? "Demonstrativo de vendas" : "Resumo de metas" }, { k: "arquivo", t: "Arquivo" },
    { k: "periodos", t: "Período", f: v => String(v).split(",").map(perLabel).join(", ") }, { k: "linhas", t: "Linhas", n: 1, f: v => num(v) },
    { k: "emitido_em", t: "Emitido em" }, { k: "usuario_relatorio", t: "Usuário" }, { k: "importado_em", t: "Importado em" },
    { k: "id", t: "", f: v => `<button class="btn link" data-desf="${v}">Desfazer</button>` },
  ], rows, null);
  el.querySelectorAll("[data-desf]").forEach(b => b.onclick = async () => {
    const c = rows.find(r => r.id === +b.dataset.desf);
    if (!await confirmar("Desfazer importação?", `${c.arquivo} (${String(c.periodos).split(",").map(perLabel).join(", ")}): as notas e metas que vieram dessa planilha serão removidas.`, "Desfazer")) return;
    try { const r = await api("DELETE", `/api/cargas/${c.id}`); toast(`Removidas ${num(r.notas)} notas e ${num(r.metas)} metas.`); await carregarInicio(); preencherFiltros(); render(); }
    catch (e) { toast(e.message, true); }
  });
}

/* ============================================================ validação */
const ESTADO = { ok: ["good", "✔ Confere"], aviso: ["warn", "▲ Atenção"], erro: ["crit", "✖ Diverge"] };
async function telaValidacao(el) {
  if (!S.periodo) { el.innerHTML = semPeriodo(); return; }
  const [rows, conc] = await Promise.all([api("GET", `/api/validacao?periodo=${S.periodo}`), api("GET", `/api/conciliacao?periodo=${S.periodo}`)]);
  const n = e => rows.filter(r => r.estado === e).length, grupos = [...new Set(rows.map(r => r.grupo))];
  const fmt = v => typeof v === "number" ? num(v, Number.isInteger(v) ? 0 : 2) : esc(v);
  el.innerHTML = `<section class="panel">
    <div class="kpis">${kpi("Verificações", num(rows.length), `período ${perLabel(S.periodo)}`)}${kpi("Conferem", num(n("ok")), "valores iguais aos da planilha")}${kpi("Atenção", num(n("aviso")), "diferenças esperadas ou explicadas")}${kpi("Divergem", num(n("erro")), n("erro") ? "precisa revisar" : "nenhuma divergência")}</div>
    ${grupos.map(g => `<div class="card"><h3>${esc(g)}</h3><div class="tbl" style="margin-top:10px"><table><thead><tr><th>Verificação</th><th class="n">Esperado</th><th class="n">Na base</th><th>Resultado</th><th>Observação</th></tr></thead><tbody>
      ${rows.filter(r => r.grupo === g).map(r => `<tr><td>${esc(r.item)}</td><td class="n">${fmt(r.esperado)}</td><td class="n">${fmt(r.obtido)}</td><td><span class="pill ${ESTADO[r.estado][0]}">${ESTADO[r.estado][1]}</span></td><td style="white-space:normal;min-width:240px;color:var(--ink-2)">${esc(r.obs)}</td></tr>`).join("")}
    </tbody></table></div></div>`).join("")}
    <div class="card"><h3>Conciliação: resumo de metas importado x notas</h3><div class="hint">${num(conc.length)} linhas de meta em que o "Vendido" do resumo difere do realizado calculado das notas (mesma região, vendedor e produto).</div><div class="tbl" id="t-conc"></div></div></section>`;
  tabela($("t-conc"), [
    { k: "regiao", t: "Região" }, { k: "vendedor", t: "Vendedor" }, { k: "produto", t: "Produto" },
    { k: "kg_resumo", t: "kg resumo", n: 1, f: v => num(v, 1) }, { k: "kg_notas", t: "kg notas", n: 1, f: v => num(v, 1) }, { k: "dif_kg", t: "Dif. kg", n: 1, f: v => num(v, 1) },
    { k: "valor_resumo", t: "R$ resumo", n: 1, f: v => brl(v, 2) }, { k: "valor_notas", t: "R$ notas", n: 1, f: v => brl(v, 2) }, { k: "dif_valor", t: "Dif. R$", n: 1, f: v => brl(v, 2) },
  ], conc, null);
}

/* ============================================================ navegação */
const TELAS = { geral: telaGeral, "analise-metas": telaAnaliseMetas, "analise-vendas": telaAnaliseVendas, notas: telaNotas, metas: telaMetas, importar: telaImportar, cargas: telaCargas, validacao: telaValidacao };

async function carregarInicio() {
  S.inicio = await api("GET", "/api/inicio");
  if (!S.inicio.periodos.includes(S.periodo)) S.periodo = S.inicio.periodos[0] || null;
}
async function preencherFiltros() {
  $("f-periodo").innerHTML = S.inicio.periodos.map(p => `<option value="${p}">${perLabel(p)}</option>`).join("") || `<option value="">sem dados</option>`;
  $("f-periodo").value = S.periodo || "";
  S.opcoes = S.periodo ? await api("GET", `/api/opcoes?periodo=${S.periodo}`) : { gerente: [], supervisor: [], vendedor: [] };
  for (const [c, rot] of [["gerente", "Todos os gerentes"], ["supervisor", "Todos os supervisores"], ["vendedor", "Todos os vendedores"]]) {
    if (!S.opcoes[c].includes(S[c])) S[c] = "";
    $("f-" + c).innerHTML = `<option value="">${rot}</option>` + S.opcoes[c].map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
    $("f-" + c).value = S[c];
  }
}
async function atualizarContadores() {
  const c = S.inicio.contagens;
  $("n-notas").textContent = num(c.notas); $("n-metas").textContent = num(c.metas); $("n-cargas").textContent = num(c.cargas);
  for (const k of Object.keys(S.inicio.cadastros)) { const e = $("n-" + k); if (e) e.textContent = num(c[k]); }
  if (S.periodo) {
    try {
      const v = await api("GET", `/api/validacao?periodo=${S.periodo}`), e = v.filter(r => r.estado === "erro").length;
      $("n-valid").textContent = e ? `${e} ✖` : "✔"; $("n-valid").style.color = e ? "var(--crit-ink)" : "var(--good-ink)";
    } catch (_) {}
  } else $("n-valid").textContent = "–";
}

function ir(pagina) { location.hash = pagina; }
async function render() {
  hideTip();
  const p = S.pagina, el = $("conteudo");
  const cad = S.inicio.cadastros[p];
  const [titulo, sub, filtros] = cad ? [cad.titulo, `Cadastro · tabela ${cad.sankhya} no Sankhya`, ""] : PAGINAS[p];
  $("pg-titulo").textContent = titulo; $("pg-sub").textContent = sub; document.title = `${titulo} · Vendas x Metas`;
  document.querySelectorAll(".tab").forEach(b => b.dataset.tab === p ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current"));
  $("filters").hidden = !filtros;
  document.querySelectorAll('[data-f="equipe"]').forEach(f => f.hidden = filtros !== "equipe");
  $("app").classList.remove("open");
  if (el.dataset.pagina !== p) { el.innerHTML = `<div class="loading">Carregando…</div>`; el.dataset.pagina = p; }
  try { await (cad ? telaCadastro(el, p) : TELAS[p](el)); }
  catch (e) { el.innerHTML = `<div class="msg err">Não foi possível carregar: ${esc(e.message)}</div>`; }
  atualizarContadores();
  try { S.inicio = await api("GET", "/api/inicio"); } catch (_) {}
}

window.addEventListener("hashchange", () => { const p = location.hash.slice(1); if (p && p !== S.pagina) { S.pagina = p; render(); } });
["periodo", "gerente", "supervisor", "vendedor"].forEach(c => $("f-" + c).addEventListener("change", async e => {
  S[c] = e.target.value; if (c === "periodo") await preencherFiltros(); render();
}));
$("menu-btn").onclick = () => $("app").classList.add("open");
$("scrim").onclick = () => $("app").classList.remove("open");

function aplicarTema(t) {
  const root = document.documentElement;
  if (t === "light" || t === "dark") root.setAttribute("data-theme", t); else root.removeAttribute("data-theme");
  document.querySelectorAll("[data-tema]").forEach(b => b.setAttribute("aria-pressed", b.dataset.tema === t));
  try { localStorage.setItem("vm-tema", t); } catch (_) {}
}
document.querySelectorAll("[data-tema]").forEach(b => b.onclick = () => aplicarTema(b.dataset.tema));
let temaSalvo = "system"; try { temaSalvo = localStorage.getItem("vm-tema") || "system"; } catch (_) {}
aplicarTema(temaSalvo);

(async () => {
  try { await carregarInicio(); }
  catch (e) { $("conteudo").innerHTML = `<div class="msg err">Não foi possível falar com o servidor do sistema. Ele está rodando? (${esc(e.message)})</div>`; return; }
  $("nav-cadastros").innerHTML = Object.entries(S.inicio.cadastros).map(([k, c]) =>
    `<button class="tab" data-tab="${k}"><svg class="i" viewBox="0 0 24 24">${ICONE_CAD[k] || ""}</svg>${esc({ tops: "TOPs" }[k] || c.titulo)}<span class="count" id="n-${k}">0</span></button>`).join("");
  document.querySelectorAll(".tab").forEach(b => b.onclick = () => ir(b.dataset.tab));
  const p = location.hash.slice(1);
  S.pagina = TELAS[p] || S.inicio.cadastros[p] ? p : "geral";
  await preencherFiltros();
  render();
})();
