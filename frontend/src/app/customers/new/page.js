"use client";

// Add new customer — a business the rep just visited that isn't in Unleashed
// (Christina's request). Type the name, see any near-duplicates, then create
// it with the basics Unleashed needs: name, a free customer code, contact.
// Same check and create as the WhatsApp inbox, without needing a summary.

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import NewCustomer from "@/components/NewCustomer";
import { SCREEN } from "@/lib/nav";

function NewCustomerScreen() {
  const router = useRouter();
  const search = useSearchParams();
  const fromSearch = (search.get("name") || "").trim();
  const [draft, setDraft] = useState(fromSearch);
  // The name the duplicate check ran on; editing the box asks for a re-check.
  // A name carried over from a search that found nothing is checked at once.
  const [checked, setChecked] = useState(fromSearch);

  const onCheck = (e) => {
    e.preventDefault();
    setChecked(draft.trim());
  };
  const open = (code) => router.push(`/visit/${code}`);

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-12">
      <header className="pt-12">
        <Link
          href={SCREEN.CUSTOMERS}
          className="grid size-10 place-items-center rounded-full bg-card text-xl text-foreground ring-1 ring-border transition active:scale-95"
          aria-label="Back to all customers"
        >
          ‹
        </Link>

        <h1 className="mt-5 font-serif text-[34px] font-semibold leading-[1.05] tracking-[-0.02em] text-balance text-foreground">
          New customer
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          Visited a shop that isn’t in Unleashed yet? Add it here. We check it isn’t already a customer, then
          create it in Unleashed so their first order syncs straight in.
        </p>
      </header>

      <form onSubmit={onCheck} className="mt-5 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Business name"
          autoComplete="off"
          enterKeyHint="search"
          className="h-12 min-w-0 flex-1 rounded-2xl border border-border bg-card px-4 text-[16px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
        />
        <button
          type="submit"
          disabled={!draft.trim() || draft.trim() === checked}
          className="h-12 shrink-0 rounded-2xl bg-primary px-4 text-[14px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:opacity-50"
        >
          Check
        </button>
      </form>

      {checked && (
        <NewCustomer key={checked} name={checked} startOpen onLink={open} onCreated={(made) => open(made.code)} />
      )}
    </main>
  );
}

export default function NewCustomerPage() {
  return (
    <Suspense fallback={<main className="mx-auto min-h-screen w-full max-w-md px-5 pt-12 text-muted-foreground">Loading…</main>}>
      <NewCustomerScreen />
    </Suspense>
  );
}
