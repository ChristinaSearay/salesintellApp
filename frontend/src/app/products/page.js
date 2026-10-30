"use client";

// View Products — Christina's stock lookup. Search the synced Unleashed
// catalogue by code or description (quantities as of the last sync); tap a
// product for its live stock in every warehouse (/products/item?code=…).

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { SCREEN, productHref } from "@/lib/nav";

// Remembered for the tab, so "back" from a product lands on the same search.
const LIST_STATE_KEY = "searay.products.list";
const SEARCH_DEBOUNCE_MS = 250;

function readListState() {
  try {
    return JSON.parse(sessionStorage.getItem(LIST_STATE_KEY)) || {};
  } catch {
    return {};
  }
}

function writeListState(state) {
  try {
    sessionStorage.setItem(LIST_STATE_KEY, JSON.stringify(state));
  } catch {}
}

const PAGER_BTN =
  "h-11 min-w-[96px] rounded-full bg-card px-4 text-[14px] font-semibold text-foreground ring-1 ring-border transition active:scale-95 disabled:opacity-40 disabled:active:scale-100";

function ProductRow({ product: p }) {
  return (
    <Link
      href={productHref(p.code)}
      className="group flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 shadow-[0_6px_18px_-16px_rgba(33,29,23,0.5)] transition active:scale-[0.99]"
    >
      <div className="min-w-0 flex-1">
        <p className="font-mono text-[12px] font-semibold text-primary">{p.code}</p>
        <p className="mt-0.5 line-clamp-2 text-[14px] leading-snug text-foreground">{p.name}</p>
        {p.group && <p className="mt-0.5 truncate text-[11.5px] text-muted-foreground">{p.group}</p>}
      </div>
      <div className="shrink-0 text-right">
        <div className={`font-serif text-[19px] font-semibold leading-none ${p.inStock ? "text-foreground" : "text-muted-foreground"}`}>
          {p.onHand}
        </div>
        <div className="mt-1 text-[10.5px] font-medium text-muted-foreground">on hand</div>
      </div>
      <span className="text-xl font-light text-muted-foreground" aria-hidden>›</span>
    </Link>
  );
}

export default function ProductsPage() {
  const [filters, setFilters] = useState(null);
  const [typed, setTyped] = useState("");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    const saved = readListState();
    const restored = {
      q: typeof saved.q === "string" ? saved.q : "",
      group: typeof saved.group === "string" ? saved.group : "",
      inStock: typeof saved.inStock === "boolean" ? saved.inStock : true,
      page: Number.isInteger(saved.page) ? saved.page : 0,
    };
    setTyped(restored.q);
    setFilters(restored);
  }, []);

  // Typing only searches once the rep pauses.
  useEffect(() => {
    if (!filters || typed === filters.q) return;
    const t = setTimeout(() => setFilters((f) => ({ ...f, q: typed, page: 0 })), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [typed, filters]);

  useEffect(() => {
    if (!filters) return;
    writeListState(filters);
    let stale = false;
    api.searchProducts(filters)
      .then((r) => { if (!stale) { setResult(r); setErr(null); } })
      .catch((e) => { if (!stale) setErr(String(e)); });
    return () => { stale = true; };
  }, [filters]);

  const update = (patch) => setFilters((f) => ({ ...f, ...patch, page: 0 }));
  const goTo = (page) => {
    setFilters((f) => ({ ...f, page }));
    window.scrollTo({ top: 0 });
  };

  const searching = !!filters?.q.trim();

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-12">
      <header className="pt-12">
        <Link
          href={SCREEN.ATTENTION}
          className="grid size-10 place-items-center rounded-full bg-card text-xl text-foreground ring-1 ring-border transition active:scale-95"
          aria-label="Back to needs attention"
        >
          ‹
        </Link>

        <h1 className="mt-5 font-serif text-[34px] font-semibold leading-[1.05] tracking-[-0.02em] text-balance text-foreground">
          View products
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          Stock here is as of the last Unleashed sync. Tap a product for live stock in every warehouse.
        </p>

        <div className="sticky top-[env(safe-area-inset-top,0px)] z-10 -mx-5 mt-5 bg-background/95 px-5 py-2 backdrop-blur">
          <input
            type="search"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="🔍  Search product code or description"
            autoComplete="off"
            enterKeyHint="search"
            className="h-12 w-full rounded-2xl border border-border bg-card px-4 text-[16px] text-foreground shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)] outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
          />
          <div className="mt-2 flex items-center gap-2">
            <select
              value={filters?.group || ""}
              onChange={(e) => update({ group: e.target.value })}
              aria-label="Product group"
              className="h-10 min-w-0 flex-1 rounded-xl border border-border bg-card px-3 text-[14px] text-foreground outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="">All groups</option>
              {(result?.groups || []).map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
            <label className="flex h-10 shrink-0 cursor-pointer items-center gap-2 rounded-xl bg-card px-3 text-[13.5px] font-semibold text-foreground ring-1 ring-border">
              <input
                type="checkbox"
                checked={!!filters?.inStock}
                onChange={(e) => update({ inStock: e.target.checked })}
                className="size-4 accent-primary"
              />
              In stock only
            </label>
          </div>
        </div>
      </header>

      {err && (
        <p className="mt-6 rounded-2xl bg-danger-soft px-4 py-3 text-[14px] font-medium text-danger">
          Can’t reach the engine. Start it with <code className="font-mono">uv run app</code>.
        </p>
      )}

      <section aria-label="Products" className="mt-4 flex flex-col gap-2.5">
        {result?.items.map((p) => (
          <ProductRow key={p.code} product={p} />
        ))}
      </section>

      {result && result.pageCount > 1 && (
        <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-3">
          <button type="button" onClick={() => goTo(result.page - 1)} disabled={result.page === 0} className={PAGER_BTN}>
            ‹ Previous
          </button>
          <span className="text-[13px] text-muted-foreground">
            Page {result.page + 1} of {result.pageCount}
          </span>
          <button type="button" onClick={() => goTo(result.page + 1)} disabled={result.page >= result.pageCount - 1} className={PAGER_BTN}>
            Next ›
          </button>
        </nav>
      )}

      {result && (
        <p className="mt-6 text-center text-xs text-muted-foreground">
          {result.total === 0
            ? searching
              ? `No product matches “${filters.q.trim()}”${filters.inStock ? " in stock" : ""}.`
              : "No products."
            : `${result.total.toLocaleString()} ${result.total === 1 ? "product" : "products"}${searching ? " match" : ""}` +
              (searching ? "" : ", newest first")}
        </p>
      )}
    </main>
  );
}
