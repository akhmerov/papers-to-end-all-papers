// Dataset dashboard: filters, linked charts and a searchable list over data/records.json.
"use strict";

const WINDOW = ["2026-04-18", "2026-10-18"];
const PAGE = 40;
const FIELD_SHORT = {
  "quantum-software": "Quantum algorithms, circuits, software", "quantum-information": "Quantum information theory, codes",
  "quantum-hardware": "Quantum devices and control", "structural-materials": "Metals, alloys, structural",
  "molecular-soft": "Polymers, soft matter", "porous-hosts": "Porous frameworks",
  "energy-reactive": "Batteries and catalysts", "electronic-functional": "Electronic, optical, functional",
  "quantum-matter": "Magnetism, correlated matter", "atomistic-simulation": "DFT, atomistic simulation",
  "diffraction-spectroscopy": "Diffraction, spectroscopy", "microscopy": "Microscopy",
  "synthesis-labs": "Synthesis, lab automation", "materials-informatics": "Materials informatics",
  "cross-materials": "Broad reviews, benchmarks", "other-fields": "Chemistry, biology, other physics",
};
const QUESTION_SHORT = {
  "method-capability": "Can a method or agent do this task?", "model-evaluation": "How well do models perform?",
  "workflow-automation": "Automating an existing workflow", "ai-workflow-perspective": "Review or perspective on AI",
  "research-infrastructure": "A tool or data resource", "physical-findings": "A new physical or mathematical finding",
  "targeted-design": "Targeted design", "literature-findings": "Knowledge from published evidence",
};

const $ = (id) => document.getElementById(id);
const words = (s) => s.replaceAll("-", " ");
const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
let DATA, CODEBOOKS, shown = PAGE;

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

// ---------- state ----------
const CONTROLS = ["q", "field", "question", "use", "family", "from", "to", "sort"];
const CHECKS = ["code", "statement", "physical"];

function state() {
  const s = {};
  for (const id of CONTROLS) s[id] = $(id).value;
  for (const id of CHECKS) s[id] = $(id).checked;
  return s;
}

function writeHash() {
  const s = state(), p = new URLSearchParams();
  for (const id of CONTROLS) if (s[id] && !(id === "sort" && s[id] === "new")) p.set(id, s[id]);
  for (const id of CHECKS) if (s[id]) p.set(id, "1");
  const h = p.toString();
  history.replaceState(null, "", h ? "#" + h : location.pathname);
}

function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  for (const id of CONTROLS) if (p.has(id)) $(id).value = p.get(id);
  for (const id of CHECKS) $(id).checked = p.get(id) === "1";
}

// ---------- filtering ----------
function matches(r, s, terms, skip = null) {
  if (skip !== "field" && s.field && !r.field.includes(s.field)) return false;
  if (s.question && !r.question.includes(s.question)) return false;
  if (s.use && r.use !== s.use) return false;
  if (skip !== "family" && s.family && !(r.families || []).includes(s.family)) return false;
  if (s.from && r.date < s.from) return false;
  if (s.to && r.date > s.to) return false;
  if (s.code && !(r.code_urls && r.code_urls.length)) return false;
  if (s.statement && !r.ai_use_statement) return false;
  if (s.physical && !r.physical_world.some(Boolean)) return false;
  return terms.every((t) => r._text.includes(t));
}

function searchTerms(q) {
  return fold(q).split(/\s+/).filter(Boolean);
}

// ---------- tiles ----------
function tiles(rows, s) {
  const from = s.from || WINDOW[0], to = s.to || WINDOW[1];
  const days = Math.max(1, (Date.parse(to) - Date.parse(from)) / 864e5 + 1);
  const phys = rows.reduce((a, r) => a + r.physical_world.filter(Boolean).length / r.physical_world.length, 0);
  const pct = (a, b) => (b ? Math.round((100 * a) / b) + "%" : "–");
  const items = [
    [rows.length.toLocaleString("en"), "matching papers"],
    [(rows.length / days).toFixed(1), `per day, ${from} to ${to}`],
    [pct(phys, rows.length), "ask a question about the physical world"],
    [pct(rows.filter((r) => r.code_urls.length).length, rows.length), "link code"],
    [pct(rows.filter((r) => r.ai_use_statement).length, rows.length), "state their AI use"],
  ];
  $("tiles").replaceChildren(...items.map(([b, t]) => el("div", {}, el("b", { text: b }), el("span", { text: t }))));
}

// ---------- charts ----------
const tip = () => $("tip");
function showTip(evt, text) {
  const t = tip();
  t.textContent = text;
  t.hidden = false;
  t.style.left = Math.min(evt.clientX + 12, innerWidth - 330) + "px";
  t.style.top = evt.clientY + 14 + "px";
}
function hideTip() { tip().hidden = true; }

function timeChart(rows) {
  const start = Date.parse(WINDOW[0]), weeks = 27, counts = new Array(weeks).fill(0);
  for (const r of rows) {
    const w = Math.floor((Date.parse(r.date) - start) / (7 * 864e5));
    if (w >= 0 && w < weeks) counts[w]++;
  }
  const W = 420, H = 170, L = 28, B = 22, max = Math.max(4, ...counts);
  const step = Math.pow(10, Math.floor(Math.log10(max))) * (max / Math.pow(10, Math.floor(Math.log10(max))) > 5 ? 2 : 1);
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Matching records per week" });
  const y = (v) => H - B - ((H - B - 8) * v) / max, bw = (W - L) / weeks;
  for (let v = 0; v <= max; v += step) {
    svg.append(svgEl("line", { x1: L, x2: W, y1: y(v), y2: y(v), stroke: "var(--rule)" }));
    const t = svgEl("text", { x: L - 4, y: y(v) + 3, "text-anchor": "end" }); t.textContent = v; svg.append(t);
  }
  counts.forEach((c, i) => {
    const x = L + i * bw, d = new Date(start + i * 7 * 864e5).toISOString().slice(0, 10);
    const mark = svgEl("rect", { x: x + 1, width: Math.max(1, bw - 2), y: y(c), height: H - B - y(c), fill: "var(--blue)", rx: 1.5 });
    const hit = svgEl("rect", { x, width: bw, y: 0, height: H - B, class: "hit" });
    hit.addEventListener("mousemove", (e) => showTip(e, `Week of ${d}: ${c} record${c === 1 ? "" : "s"}`));
    hit.addEventListener("mouseleave", hideTip);
    svg.append(mark, hit);
  });
  for (const [m, label] of [["2026-05-01", "May"], ["2026-06-01", "Jun"], ["2026-07-01", "Jul"], ["2026-08-01", "Aug"], ["2026-09-01", "Sep"], ["2026-10-01", "Oct"]]) {
    const x = L + ((Date.parse(m) - start) / (7 * 864e5)) * bw;
    const t = svgEl("text", { x, y: H - 6, "text-anchor": "middle" }); t.textContent = label; svg.append(t);
  }
  $("chart-time").replaceChildren(svg);
}

function barChart(target, entries, selected, onPick, unit) {
  // entries: [{id, label, value, group?}]
  const W = 440, row = 17, L = 236, top = 4;
  let groups = 0, last = null;
  for (const e of entries) if (e.group && e.group !== last) { groups++; last = e.group; }
  const H = top + entries.length * row + groups * 16 + 4, max = Math.max(1, ...entries.map((e) => e.value));
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" });
  let yy = top; last = null;
  for (const e of entries) {
    if (e.group && e.group !== last) {
      const g = svgEl("text", { x: 0, y: yy + 11, "font-weight": 600 }); g.textContent = e.group; svg.append(g);
      yy += 16; last = e.group;
    }
    const w = ((W - L - 34) * e.value) / max;
    const label = svgEl("text", { x: L - 6, y: yy + 12, "text-anchor": "end", class: "label" }); label.textContent = e.label;
    const pick = () => { hideTip(); onPick(selected === e.id ? "" : e.id); };
    const g = svgEl("g", { class: "row" });
    // The transparent hit area is drawn last, on top of the bar and its labels, so that it receives the clicks.
    const hit = svgEl("rect", { x: 0, y: yy, width: W, height: row, class: "hit", tabindex: 0, role: "button",
      "aria-pressed": String(selected === e.id), "aria-label": `${e.label}: ${Math.round(e.value)} ${unit}. ${selected === e.id ? "Clear" : "Filter by"} this.` });
    const mark = svgEl("rect", { x: L, y: yy + 3, width: Math.max(0, w), height: row - 6, rx: 2, fill: e.color || "var(--blue)",
      class: selected ? (selected === e.id ? "mark sel" : "mark dim") : "mark" });
    const val = svgEl("text", { x: L + w + 4, y: yy + 12 }); val.textContent = Math.round(e.value);
    hit.addEventListener("mousemove", (ev) => showTip(ev, `${e.label}: ${Math.round(e.value)} ${unit}. Click to ${selected === e.id ? "clear" : "filter"}.`));
    hit.addEventListener("mouseleave", hideTip);
    hit.addEventListener("click", pick);
    hit.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(); } });
    g.append(label, mark, val, hit);
    svg.append(g);
    yy += row;
  }
  $(target).replaceChildren(svg);
}

function fieldChart(rows, s) {
  const counts = {};
  for (const r of rows) for (const f of r.field) counts[f] = (counts[f] || 0) + 1 / r.field.length;
  const entries = CODEBOOKS.field.map((c) => ({ id: c.id, label: FIELD_SHORT[c.id] || c.name, value: counts[c.id] || 0, group: c.group }));
  barChart("chart-field", entries, s.field, (v) => { $("field").value = v; update(); }, "papers");
}

function familyChart(rows, s) {
  const counts = {};
  for (const r of rows) for (const f of r.families || []) counts[f] = (counts[f] || 0) + 1;
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([id, value]) => ({ id, label: id, value }));
  if (!entries.length) { $("chart-family").replaceChildren(el("p", { class: "hint", text: "No papers match." })); return; }
  barChart("chart-family", entries, s.family, (v) => { $("family").value = v; update(); }, "papers run a model of this developer");
}

// ---------- list ----------
function highlight(text, terms) {
  if (!terms.length) return document.createTextNode(text);
  const frag = document.createDocumentFragment(), low = fold(text);
  let i = 0;
  while (i < text.length) {
    let best = -1, len = 0;
    for (const t of terms) { const j = low.indexOf(t, i); if (j >= 0 && (best < 0 || j < best)) { best = j; len = t.length; } }
    if (best < 0) { frag.append(text.slice(i)); break; }
    frag.append(text.slice(i, best), el("mark", { text: text.slice(best, best + len) }));
    i = best + len;
  }
  return frag;
}

function item(r, terms) {
  const authors = r.authors.length > 8 ? r.authors.slice(0, 8).join(", ") + ` et al. (${r.authors.length} authors)` : r.authors.join(", ");
  const chips = el("div", { class: "chips" });
  for (const f of r.field) chips.append(el("span", { class: "chip", text: FIELD_SHORT[f] || f }));
  r.question.forEach((q, i) => chips.append(el("span", { class: "chip" + (r.physical_world[i] ? " phys" : ""), text: QUESTION_SHORT[q] || q })));
  for (const f of r.families || []) chips.append(el("span", { class: "chip", text: f }));
  const meta = [r.date, "arXiv " + r.id.split(":")[1] + " [" + r.category + "]", words(r.use)];
  const dl = el("dl");
  const add = (k, v) => { if (v) dl.append(el("dt", { text: k }), el("dd", {}, v)); };
  add("Scope", words(r.scope));
  add("Paper kind", words(r.kind));
  add("Agent form", words(r.agent_form));
  add("Field", r.field.map((f) => FIELD_SHORT[f] || f).join(" / ") + (r.field.length > 1 ? " (coders differ)" : ""));
  add("Question", r.question.map((q) => QUESTION_SHORT[q] || q).join(" / ") + (r.question.length > 1 ? " (coders differ)" : ""));
  add("Models run", r.models.join(", ") || "none named");
  add("Harness", r.harness);
  add("AI-use statement", r.ai_use_statement ? "yes" : "no");
  if (r.model_lag_days != null) add("Newest model's age at submission", r.model_lag_days + " days");
  if (r.code_urls.length) {
    const span = el("span");
    r.code_urls.forEach((u, i) => { if (i) span.append(", "); span.append(el("a", { href: u, text: u.replace(/^https?:\/\//, "") })); });
    add("Code", span);
  }
  return el("li", {},
    el("a", { class: "t", href: r.url }, highlight(r.title, terms)),
    el("div", { class: "au" }, highlight(authors, terms)),
    el("div", { class: "meta", text: meta.join(" · ") }),
    chips,
    el("details", {}, el("summary", { text: "Abstract and labels" }), el("p", {}, highlight(r.abstract || "No abstract available.", terms)), dl));
}

function list(rows, terms, sort) {
  const sorted = rows.slice();
  if (sort === "old") sorted.reverse();
  if (sort === "title") sorted.sort((a, b) => a.title.localeCompare(b.title));
  $("count").textContent = `${rows.length.toLocaleString("en")} paper${rows.length === 1 ? "" : "s"}`;
  $("list").replaceChildren(...sorted.slice(0, shown).map((r) => item(r, terms)));
  $("more").hidden = rows.length <= shown;
  $("more").textContent = `Show more (${Math.min(PAGE, rows.length - shown)} of ${rows.length - shown} remaining)`;
  return sorted;
}

// ---------- CSV ----------
let current = [];
function csv() {
  const cols = ["id", "date", "category", "title", "authors", "url", "doi", "scope", "use", "kind", "field", "question", "models", "harness", "code_urls", "ai_use_statement"];
  const cell = (v) => {
    const s = Array.isArray(v) ? v.join("; ") : v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replaceAll('"', '""') + '"' : s;
  };
  const text = [cols.join(",")].concat(current.map((r) => cols.map((c) => cell(r[c])).join(","))).join("\n");
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type: "text/csv" })), download: "papers-to-end-all-papers.csv" });
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---------- wiring ----------
function update(resetPage = true) {
  if (resetPage) shown = PAGE;
  const s = state(), terms = searchTerms(s.q);
  const rows = DATA.filter((r) => matches(r, s, terms));
  tiles(rows, s);
  timeChart(rows);
  fieldChart(DATA.filter((r) => matches(r, s, terms, "field")), s);
  familyChart(DATA.filter((r) => matches(r, s, terms, "family")), s);
  current = list(rows, terms, s.sort);
  writeHash();
}

function options(id, entries, allLabel) {
  const sel = $(id);
  sel.replaceChildren(el("option", { value: "", text: allLabel }));
  let group = null, parent = sel;
  for (const e of entries) {
    if (e.group && e.group !== group) { group = e.group; parent = el("optgroup", { label: group }); sel.append(parent); }
    parent.append(el("option", { value: e.id, text: e.label }));
  }
}

async function main() {
  const res = await fetch("data/records.json");
  const data = await res.json();
  CODEBOOKS = data.codebooks;
  DATA = data.records;
  for (const r of DATA) r._text = fold([r.title, r.abstract, r.authors.join(" ")].join(" "));
  options("field", CODEBOOKS.field.map((c) => ({ id: c.id, label: FIELD_SHORT[c.id] || c.name, group: c.group })), "All fields");
  options("question", CODEBOOKS.question.map((c) => ({ id: c.id, label: QUESTION_SHORT[c.id] || c.name,
    group: c.physical_world ? "About the physical world" : "About the AI or workflow" })), "All questions");
  const uses = [...new Set(DATA.map((r) => r.use))].sort();
  options("use", uses.map((u) => ({ id: u, label: words(u) })), "All uses");
  const fams = {};
  for (const r of DATA) for (const f of r.families || []) fams[f] = (fams[f] || 0) + 1;
  options("family", Object.keys(fams).sort((a, b) => fams[b] - fams[a]).map((f) => ({ id: f, label: f })), "Any developer");
  readHash();
  for (const id of CONTROLS) $(id).addEventListener(id === "q" ? "input" : "change", () => update());
  for (const id of CHECKS) $(id).addEventListener("change", () => update());
  $("reset").addEventListener("click", () => {
    for (const id of CONTROLS) $(id).value = id === "sort" ? "new" : "";
    for (const id of CHECKS) $(id).checked = false;
    update();
  });
  $("more").addEventListener("click", () => { shown += PAGE; update(false); });
  $("csv").addEventListener("click", csv);
  update();
}

main();
