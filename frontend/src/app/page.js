"use client";

// Screen 1 — Needs attention. v0's design, driven by the live engine
// (api.getAttention() → /api proxy → Python): the 5 customers to work on now;
// a saved note sends one to the back of the line and the next pops up. The
// full searchable list lives behind the "All customers" button (/customers).

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { SCREEN, useRememberScreen } from "@/lib/nav";
import AttentionCard from "@/components/AttentionCard";

const PILL =
  "flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full bg-card px-3 text-[13px] font-semibold text-foreground ring-1 ring-border transition active:scale-95";

export default function AttentionPage() {
  const [attention, setAttention] = useState(null);
  const [err, setErr] = useState(null);
  const [toast, setToast] = useState("");
  useRememberScreen(SCREEN.ATTENTION);

  useEffect(() => {
    api.getAttention().then(setAttention).catch((e) => setErr(String(e)));
  }, []);

  const onNoteSaved = (account, next) => {
    setAttention(next);
    setToast(`Noted ${account.name} — back of the line for ${next.snoozeDays} days.`);
  };

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-12">
      <header className="pt-12">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary">
            Searay
          </span>
          <nav aria-label="Screens" className="flex items-center gap-2">
            <Link href={SCREEN.CUSTOMERS} className={PILL}>
              <span aria-hidden>👥</span> All customers
            </Link>
            <Link href="/inbox" className={PILL}>
              <span aria-hidden>💬</span> WhatsApp
            </Link>
          </nav>
        </div>

        <h1 className="mt-7 font-serif text-[34px] font-semibold leading-[1.05] tracking-[-0.02em] text-balance text-foreground">
          Needs attention
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          {attention ? (
            <>
              {attention.overdue > 0 && (
                <span className="font-semibold text-danger">{attention.overdue} customers overdue for an order. </span>
              )}
              Biggest spenders first — late for an order, then no recent note. Add a note once you’ve
              actioned one and the next customer pops up.
            </>
          ) : (
            "Loading…"
          )}
        </p>
      </header>

      {err && (
        <p className="mt-6 rounded-2xl bg-danger-soft px-4 py-3 text-[14px] font-medium text-danger">
          Can’t reach the engine. Start it with <code className="font-mono">uv run app</code>.
        </p>
      )}

      {toast && (
        <p role="status" className="mt-5 rounded-2xl bg-good-soft px-4 py-2.5 text-[13px] font-semibold text-good">
          ✓ {toast}
        </p>
      )}

      {attention && (
        <section aria-label="Needs attention" className="mt-5 flex flex-col gap-3">
          {attention.queue.map((a, i) => (
            <AttentionCard key={a.code} account={a} index={i} onSaved={onNoteSaved} />
          ))}
        </section>
      )}
    </main>
  );
}
