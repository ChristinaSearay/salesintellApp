# v0 Prompt — Searay Sales Assistant

> Paste everything below the line into v0.

---

Build a **mobile web app** (Next.js App Router, **JavaScript/JSX**, Tailwind, shadcn/ui) for jewellery wholesale **sales reps** to prep customer visits on their phone. The rep is non-technical — it must make sense at a glance and feel like a beautiful, modern, slightly playful $100M app. **You own the design — layout, colour, type, and motion are your call.** Keep first-glance text minimal; tuck detail behind taps.

Output JSX only — don't run, preview, or test it (one pass).

**Two screens:**
1. **Accounts** — a list of customer cards (name + a friendly status + the odd alert like "owes money"). Tap one to open.
2. **Visit prep** — the customer's key stats, a few short "what's going on" highlights, and **3 pitch cards** the rep accepts 👍 or rejects 👎 (rejecting asks a quick reason). A button swaps in 3 fresh pitches; small "what I've learned" hints build up over time.

Use this mock data (same shape the real API returns; wire buttons to stub handlers):

```js
const accounts = [
  { code:"CMJ223", name:"Class A Manufacturing Jewellers", emoji:"⭐", status:"Top customer",
    alerts:[{icon:"👋",label:"May be leaving us"},{icon:"💰",label:"Owes $2,862"}] },
  { code:"MJ001", name:"My Jewellers", emoji:"💚", status:"Loyal",
    alerts:[{icon:"📉",label:"Slowing down"}] },
  { code:"TCJ1138", name:"The Cut Jewellery", emoji:"❄️", status:"Gone cold",
    alerts:[{icon:"👀",label:"Keen but hasn't bought"}] },
];

const prep = {
  account: accounts[0],
  stats: [{label:"Spend · 2yr", value:"$178K"}, {label:"Last order", value:"5 days ago"}, {label:"Orders · 2yr", value:"106"}],
  highlights: [{icon:"⚠️",label:"Quality complaint (9KC239)"}, {icon:"💎",label:"Wants lab-grown bracelets"}, {icon:"💰",label:"Owes $2,862"}],
  pitches: [
    { id:"p1", badge:"Save the account", title:"Fix the 9KC239 quality complaint",
      products:[{name:"9k Puff Heart Pendant", price:"$266", inStock:true}], offer:"Free replacement + credit — needs manager OK" },
    { id:"p2", badge:"Try something new", title:"Lab-grown diamond bracelets for Sam",
      products:[{name:"9k Lab Diamond Tennis Bracelet", price:"$3,464", inStock:true}], offer:null },
    { id:"p3", badge:"Protect the order", title:"Lock in their core chain lines", products:[], offer:null },
  ],
  learned: [{icon:"🏷️",label:"No discounts"}],
};
```

Reject-reason chips: Too pricey · Don't sell it · No discounts · Too pushy · Bad timing · Tried it · Has it · Show others.
