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
  "Retention": "Save the account", "Upsell": "Add to their order",
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
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

export function toAccount(c) {
  const seg = SEGMENT[c.segment] || { em: "•", label: c.segment, tone: "neutral" };
  const alerts = [];
  const flag = FLAG[c.flag_key];
  if (flag) alerts.push({ icon: flag.icon, label: flag.label, tone: flag.tone });
  if (c.balance > 0) alerts.push({ icon: "💰", label: `Owes ${money(c.balance)}`, tone: "danger" });
  // Shape matches v0's components: status as a string + a top-level tone.
  return { code: c.code, name: c.name, emoji: seg.em, status: seg.label, tone: seg.tone, alerts };
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
  return {
    code: c.code,
    account: toAccount(c),
    stats: [
      { label: "Spend · 2yr", value: moneyShort(c.spend) },
      { label: "Last order", value: daysPhrase(c.last_order_days) },
      { label: "Orders · 2yr", value: String(c.orders) },
    ],
    highlights: (c.hooks || []).slice(0, 3).map((h) => ({ icon: "✦", label: h })),
    story: c.kind || "",
    nextContact: c.next_contact || "",
    topGroups: c.top_groups || [],
    balance: c.balance || 0,
    learned: c.learned || [],
    pitches: (payload.actions || []).map(toPitch),
    exhausted: !!payload.exhausted,
  };
}

export const api = {
  getAccounts: async () => (await get("/api/customers")).map(toAccount),
  getReasons: () => get("/api/reasons"),
  getPrep: async (code) => toPrep(await get(`/api/customer/${code}`)),
  // rejections: [{ id, reasons: [REASON_NAME], note }]
  sendFeedback: async (code, accepted, rejections) =>
    toPrep(await post(`/api/customer/${code}/feedback`, { accepted, rejections })),
  reset: async (code) => toPrep(await post(`/api/customer/${code}/reset`, {})),
};
