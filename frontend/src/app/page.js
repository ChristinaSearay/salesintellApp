"use client";

// Screen 1 — Accounts. A functional starting point (restyle with v0 later).
// Live data via api.getAccounts(); each card links to /visit/[code].

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import AccountCard from "@/components/AccountCard";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch((e) => setErr(String(e)));
  }, []);

  return (
    <main className="mx-auto min-h-screen max-w-md bg-neutral-50">
      <header className="bg-gradient-to-br from-emerald-700 to-emerald-900 px-5 pb-5 pt-12 text-white">
        <div className="text-2xl font-bold tracking-tight">Searay</div>
        <div className="text-sm text-emerald-100/90">Sales Assistant</div>
      </header>

      <div className="p-5">
        <h1 className="text-xl font-bold">Your accounts</h1>
        <p className="mt-1 text-sm text-neutral-500">Tap a customer to prep your visit.</p>

        {err && (
          <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            Can’t reach the API ({err}). Start it with <code className="font-mono">uv run app</code>.
          </p>
        )}
        {!accounts && !err && <p className="mt-8 text-neutral-400">Loading…</p>}

        <ul className="mt-4 space-y-3">
          {accounts?.map((a) => (
            <li key={a.code}>
              <AccountCard account={a} />
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
