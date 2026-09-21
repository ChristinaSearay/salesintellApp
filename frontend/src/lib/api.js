// API client for the Searay rep app.
//
// It calls the Python engine through the /api proxy (see next.config.mjs) and
// ADAPTS the raw responses into the friendly "view model" the UI renders
// (plain-language status, stat tiles, pitch cards). This is the same shape used
// in V0_PROMPT.md — so a UI generated in v0 binds to this directly.

const SEGMENT = {
  "Champion":            { em: "⭐", label: "Top customer", tone: "good" },
  "Loyal":               { em: "💚", label: "Loyal",        tone: "good" },
  "Potential Loyalist":  { em: "🌱", label: "Growing",      tone: "good" },
  "At Risk":             { em: "⚠️", label: "At risk",      tone: "warn" },
  "About to Sleep":      { em: "😴", label: "Going quiet",  tone: "warn" },
  "Hibernating / Lost":  { em: "❄️", label: "Gone cold",    tone: "cold" },
};
const FLAG = {
  CHURN_RISK:       { icon: "👋", label: "May be leaving us",      tone: "danger" },
  STALLED:          { icon: "😶", label: "Gone quiet on us",       tone: "warn" },
  DECLINING:        { icon: "📉", label: "Slowing down",           tone: "warn" },
  DORMANT_PROSPECT: { icon: "👀", label: "Keen but hasn’t bought", tone: "info" },
  OCCASIONAL:       { icon: "🛒", label: "Buys now & then",        tone: "neutral" },
  NONE:             null,
};
const KIND = {
  "Retention": "Save the account", "Reorder": "Due to reorder",
  "Upsell": "Add to their order",
  "New category": "Try something new", "Relationship": "Build trust",
  "Commercial terms": "New deal structure", "Equipment": "Sell equipment",
  "General": "Idea",
};

const money = (v) => (v == null ? "" : "$" + Math.round(v).toLocaleString());
const moneyShort = (v) => (v == null ? "" : "$" + new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(v));
const daysPhrase = (n) => (n == null ? "—" : n === 0 ? "today" : n === 1 ? "yesterday" : `${n} days ago`);

async function get(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}
async function post(url, body) {
  let r;
  try {
    r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  } catch {
    // The browser's own wording for this is "Load failed", which tells a rep
    // nothing. It's the engine being unreachable — usually a restart.
    throw new Error("Couldn’t reach the engine — it may be restarting. Try again in a moment.");
  }
  if (!r.ok) {
    let msg = `${url} → ${r.status}`;
    try { const j = await r.json(); if (j?.error) msg = j.error; } catch {}
    throw new Error(msg);
  }
  return r.json();
}
const whenPhrase = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-AU", { day: "numeric", month: "short" }) + " " +
    d.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit" });
};

export function toAccount(c) {
  const seg = SEGMENT[c.segment] || { em: "•", label: c.segment, tone: "neutral" };
  const alerts = [];
  const flag = FLAG[c.flag_key];
  if (flag) alerts.push({ icon: flag.icon, label: flag.label, tone: flag.tone });
  if (c.balance > 0) alerts.push({ icon: "💰", label: `Owes ${money(c.balance)}`, tone: "danger" });
  // Shape matches v0's components: status as a string + a top-level tone.
  const meta = [
    c.spend != null ? `${moneyShort(c.spend)} · 2yr` : "",
    c.last_order_days != null ? `last order ${daysPhrase(c.last_order_days)}` : "",
  ].filter(Boolean).join(" · ");
  return { code: c.code, name: c.name, emoji: seg.em, status: seg.label, tone: seg.tone, alerts, meta };
}

// Case-insensitive match on customer name or code (accounts search).
export function matchesAccount(account, query) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return account.name.toLowerCase().includes(q) || account.code.toLowerCase().includes(q);
}

// Why a customer is in the "needs attention" queue (AttentionReason in constants/attention.py).
export const REASON = {
  OVERDUE: "overdue", NO_RECENT_NOTE: "no_recent_note",
  RECENTLY_NOTED: "recently_noted", MUTED: "muted",
};

// The "needs attention" queue: account cards plus why each customer is there.
function toAttention(payload) {
  return {
    queue: (payload.queue || []).map((c) => ({
      ...toAccount(c),
      why: c.why || "",
      reason: c.reason,
      lastNote: c.last_note
        ? { text: c.last_note.text, when: daysPhrase(c.last_note.days_ago) }
        : null,
    })),
    overdue: payload.overdue || 0,
    notedRecently: payload.noted_recently || 0,
    muted: payload.muted || 0,
    snoozeDays: payload.snooze_days || 0,
  };
}

function toPitch(a) {
  return {
    id: a.id,
    accepted: !!a.accepted,
    badge: KIND[a.kind] || a.kind,
    title: a.title,
    blurb: a.detail,
    products: (a.products || []).map((p) => ({
      name: p.desc, code: p.code, price: money(p.price), inStock: p.stock === "In stock",
    })),
    offer: a.incentive ? a.incentive.replace(/^PROPOSED:\s*/i, "") + " — needs manager OK" : null,
  };
}

function toPrep(payload) {
  const c = payload.customer;
  const contact = c.contact || {};
  return {
    code: c.code,
    account: toAccount(c),
    contact: { name: contact.name || "", phone: contact.phone || "", email: contact.email || "" },
    stats: [
      { label: "Spend · 2yr", value: moneyShort(c.spend) },
      { label: "Last order", value: daysPhrase(c.last_order_days) },
      { label: "Orders · 2yr", value: String(c.orders) },
    ],
    // Live WhatsApp bullets come first (tagged), then the meeting-notes baseline.
    highlights: (c.hook_items || (c.hooks || []).map((h) => ({ text: h, live: false })))
      .slice(0, 5)
      .map((h) => ({ icon: h.live ? "💬" : "✦", label: h.text, live: !!h.live })),
    advice: c.advice || "",
    intelUpdated: whenPhrase(c.intel_updated),
    intelCount: c.intel_count || 0,
    story: c.kind || "",
    nextContact: c.next_contact || "",
    topGroups: c.top_groups || [],
    balance: c.balance || 0,
    learned: c.learned || [],
    muted: !!c.is_muted,
    mutedNote: c.muted || "",
    pitches: (payload.actions || []).map(toPitch),
    exhausted: !!payload.exhausted,
  };
}

export const api = {
  getAccounts: async () => (await get("/api/customers")).map(toAccount),
  getAttention: async () => toAttention(await get("/api/attention")),
  // Saving a note sends the customer to the back of the queue → refreshed queue.
  // mute = "do not alert again": off the queue until they order (utils/mute.py).
  saveNote: async (code, text, mute = false) =>
    toAttention(await post(`/api/attention/${code}/note`, { text, mute })),
  unmute: async (code) => toPrep(await post(`/api/attention/${code}/unmute`, {})),
  getReasons: () => get("/api/reasons"),
  getPrep: async (code) => toPrep(await get(`/api/customer/${code}`)),
  // rejections: [{ id, reasons: [REASON_NAME], note }]
  sendFeedback: async (code, accepted, rejections) =>
    toPrep(await post(`/api/customer/${code}/feedback`, { accepted, rejections })),
  reset: async (code) => toPrep(await post(`/api/customer/${code}/reset`, {})),
  // Live intel (WhatsApp dumps → summarised updates)
  summarise: async (text) => (await post("/api/intel/summarise", { text, source: "whatsapp" })).proposals,
  getIntel: async (code) => (await get(`/api/intel/${code}`)).updates,
  saveIntel: async (code, proposal) => toPrep(await post(`/api/intel/${code}`, proposal)),
  deleteIntel: async (code, id) => toPrep(await post(`/api/intel/${code}/delete`, { id })),

  // A business we visited that isn't in Unleashed yet. checkProspect only
  // looks (and returns possible duplicates); createProspect writes it.
  checkProspect: (name) => post("/api/prospects/check", { name }),
  createProspect: (prospect) => post("/api/prospects/create", prospect),
};

export const PROSPECT_OUTCOME = {
  NEW: "new",
  POSSIBLE_DUPLICATE: "possible_duplicate",
  EXISTS: "exists",
};
export { whenPhrase };
