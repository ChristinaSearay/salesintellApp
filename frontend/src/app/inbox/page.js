"use client";

// Screen 3 — WhatsApp inbox. Paste (or forward) a team WhatsApp dump; the
// engine summarises it into per-customer updates; the rep confirms each one
// and it lands in that customer's "What's going on" + re-ranks their pitches.

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { api, whenPhrase } from "@/lib/api";
import NewCustomer from "@/components/NewCustomer";

const RELATIONSHIP_LABEL = {
  CHURN_RISK: { icon: "👋", label: "May be leaving us", cls: "bg-danger-soft text-danger" },
  STALLED: { icon: "😶", label: "Gone quiet", cls: "bg-warn-soft text-warn" },
  DECLINING: { icon: "📉", label: "Slowing down", cls: "bg-warn-soft text-warn" },
  DORMANT_PROSPECT: { icon: "👀", label: "Keen, hasn’t bought", cls: "bg-info-soft text-info" },
  OCCASIONAL: { icon: "🛒", label: "Buys now & then", cls: "bg-muted text-muted-foreground" },
};

function Proposal({ p, accounts, onSave, onDiscard, saving, onCreated, focusCode }) {
  // Opened from a customer's page ("Add WhatsApp update"), so an update the
  // model couldn't place is about THEM. Notes name people, not shop names —
  // "Michelle is waiting on a quote" is Evans Jewellery to the rep who wrote
  // it, and there are four Michelles in the customer master.
  const [code, setCode] = useState(p.customer_code || focusCode || "");
  const rel = RELATIONSHIP_LABEL[p.relationship];
  // Once the rep creates (or links) the business, this stops being unmatched.
  const unmatched = !code;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className={`rounded-3xl border bg-card p-4 shadow-[0_8px_24px_-18px_rgba(33,29,23,0.55)] ${unmatched ? "border-warn/40" : "border-border"}`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {unmatched ? "Not one of ours" : "Update for"}
        </span>
        {unmatched ? (
          <span className="rounded-full bg-warn-soft px-2.5 py-1 text-[11px] font-semibold text-warn">{p.customer_as_written || "Unknown"}</span>
        ) : null}
        {rel && (
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${rel.cls}`}>
            <span aria-hidden>{rel.icon}</span> {rel.label}
          </span>
        )}
      </div>

      <select
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="mt-2 w-full rounded-xl border border-border bg-background px-3 py-2 font-serif text-[18px] font-semibold text-foreground"
      >
        <option value="">— pick a customer to file this under —</option>
        {accounts.map((a) => (
          <option key={a.code} value={a.code}>{a.name}</option>
        ))}
      </select>
      {!p.customer_code && code && focusCode === code && (
        <p className="mt-1.5 text-[12px] text-muted-foreground">
          Written as “{p.customer_as_written}” — filed under the customer you opened this from. Change it above
          if that’s wrong.
        </p>
      )}
      {unmatched && (
        <>
          <p className="mt-1.5 text-[12px] text-muted-foreground">
            Written as “{p.customer_as_written}” — not in the app’s customer list. Pick one above if it’s a
            nickname, or add them to Unleashed below.
          </p>
          {p.customer_as_written && (
            <NewCustomer
              name={p.customer_as_written}
              onLink={(picked) => setCode(picked)}
              onCreated={(made) => { setCode(made.code); onCreated?.(made); }}
            />
          )}
        </>
      )}

      <ul className="mt-3 flex flex-col gap-2">
        {p.hooks.map((h, i) => (
          <li key={i} className="flex items-start gap-2.5 text-[14.5px] leading-snug text-foreground">
            <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-info-soft text-[12px]" aria-hidden>💬</span>
            <span>{h}</span>
          </li>
        ))}
      </ul>

      {(p.opportunity_groups?.length > 0 || p.prior_incentive) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {p.opportunity_groups.map((g) => (
            <span key={g} className="rounded-full bg-good-soft px-2.5 py-1 text-[11px] font-semibold text-good">🎯 Pitch {g}</span>
          ))}
          {p.prior_incentive && (
            <span className="rounded-full bg-warn-soft px-2.5 py-1 text-[11px] font-semibold text-warn">🏷️ Asked for: {p.prior_incentive}</span>
          )}
        </div>
      )}
      {p.advice && (
        <p className="mt-3 rounded-2xl bg-secondary/70 px-3.5 py-2.5 text-[13px] leading-snug text-secondary-foreground">
          <span className="font-semibold">Next move: </span>{p.advice}
        </p>
      )}

      <div className="mt-4 grid grid-cols-[1fr_auto] gap-2">
        <button
          type="button"
          disabled={!code || saving}
          onClick={() => onSave({ ...p, customer_code: code })}
          className="h-11 rounded-xl bg-primary text-[14px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:opacity-50"
        >
          {saving ? "Saving…" : "✅ Add to what’s going on"}
        </button>
        <button type="button" onClick={onDiscard} className="h-11 rounded-xl px-4 text-[14px] font-semibold text-muted-foreground ring-1 ring-border">
          Discard
        </button>
      </div>
    </motion.article>
  );
}

function InboxInner() {
  const search = useSearchParams();
  const focusCode = search.get("code") || "";
  const [accounts, setAccounts] = useState([]);
  const [text, setText] = useState("");
  const [proposals, setProposals] = useState([]);
  const [busy, setBusy] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [err, setErr] = useState(null);
  const [saved, setSaved] = useState([]);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch(() => {});
  }, []);
  useEffect(() => {
    if (focusCode) api.getIntel(focusCode).then(setHistory).catch(() => {});
  }, [focusCode, saved.length]);

  // A brand-new customer must appear in the "file this under" list straight
  // away, or the rep can't save the very update that created them.
  function onProspectCreated(made) {
    setAccounts((list) =>
      list.some((a) => a.code === made.code)
        ? list
        : [...list, { code: made.code, name: made.name }]);
    api.getAccounts().then(setAccounts).catch(() => {});
  }

  async function summarise() {
    setErr(null);
    setBusy(true);
    try {
      setProposals(await api.summarise(text));
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  async function save(p) {
    setSavingId(p.id);
    setErr(null);
    try {
      await api.saveIntel(p.customer_code, p);
      const acc = accounts.find((a) => a.code === p.customer_code);
      setSaved((s) => [...s, { code: p.customer_code, name: acc?.name || p.customer_code }]);
      setProposals((ps) => ps.filter((x) => x.id !== p.id));
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setSavingId(null);
    }
  }

  async function remove(u) {
    await api.deleteIntel(u.customer_code, u.id);
    setHistory((h) => h.filter((x) => x.id !== u.id));
  }

  const focusName = accounts.find((a) => a.code === focusCode)?.name;

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-16">
      <header className="pt-12">
        <Link
          href={focusCode ? `/visit/${focusCode}` : "/"}
          className="grid size-10 place-items-center rounded-full bg-card text-xl text-foreground ring-1 ring-border transition active:scale-95"
          aria-label="Back"
        >
          ‹
        </Link>
        <h1 className="mt-5 font-serif text-[30px] font-semibold leading-[1.05] tracking-[-0.02em] text-foreground">
          WhatsApp updates
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          Paste the team chat. I’ll work out who it’s about, add the gist to their
          <em> What’s going on</em>, and rethink the pitches.
        </p>
      </header>

      <section className="mt-6">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          placeholder={"CLASS A JEWELLERS\nConfirmed they are interested in sample tennis bracelets but require finish to be very high quality"}
          className="w-full rounded-3xl border border-border bg-card p-4 text-[15px] leading-relaxed text-foreground shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)] outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
        />
        <button
          type="button"
          onClick={summarise}
          disabled={busy || text.trim().length < 10}
          className="mt-3 flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-primary text-[16px] font-semibold text-primary-foreground shadow-[0_12px_30px_-12px_rgba(154,107,31,0.7)] transition active:scale-[0.99] disabled:opacity-60"
        >
          {busy ? "Reading the chat…" : <><span aria-hidden>✨</span> Summarise &amp; match customers</>}
        </button>
        {err && (
          <p className="mt-3 rounded-2xl bg-danger-soft px-4 py-3 text-[13px] font-medium text-danger">{err}</p>
        )}
      </section>

      <AnimatePresence>
        {proposals.length > 0 && (
          <motion.section layout className="mt-6 flex flex-col gap-3.5" aria-label="Proposed updates">
            <h2 className="font-serif text-[20px] font-semibold text-foreground">
              {proposals.length} update{proposals.length === 1 ? "" : "s"} found — confirm each
            </h2>
            {proposals.map((p) => (
              <Proposal
                key={p.id}
                p={p}
                accounts={accounts}
                saving={savingId === p.id}
                focusCode={focusCode}
                onSave={save}
                onCreated={onProspectCreated}
                onDiscard={() => setProposals((ps) => ps.filter((x) => x.id !== p.id))}
              />
            ))}
          </motion.section>
        )}
      </AnimatePresence>

      {saved.length > 0 && (
        <section className="mt-6 rounded-2xl border border-good/30 bg-good-soft/50 p-3.5">
          <h2 className="text-[13px] font-semibold text-good">Added</h2>
          <ul className="mt-2 flex flex-col gap-1.5">
            {saved.map((s, i) => (
              <li key={i} className="flex items-center justify-between text-[14px] text-foreground">
                <span>{s.name}</span>
                <Link href={`/visit/${s.code}`} className="text-[13px] font-semibold text-primary">Open prep ›</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {focusCode && (
        <section className="mt-8">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Saved updates · {focusName || focusCode}
          </h2>
          {history.length === 0 ? (
            <p className="mt-2 text-[14px] text-muted-foreground">Nothing from WhatsApp yet.</p>
          ) : (
            <ul className="mt-3 flex flex-col gap-2.5">
              {[...history].reverse().map((u) => (
                <li key={u.id} className="rounded-2xl border border-border bg-card p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-muted-foreground">💬 {whenPhrase(u.ts)}</span>
                    <button onClick={() => remove(u)} className="text-[12px] font-semibold text-muted-foreground active:text-danger">Remove</button>
                  </div>
                  <ul className="mt-2 flex flex-col gap-1 text-[14px] leading-snug text-foreground">
                    {u.hooks.map((h, i) => <li key={i}>• {h}</li>)}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}

export default function InboxPage() {
  return (
    <Suspense fallback={<main className="mx-auto min-h-screen w-full max-w-md px-5 pt-12 text-muted-foreground">Loading…</main>}>
      <InboxInner />
    </Suspense>
  );
}
