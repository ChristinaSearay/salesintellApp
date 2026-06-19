"use client";

// Screen 1 — Accounts. v0's "Today's visits" design, driven by the live engine
// (api.getAccounts() → /api proxy → Python).

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import AccountCard from "@/components/AccountCard";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch((e) => setErr(String(e)));
  }, []);

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
          <span className="grid size-9 place-items-center rounded-full bg-card text-sm font-semibold text-foreground ring-1 ring-border">
            SR
          </span>
        </div>

        <h1 className="mt-7 font-serif text-[34px] font-semibold leading-[1.05] tracking-[-0.02em] text-balance text-foreground">
          Today&apos;s visits
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          {accounts ? (
            <>
              {accounts.length} accounts to see
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
      </header>

      {err && (
        <p className="mt-6 rounded-2xl bg-danger-soft px-4 py-3 text-[14px] font-medium text-danger">
          Can’t reach the engine. Start it with <code className="font-mono">uv run app</code>.
        </p>
      )}

      <section aria-label="Your accounts" className="mt-7 flex flex-col gap-3">
        {accounts?.map((a, i) => (
          <AccountCard key={a.code} account={a} index={i} />
        ))}
      </section>

      {accounts && (
        <p className="mt-8 text-center text-xs text-muted-foreground">
          Tap a customer to prep your visit
        </p>
      )}
    </main>
  );
}
