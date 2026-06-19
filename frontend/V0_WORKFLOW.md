# Frontend (Next.js) — v0 workflow

A Next.js (App Router · **JSX** · Tailwind · shadcn/ui) frontend for the Searay rep app.
It does **not** replace the backend — it calls the existing **Python engine** over a proxy,
so all the RFM / upsell / learning logic stays in Python.

## Run it (two terminals)

```bash
# 1) the engine (repo root) — JSON API on :8000
uv run app

# 2) the frontend (this folder) — app on :3000
cd frontend && pnpm dev
```

Open **http://localhost:3000**. `next.config.mjs` proxies `/api/*` → `http://localhost:8000`,
so the browser calls same-origin (no CORS). Override the backend with `SEARAY_API=...`.

## The v0 loop

1. **Generate.** Open [v0.dev](https://v0.dev), paste the prompt in [`../V0_PROMPT.md`](../V0_PROMPT.md), and generate. The prompt tells v0 to use **JavaScript/JSX** and to output code only (no preview/test) to keep token cost down.
2. **Bring it in.** Either run the `npx shadcn@latest add "<v0-block-url>"` command v0 gives you, or paste the component files into `src/components/` and add any shadcn primitives it imports: `npx shadcn@latest add button card sheet badge`.
3. **Wire to live data.** Replace v0's mock arrays with the client — the shapes already match:
   ```js
   import { api } from "@/lib/api";
   const accounts = await api.getAccounts();      // → AccountCard[]
   const prep     = await api.getPrep(code);       // → stats, highlights, pitches, learned…
   await api.sendFeedback(code, accepted, rejections);  // rejections: [{id, reasons:[NAME], note}]
   await api.reset(code);
   ```

## Key files

| File | Role |
|------|------|
| `next.config.mjs` | Proxies `/api/*` to the Python engine |
| `src/lib/api.js` | Fetches + **adapts** raw API → the friendly view model v0 designs against. Keep its output shape stable. |
| `src/app/page.js` | Placeholder home (replace with your v0 UI) |

Reason names for `sendFeedback`: `TOO_EXPENSIVE`, `WRONG_PRODUCT`, `ALREADY_HAVE`, `TRIED_BEFORE`, `NO_INCENTIVES`, `TOO_PUSHY`, `BAD_TIMING`, `WANT_OTHER` (also at `GET /api/reasons`).
