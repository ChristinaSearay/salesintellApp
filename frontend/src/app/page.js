"use client";

// Screen 1 — Accounts. v0's design, driven by the live engine
// (api.getAccounts() → /api proxy → Python). On top, the "Needs attention"
// queue: the 5 customers to work on now; a saved note sends one to the back of
// the line and the next pops up. Below, every active Unleashed customer,
// biggest 2-year spend first, searchable and paged.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, matchesAccount } from "@/lib/api";
import AccountCard from "@/components/AccountCard";
import AttentionCard from "@/components/AttentionCard";

const PAGE_SIZE = 10;
// Remembered for the tab, so "back" from a visit lands on the same page.
const LIST_STATE_KEY = "searay.accounts.list";

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

export default function AccountsPage() {
  const [accounts, setAccounts] = useState(null);
  const [err, setErr] = useState(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [restored, setRestored] = useState(false);
  const [attention, setAttention] = useState(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch((e) => setErr(String(e)));
    api.getAttention().then(setAttention).catch((e) => setErr(String(e)));
    const saved = readListState();
    if (typeof saved.query === "string") setQuery(saved.query);
    if (Number.isInteger(saved.page)) setPage(saved.page);
    setRestored(true);
  }, []);

  useEffect(() => {
    if (restored) writeListState({ query, page });
  }, [restored, query, page]);

  const searching = query.trim().length > 0;
  const matches = useMemo(
    () => (accounts || []).filter((a) => matchesAccount(a, query)),
    [accounts, query]
  );
  const pageCount = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const shown = matches.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);

  const onSearch = (value) => {
    setQuery(value);
    setPage(0);
  };

  const goTo = (next) => {
    setPage(next);
    // Back to the top of the customer list (below the queue), not the page top.
    const heading = document.getElementById("all-customers");
    const top = heading ? heading.getBoundingClientRect().top + window.scrollY - 16 : 0;
    window.scrollTo({ top });
  };

  const onNoteSaved = (account, next) => {
    setAttention(next);
    setToast(`Noted ${account.name} — back of the line for ${next.snoozeDays} days.`);
  };

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
              {attention?.overdue > 0 && (
                <>
                  {" · "}
                  <span className="font-semibold text-danger">{attention.overdue} overdue for an order</span>
                </>
              )}
              .
            </>
          ) : (
            "Loading your accounts…"
          )}
        </p>
      </header>

      {err && (
        <p className="mt-6 rounded-2xl bg-danger-soft px-4 py-3 text-[14px] font-medium text-danger">
          Can’t reach the engine. Start it with <code className="font-mono">uv run app</code>.
        </p>
      )}

      {attention && attention.queue.length > 0 && (
        <section aria-labelledby="attention-heading" className="mt-7">
          <h2 id="attention-heading" className="font-serif text-[22px] font-semibold tracking-[-0.01em] text-foreground">
            Needs attention
          </h2>
          <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            Biggest spenders first — late for an order, then no recent note. Add a note once you’ve
            actioned one and the next customer pops up.
          </p>
          {toast && (
            <p role="status" className="mt-3 rounded-2xl bg-good-soft px-4 py-2.5 text-[13px] font-semibold text-good">
              ✓ {toast}
            </p>
          )}
          <div className="mt-3 flex flex-col gap-3">
            {attention.queue.map((a, i) => (
              <AttentionCard key={a.code} account={a} index={i} onSaved={onNoteSaved} />
            ))}
          </div>
        </section>
      )}

      <h2 id="all-customers" className="mt-9 font-serif text-[22px] font-semibold tracking-[-0.01em] text-foreground">
        All customers
      </h2>
      <div className="sticky top-[env(safe-area-inset-top,0px)] z-10 -mx-5 mt-2 bg-background/95 px-5 py-2 backdrop-blur">
        <input
          type="search"
          value={query}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="🔍  Search customer name or code"
          autoComplete="off"
          enterKeyHint="search"
          className="h-12 w-full rounded-2xl border border-border bg-card px-4 text-[16px] text-foreground shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)] outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
        />
      </div>

      <section aria-label="All customers" className="mt-2 flex flex-col gap-3">
        {shown.map((a, i) => (
          <AccountCard key={a.code} account={a} index={i} />
        ))}
      </section>

      {accounts && matches.length > PAGE_SIZE && (
        <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => goTo(current - 1)}
            disabled={current === 0}
            className="h-11 min-w-[96px] rounded-full bg-card px-4 text-[14px] font-semibold text-foreground ring-1 ring-border transition active:scale-95 disabled:opacity-40 disabled:active:scale-100"
          >
            ‹ Previous
          </button>
          <span className="text-[13px] text-muted-foreground">
            Page {current + 1} of {pageCount}
          </span>
          <button
            type="button"
            onClick={() => goTo(current + 1)}
            disabled={current >= pageCount - 1}
            className="h-11 min-w-[96px] rounded-full bg-card px-4 text-[14px] font-semibold text-foreground ring-1 ring-border transition active:scale-95 disabled:opacity-40 disabled:active:scale-100"
          >
            Next ›
          </button>
        </nav>
      )}

      {accounts && (
        <p className="mt-6 text-center text-xs text-muted-foreground">
          {searching && matches.length === 0
            ? `No customer matches “${query.trim()}”.`
            : matches.length > PAGE_SIZE
              ? `${current * PAGE_SIZE + 1}–${current * PAGE_SIZE + shown.length} of ${matches.length.toLocaleString()} ${searching ? "matches" : "customers, biggest spend first"}`
              : "Tap a customer to prep your visit"}
        </p>
      )}
    </main>
  );
}
