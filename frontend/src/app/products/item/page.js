"use client";

// One product, live from Unleashed: how many are on hand and in which
// warehouses, grouped as Our stock / At customers (consignment) / Not for sale.
// The synced numbers show at once; the live check takes a few seconds because
// Unleashed is asked about every warehouse separately (utils/stock.py).

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { PRODUCTS } from "@/lib/nav";

const CARD = "rounded-3xl border border-border bg-card p-4 shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)]";

function Totals({ totals }) {
  return (
    <section className="mt-5 grid grid-cols-4 gap-2" aria-label="Stock totals">
      {totals.map((t) => (
        <div key={t.label} className="rounded-2xl border border-border bg-card px-1.5 py-3 text-center shadow-[0_6px_18px_-16px_rgba(33,29,23,0.5)]">
          <div className="font-serif text-[19px] font-semibold leading-none text-foreground">{t.value}</div>
          <div className="mt-1.5 text-[10.5px] font-medium leading-tight text-muted-foreground">{t.label}</div>
        </div>
      ))}
    </section>
  );
}

function WarehouseGroup({ group }) {
  return (
    <section className={`mt-3 ${CARD}`}>
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{group.label}</h2>
        <span className="text-[12px] font-semibold text-foreground">{group.onHand} on hand</span>
      </div>
      {/* Fixed columns so the numbers line up from one group's card to the next. */}
      <table className="mt-2 w-full table-fixed text-[13.5px]">
        <thead>
          <tr className="text-[10.5px] font-medium text-muted-foreground">
            <th className="py-1 text-left font-medium">Warehouse</th>
            <th className="w-14 py-1 text-right font-medium">On hand</th>
            <th className="w-16 py-1 text-right font-medium">Allocated</th>
            <th className="w-16 py-1 text-right font-medium">Available</th>
          </tr>
        </thead>
        <tbody>
          {group.warehouses.map((w) => (
            <tr key={w.code} className="border-t border-border">
              <td className="py-2 pr-2 text-foreground">{w.name}</td>
              <td className="py-2 text-right font-semibold text-foreground">{w.onHand}</td>
              <td className="py-2 text-right text-muted-foreground">{w.allocated}</td>
              <td className="py-2 text-right text-muted-foreground">{w.available}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ProductInner() {
  const code = useSearchParams().get("code") || "";
  const [synced, setSynced] = useState(null);
  const [live, setLive] = useState(null);
  const [checking, setChecking] = useState(false);
  const [err, setErr] = useState(null);

  const check = useCallback(() => {
    setChecking(true);
    setErr(null);
    api.getProduct(code)
      .then(setLive)
      .catch((e) => setErr(e.message))
      .finally(() => setChecking(false));
  }, [code]);

  useEffect(() => {
    if (!code) return;
    api.getSyncedProduct(code).then(setSynced).catch(() => {});
    check();
  }, [code, check]);

  const name = live?.name || synced?.name || code;
  const group = live?.group || synced?.group || "";

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-12">
      <header className="pt-12">
        <Link
          href={PRODUCTS}
          className="grid size-10 place-items-center rounded-full bg-card text-xl text-foreground ring-1 ring-border transition active:scale-95"
          aria-label="Back to products"
        >
          ‹
        </Link>

        {live?.image && (
          // Unleashed's own CDN image; plain <img> since it's an external host.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={live.image}
            alt={name}
            className="mt-5 aspect-square w-full rounded-3xl border border-border bg-card object-contain"
          />
        )}

        <p className="mt-5 font-mono text-[13px] font-semibold text-primary">{code}</p>
        <h1 className="mt-1 font-serif text-[26px] font-semibold leading-[1.15] tracking-[-0.01em] text-balance text-foreground">
          {name}
        </h1>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {group && (
            <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold text-muted-foreground">{group}</span>
          )}
          {live?.obsolete && (
            <span className="rounded-full bg-warn-soft px-2.5 py-1 text-[11px] font-semibold text-warn">Obsolete in Unleashed</span>
          )}
        </div>
      </header>

      {live ? (
        <>
          <p className="mt-5 text-[12px] text-muted-foreground">
            <span aria-hidden>🟢</span> Live from Unleashed · {live.checkedAt}
            {" · "}
            <button type="button" onClick={check} disabled={checking} className="font-semibold text-primary disabled:opacity-50">
              {checking ? "Checking…" : "Refresh"}
            </button>
          </p>
          <Totals totals={live.totals} />
          {live.groups.length > 0 ? (
            live.groups.map((g) => <WarehouseGroup key={g.key} group={g} />)
          ) : (
            <p className={`mt-3 text-[14px] text-muted-foreground ${CARD}`}>None in any warehouse right now.</p>
          )}
        </>
      ) : (
        <>
          {synced && (
            <section className={`mt-5 ${CARD}`}>
              <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">At last sync</h2>
              <p className="mt-1.5 text-[15px] text-foreground">
                <span className="font-semibold">{synced.onHand}</span> on hand ·{" "}
                <span className="font-semibold">{synced.available}</span> available
              </p>
            </section>
          )}
          {checking && (
            <p role="status" className="mt-4 animate-pulse rounded-2xl bg-info-soft px-4 py-3 text-[13.5px] font-medium text-info">
              Checking every warehouse in Unleashed… this takes a few seconds.
            </p>
          )}
          {err && (
            <div className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-[13.5px] font-medium text-danger">
              <p>Couldn’t get live stock: {err}</p>
              <button type="button" onClick={check} className="mt-2 font-semibold underline">
                Try again
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}

export default function ProductPage() {
  return (
    <Suspense fallback={<main className="mx-auto min-h-screen w-full max-w-md px-5 pt-12 text-muted-foreground">Loading…</main>}>
      <ProductInner />
    </Suspense>
  );
}
