"use strict";

const SEG_COLORS = {
  "Champion": "#138a4e", "Loyal": "#0e7c66", "Potential Loyalist": "#2e7d32",
  "At Risk": "#e67e22", "About to Sleep": "#b9770e", "Hibernating / Lost": "#8a8f8d",
};
const FLAG_STYLE = {
  CHURN_RISK: ["#fdecea", "#a02020"], STALLED: ["#fff1e2", "#9a5a12"],
  DECLINING: ["#fff7e0", "#8a6512"], DORMANT_PROSPECT: ["#e8f0fb", "#27548f"],
  OCCASIONAL: ["#eef2f0", "#566", ], NONE: null,
};

let REASONS = [];
let state = { code: null, actions: [], marks: {} };

const $ = (s, r = document) => r.querySelector(s);
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };
const money = (v) => v == null ? "" : "$" + Math.round(v).toLocaleString();
const esc = (s) => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function getJSON(url) { const r = await fetch(url); return r.json(); }
async function postJSON(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return r.json();
}

let toastTimer;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.hidden = true, 2200);
}

/* ---------- screen 1: customers ---------- */
async function loadCustomers() {
  const list = await getJSON("/api/customers");
  const root = $("#customer-list"); root.innerHTML = "";
  list.forEach(c => {
    const seg = SEG_COLORS[c.segment] || "#999";
    const card = el(`<button class="cust-card" style="--seg:${seg}">
      <div class="cust-card__name">${esc(c.name)}</div>
      <div class="cust-card__row">
        <span class="pill pill--seg" style="--seg:${seg}">${esc(c.segment)}</span>
        ${flagPill(c)}
        ${c.balance > 0 ? `<span class="pill pill--bal">💰 owes ${money(c.balance)}</span>` : ""}
        <span class="pill pill--rfm">RFM ${c.rfm}</span>
      </div></button>`);
    card.addEventListener("click", () => openCustomer(c.code));
    root.appendChild(card);
  });
}

function flagPill(c) {
  const st = FLAG_STYLE[c.flag_key];
  if (!st || !c.flag) return "";
  const short = c.flag.split("—")[0].trim();
  return `<span class="pill pill--flag" style="--flagbg:${st[0]};--flagink:${st[1]}">⚠ ${esc(short)}</span>`;
}

/* ---------- screen 2: actions ---------- */
async function openCustomer(code) {
  state.code = code;
  showScreen("actions");
  $("#action-cards").innerHTML = `<div class="loading">Loading…</div>`;
  const payload = await getJSON("/api/customer/" + code);
  renderActions(payload);
}

function renderActions(payload) {
  const c = payload.customer;
  $("#cust-name").textContent = c.name;
  $("#cust-snapshot").textContent = c.snapshot;

  const seg = SEG_COLORS[c.segment] || "#999";
  $("#cust-badges").innerHTML =
    `<span class="pill pill--seg" style="--seg:${seg}">${esc(c.segment)}</span>` +
    flagPill(c) +
    (c.balance > 0 ? `<span class="pill pill--bal">💰 owes ${money(c.balance)}</span>` : `<span class="pill pill--ok">✅ paid up</span>`);

  // learned chips
  const learned = $("#learned");
  if (c.learned && c.learned.length) {
    learned.hidden = false;
    $("#learned-chips").innerHTML = c.learned.map(ch => `<span class="chip">${ch.icon} ${esc(ch.label)}</span>`).join("");
  } else { learned.hidden = true; $("#learned-chips").innerHTML = ""; }

  // cards
  state.actions = payload.actions;
  state.marks = {};
  payload.actions.forEach(a => { if (a.accepted) state.marks[a.id] = { decision: "good", reasons: [], note: "" }; });

  const root = $("#action-cards"); root.innerHTML = "";
  if (!payload.actions.length) {
    root.appendChild(el(`<div class="empty"><span class="big">🎉</span>No more ideas to show — you’ve been through them all. Tap ↺ Start over to reset.</div>`));
    return;
  }
  payload.actions.forEach((a, i) => root.appendChild(buildCard(a, i)));
  updateNextBtn();
}

function buildCard(a, i) {
  const products = (a.products || []).map(p => {
    const cls = p.stock === "In stock" ? "in" : (p.stock === "Backorder" ? "back" : "");
    return `<div class="product">
      <span class="product__dot ${cls}"></span>
      <span class="product__code">${esc(p.code)}</span>
      <span class="product__desc">${esc(p.desc)}</span>
      <span class="product__price">${money(p.price)}</span>
    </div>`;
  }).join("");

  const ribbon = a.incentive ? `<div class="ribbon">🎁 ${esc(a.incentive)} <b>(needs approval)</b></div>` : "";
  const accepted = a.accepted;

  const card = el(`<article class="card ${accepted ? "is-good" : ""}" data-id="${a.id}">
    <div class="card__top">
      <span class="card__num">${i + 1}</span>
      <span class="kindpill">${esc(a.kind)}</span>
      <span class="tick">${accepted ? "✅" : ""}</span>
    </div>
    <h3 class="card__title">${esc(a.title)}</h3>
    <p class="card__detail">${esc(a.detail)}</p>
    ${products ? `<div class="products">${products}</div>` : ""}
    ${ribbon}
    <div class="choices">
      <button class="choice choice--good ${accepted ? "sel" : ""}">👍 Good</button>
      <button class="choice choice--no">👎 No</button>
    </div>
    <div class="reasons">
      <div class="reasons__q">Why not? (tap any)</div>
      <div class="reason-grid">${REASONS.map(r => `<button class="reason" data-r="${r.name}"><span class="ic">${r.icon}</span>${esc(r.label)}</button>`).join("")}</div>
      <textarea class="note" rows="2" placeholder="Add a note (optional)…"></textarea>
    </div>
  </article>`);

  const good = $(".choice--good", card), no = $(".choice--no", card);
  good.addEventListener("click", () => setDecision(card, a.id, "good"));
  no.addEventListener("click", () => setDecision(card, a.id, "no"));
  card.querySelectorAll(".reason").forEach(rb =>
    rb.addEventListener("click", () => toggleReason(card, a.id, rb)));
  $(".note", card).addEventListener("input", e => {
    if (state.marks[a.id]) state.marks[a.id].note = e.target.value;
  });
  return card;
}

function setDecision(card, id, decision) {
  state.marks[id] = state.marks[id] || { decision: null, reasons: [], note: "" };
  state.marks[id].decision = decision;
  card.classList.toggle("is-good", decision === "good");
  card.classList.toggle("is-no", decision === "no");
  card.classList.toggle("show-reasons", decision === "no");
  $(".choice--good", card).classList.toggle("sel", decision === "good");
  $(".choice--no", card).classList.toggle("sel", decision === "no");
  $(".tick", card).textContent = decision === "good" ? "✅" : (decision === "no" ? "🚫" : "");
  updateNextBtn();
}

function toggleReason(card, id, btn) {
  const r = btn.dataset.r;
  const m = state.marks[id] = state.marks[id] || { decision: "no", reasons: [], note: "" };
  const idx = m.reasons.indexOf(r);
  if (idx >= 0) { m.reasons.splice(idx, 1); btn.classList.remove("sel"); }
  else { m.reasons.push(r); btn.classList.add("sel"); }
}

function updateNextBtn() {
  const anyNo = Object.values(state.marks).some(m => m.decision === "no");
  const btn = $("#next-btn");
  btn.textContent = anyNo ? "✨ Show me 3 better" : "✅ Save these 3";
}

async function submitRound() {
  const marks = state.marks;
  const decided = Object.entries(marks).filter(([, m]) => m.decision);
  if (!decided.length) { toast("Tap 👍 or 👎 on each one first"); return; }

  const accepted = [], rejections = [];
  for (const [id, m] of decided) {
    if (m.decision === "good") accepted.push(id);
    else rejections.push({ id, reasons: m.reasons.length ? m.reasons : ["WANT_OTHER"], note: m.note || "" });
  }
  $("#next-btn").disabled = true;
  const payload = await postJSON(`/api/customer/${state.code}/feedback`, { accepted, rejections });
  $("#next-btn").disabled = false;
  renderActions(payload);
  toast(rejections.length ? "Found you some better ones 👇" : "Saved ✓");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function resetCustomer() {
  const payload = await postJSON(`/api/customer/${state.code}/reset`, {});
  renderActions(payload);
  toast("Started over for this customer");
}

/* ---------- nav ---------- */
function showScreen(name) {
  $("#screen-list").classList.toggle("is-active", name === "list");
  $("#screen-actions").classList.toggle("is-active", name === "actions");
  window.scrollTo(0, 0);
}

function openFromHash() {
  const m = (location.hash || "").match(/c=([A-Za-z0-9]+)/);
  if (m) openCustomer(m[1]);
}

async function init() {
  REASONS = await getJSON("/api/reasons");
  await loadCustomers();
  $("#back-btn").addEventListener("click", () => { location.hash = ""; showScreen("list"); });
  $("#next-btn").addEventListener("click", submitRound);
  $("#reset-btn").addEventListener("click", resetCustomer);
  window.addEventListener("hashchange", openFromHash);
  openFromHash();  // deep-link support: /#c=MJ001 opens that customer directly
}

init();
