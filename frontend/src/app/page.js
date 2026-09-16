"use client";

// Screen 1 — Accounts. v0's design, driven by the live engine
// (api.getAccounts() → /api proxy → Python). Every active Unleashed customer,
// biggest 2-year spend first, with search so a rep on the road can find anyone.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, matchesAccount } from "@/lib/api";
import AccountCard from "@/components/AccountCard";

// Cards rendered at once: top accounts when idle, best matches when searching.
const BROWSE_LIMIT = 30;
const SEARCH_LIMIT = 50;

export default function AccountsPage() {
  const [accounts, setAccounts] = useState(null);
  const [err, setErr] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch((e) => setErr(String(e)));
  }, []);

  const searching = query.trim().length > 0;
  const matches = useMemo(
    () => (accounts || []).filter((a) => matchesAccount(a, query)),
    [accounts, query]
  );
  const shown = matches.slice(0, searching ? SEARCH_LIMIT : BROWSE_LIMIT);

  const needAttention = (accounts || []).filter((a) =>
    a.alerts?.some((al) => al.tone === "danger")
  ).length;

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-12">
      <header className="pt-12">
        <div className="flex items-center justify-between">
          <span className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary">
            Searay
          </span>
          <Link
            href="/inbox"
            className="flex h-9 items-center gap-1.5 rounded-full bg-card px-3.5 text-[13px] font-semibold text-foreground ring-1 ring-border transition active:scale-95"
          >
            <span aria-hidden>💬</span> WhatsApp
          </Link>
        </div>

        <h1 className="mt-7 font-serif text-[34px] font-semibold leading-[1.05] tracking-[-0.02em] text-balance text-foreground">
          Your accounts
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          {accounts ? (
            <>
              {accounts.length.toLocaleString()} customers
              {needAttention > 0 && (
                <>
                  {" · "}
                  <span className="font-semibold text-danger">{needAttention} need a nudge</span>
                </>
              )}
              .
            </>
          ) : (
            "Loading your accounts…"
          )}
        </p>

        <div className="sticky top-[env(safe-area-inset-top,0px)] z-10 -mx-5 mt-5 bg-background/95 px-5 py-2 backdrop-blur">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="🔍  Search customer name or code"
            autoComplete="off"
            enterKeyHint="search"
            className="h-12 w-full rounded-2xl border border-border bg-card px-4 text-[16px] text-foreground shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)] outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
          />
        </div>
      </header>

      {err && (
        <p className="mt-6 rounded-2xl bg-danger-soft px-4 py-3 text-[14px] font-medium text-danger">
          Can’t reach the engine. Start it with <code className="font-mono">uv run app</code>.
        </p>
      )}

      <section aria-label="Your accounts" className="mt-4 flex flex-col gap-3">
        {shown.map((a, i) => (
          <AccountCard key={a.code} account={a} index={i} />
        ))}
      </section>

      {accounts && (
        <p className="mt-8 text-center text-xs text-muted-foreground">
          {searching && matches.length === 0
            ? `No customer matches “${query.trim()}”.`
            : matches.length > shown.length
              ? searching
                ? `Showing ${shown.length} of ${matches.length} matches — keep typing to narrow it down`
                : `Top ${shown.length} by spend — search to find any of the ${accounts.length.toLocaleString()} customers`
              : "Tap a customer to prep your visit"}
        </p>
      )}
    </main>
  );
}
