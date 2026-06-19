"use strict";

/* Plain-language translation — reps never see RFM/segment jargon. */
const SEGMENT_PLAIN = {
  "Champion":            { t: "Top customer",  em: "⭐", tone: "good" },
  "Loyal":               { t: "Loyal",         em: "💚", tone: "good" },
  "Potential Loyalist":  { t: "Growing",       em: "🌱", tone: "good" },
  "At Risk":             { t: "At risk",       em: "⚠️", tone: "warn" },
  "About to Sleep":      { t: "Going quiet",   em: "😴", tone: "warn" },
  "Hibernating / Lost":  { t: "Gone cold",     em: "❄️", tone: "cold" },
};
const FLAG_PLAIN = {
  CHURN_RISK:       { t: "May be leaving us",      tone: "danger" },
  STALLED:          { t: "Gone quiet on us",       tone: "warn" },
  DECLINING:        { t: "Slowing down",           tone: "warn" },
  DORMANT_PROSPECT: { t: "Keen but hasn’t bought", tone: "info" },
  OCCASIONAL:       { t: "Buys now & then",        tone: "neutral" },
  NONE:             null,
};
const KIND_PLAIN = {
  "Retention": "Save the account", "Upsell": "Add to their order",
  "New category": "Try something new", "Relationship": "Build trust",
  "Commercial terms": "New deal structure", "Equipment": "Sell equipment",
  "General": "Idea",
};
const TONE_RANK = { danger: 5, warn: 4, info: 3, cold: 2, good: 1, neutral: 0 };

let REASONS = [];
let state = { code: null, actions: [], marks: {} };

const $ = (s, r = document) => r.querySelector(s);
const el = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content.firstChild; };
const esc = (s) => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const money = (v) => v == null ? "" : "$" + Math.round(v).toLocaleString();
const moneyShort = (v) => v == null ? "" : "$" + new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(v);
const daysPhrase = (n) => n == null ? "—" : n === 0 ? "today" : n === 1 ? "yesterday" : `${n} days ago`;

async function getJSON(u) { return (await fetch(u)).json(); }
async function postJSON(u, b) {
  return (await fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) })).json();
}

let toastTimer;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 2300);
}

function statusTags(c) {
  const seg = SEGMENT_PLAIN[c.segment] || { t: c.segment, em: "", tone: "neutral" };
  const tags = [`<span class="tag tag--${seg.tone}"><span class="em">${seg.em}</span>${esc(seg.t)}</span>`];
  const flag = FLAG_PLAIN[c.flag_key];
  if (flag) tags.push(`<span class="tag tag--${flag.tone}">${esc(flag.t)}</span>`);
  if (c.balance > 0) tags.push(`<span class="tag tag--money">💰 owes ${money(c.balance)}</span>`);
  return { tags, seg, flag };
}

/* ---------- screen 1 ---------- */
async function loadCustomers() {
  const list = await getJSON("/api/customers");
  const root = $("#customer-list"); root.innerHTML = "";
  list.forEach((c, i) => {
    const { tags, seg, flag } = statusTags(c);
    const accentTone = (flag && TONE_RANK[flag.tone] >= TONE_RANK[seg.tone]) ? flag.tone : seg.tone;
    const card = el(`<button class="cust" style="--accent:var(--${accentTone});animation-delay:${i * 45}ms">
      <div class="cust__main">
        <div class="cust__name">${esc(c.name)}</div>
        <div class="cust__row">${tags.join("")}</div>
      </div>
      <span class="cust__chev">›</span>
    </button>`);
    card.addEventListener("click", () => openCustomer(c.code));
    root.appendChild(card);
  });
}

/* ---------- screen 2 ---------- */
async function openCustomer(code) {
  state.code = code;
  showScreen("actions");
  $("#action-cards").innerHTML = `<div class="loading"><span class="spinner"></span> Loading…</div>`;
  renderActions(await getJSON("/api/customer/" + code));
}

function renderActions(payload) {
  const c = payload.customer;
  const seg = SEGMENT_PLAIN[c.segment] || { t: c.segment, em: "" };
  const flag = FLAG_PLAIN[c.flag_key];

  $("#cust-name").textContent = c.name;
  $("#cust-status").textContent = `${seg.em} ${seg.t}` + (flag ? ` · ${flag.t}` : "");

  // story
  $("#cust-kind").textContent = c.kind || "";
  $("#cust-hooks").innerHTML = (c.hooks || []).map(h => `<li>${esc(h)}</li>`).join("");
  const meta = [];
  meta.push(`<span class="metachip">Last order <b>${daysPhrase(c.last_order_days)}</b></span>`);
  meta.push(`<span class="metachip"><b>${c.orders}</b> orders / 2 yrs</span>`);
  if (c.spend) meta.push(`<span class="metachip"><b>${moneyShort(c.spend)}</b> spend</span>`);
  if (c.balance > 0) meta.push(`<span class="metachip" style="color:var(--danger)">💰 owes <b>${money(c.balance)}</b></span>`);
  if (c.next_contact) meta.push(`<span class="metachip">Next visit <b>${esc(c.next_contact)}</b></span>`);
  if (c.top_groups && c.top_groups.length) meta.push(`<span class="metachip">Usually buys <b>${esc(c.top_groups.slice(0, 3).join(", "))}</b></span>`);
  $("#cust-meta").innerHTML = meta.join("");

  // learned
  const learned = $("#learned");
  if (c.learned && c.learned.length) {
    learned.hidden = false;
    $("#learned-chips").innerHTML = c.learned.map(ch => `<span class="chip">${ch.icon} ${esc(ch.label)}</span>`).join("");
  } else learned.hidden = true;

  // cards
  state.actions = payload.actions;
  state.marks = {};
  payload.actions.forEach(a => { if (a.accepted) state.marks[a.id] = { decision: "good", reasons: [], note: "" }; });

  const root = $("#action-cards"); root.innerHTML = "";
  if (!payload.actions.length) {
    root.appendChild(el(`<div class="empty"><span class="big">🎉</span>That’s every idea I’ve got for now. Tap <b>↺ Start over</b> above to reset.</div>`));
  } else {
    payload.actions.forEach((a, i) => root.appendChild(buildCard(a, i)));
  }
  updateNextBtn();
}

function buildCard(a, i) {
  const products = (a.products || []).map(p => {
    const inStock = p.stock === "In stock";
    const stockCls = inStock ? "in" : (p.stock === "Backorder" ? "back" : "");
    const stockLbl = inStock ? `<small>in stock</small>` : (p.stock === "Backorder" ? `<small class="back">backorder</small>` : "");
    return `<div class="product">
      <span class="product__dot ${stockCls}"></span>
      <div class="product__body">
        <div class="product__desc">${esc(p.desc)}</div>
        <div class="product__code">${esc(p.code)}</div>
      </div>
      <div class="product__price">${money(p.price)}${stockLbl}</div>
    </div>`;
  }).join("");

  const offer = a.incentive
    ? `<div class="offer"><span class="offer__ic">🎁</span><div>${esc(a.incentive.replace(/^PROPOSED:\s*/i, ""))} <b>· needs manager OK</b></div></div>`
    : "";
  const kind = KIND_PLAIN[a.kind] || a.kind;
  const acc = a.accepted;

  const card = el(`<article class="card ${acc ? "is-good" : ""}" data-id="${a.id}">
    <div class="card__top">
      <span class="card__num">Pitch ${i + 1}</span>
      <span class="kindtag">${esc(kind)}</span>
      <span class="tick">${acc ? "✅" : ""}</span>
    </div>
    <h3 class="card__title">${esc(a.title)}</h3>
    <p class="card__detail">${esc(a.detail)}</p>
    ${products ? `<div class="products">${products}</div>` : ""}
    ${offer}
    <div class="choices">
      <button class="choice choice--good ${acc ? "sel" : ""}">👍 Good</button>
      <button class="choice choice--no">👎 No</button>
    </div>
    <div class="reasons">
      <div class="reasons__q">Why not? (tap any that fit)</div>
      <div class="reason-grid">${REASONS.map(r => `<button class="reason" data-r="${r.name}"><span class="ic">${r.icon}</span>${esc(r.label)}</button>`).join("")}</div>
      <textarea class="note" rows="2" placeholder="Add a note (optional)…"></textarea>
    </div>
  </article>`);

  $(".choice--good", card).addEventListener("click", () => setDecision(card, a.id, "good"));
  $(".choice--no", card).addEventListener("click", () => setDecision(card, a.id, "no"));
  card.querySelectorAll(".reason").forEach(rb => rb.addEventListener("click", () => toggleReason(a.id, rb)));
  $(".note", card).addEventListener("input", e => { if (state.marks[a.id]) state.marks[a.id].note = e.target.value; });
  return card;
}

function setDecision(card, id, decision) {
  const m = state.marks[id] = state.marks[id] || { decision: null, reasons: [], note: "" };
  m.decision = decision;
  card.classList.toggle("is-good", decision === "good");
  card.classList.toggle("is-no", decision === "no");
  card.classList.toggle("show-reasons", decision === "no");
  $(".choice--good", card).classList.toggle("sel", decision === "good");
  $(".choice--no", card).classList.toggle("sel", decision === "no");
  $(".tick", card).textContent = decision === "good" ? "✅" : (decision === "no" ? "🚫" : "");
  updateNextBtn();
}

function toggleReason(id, btn) {
  const m = state.marks[id] = state.marks[id] || { decision: "no", reasons: [], note: "" };
  const r = btn.dataset.r, idx = m.reasons.indexOf(r);
  if (idx >= 0) { m.reasons.splice(idx, 1); btn.classList.remove("sel"); }
  else { m.reasons.push(r); btn.classList.add("sel"); }
}

function updateNextBtn() {
  const anyNo = Object.values(state.marks).some(m => m.decision === "no");
  const btn = $("#next-btn");
  btn.textContent = anyNo ? "✨ Show me 3 better" : "✅ Save these 3";
  btn.classList.toggle("bigbtn--save", !anyNo);
}

async function submitRound() {
  const decided = Object.entries(state.marks).filter(([, m]) => m.decision);
  if (!decided.length) { toast("Tap 👍 or 👎 on each one first"); return; }
  const accepted = [], rejections = [];
  for (const [id, m] of decided) {
    if (m.decision === "good") accepted.push(id);
    else rejections.push({ id, reasons: m.reasons.length ? m.reasons : ["WANT_OTHER"], note: m.note || "" });
  }
  const btn = $("#next-btn"); btn.disabled = true;
  const payload = await postJSON(`/api/customer/${state.code}/feedback`, { accepted, rejections });
  btn.disabled = false;
  renderActions(payload);
  $(".screen__body", $("#screen-actions")).scrollIntoView({ block: "start" });
  window.scrollTo({ top: 0, behavior: "smooth" });
  toast(rejections.length ? "Found you some better ones 👇" : "Saved ✓ — locked in");
}

async function resetCustomer() {
  renderActions(await postJSON(`/api/customer/${state.code}/reset`, {}));
  toast("Started fresh for this customer");
}

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
  openFromHash();
}

init();
