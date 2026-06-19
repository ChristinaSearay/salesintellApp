"use client";

// Screen 2 — Visit prep. v0's design, wired to the live engine: real reasons,
// real pitches, and the accept/skip → re-suggest learning loop (api.sendFeedback
// persists per-customer preferences in Python).

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { toneCls } from "@/lib/ui";
import Pitch from "@/components/Pitch";

function initMarks(prep) {
  const m = {};
  prep.pitches.forEach((p) => {
    if (p.accepted) m[p.id] = { decision: "good", reasons: [] };
  });
  return m;
}

export default function VisitPage({ params }) {
  const { code } = use(params);
  const [prep, setPrep] = useState(null);
  const [reasons, setReasons] = useState([]);
  const [marks, setMarks] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.getReasons().then(setReasons).catch(() => {});
    api.getPrep(code)
      .then((p) => { setPrep(p); setMarks(initMarks(p)); })
      .catch((e) => setErr(String(e)));
  }, [code]);

  const setDecision = (id, decision) =>
    setMarks((m) => ({ ...m, [id]: { decision, reasons: m[id]?.reasons || [] } }));

  const toggleReason = (id, name) =>
    setMarks((m) => {
      const cur = m[id]?.reasons || [];
      const next = cur.includes(name) ? cur.filter((x) => x !== name) : [...cur, name];
      return { ...m, [id]: { decision: m[id]?.decision || "no", reasons: next } };
    });

  async function refresh() {
    const accepted = [];
    const rejections = [];
    for (const [id, x] of Object.entries(marks)) {
      if (x.decision === "good") accepted.push(id);
      else if (x.decision === "no")
        rejections.push({ id, reasons: x.reasons.length ? x.reasons : ["WANT_OTHER"], note: "" });
    }
    // Nothing marked → treat "fresh pitches" as "show me others".
    if (!accepted.length && !rejections.length) {
      (prep?.pitches || []).forEach((p) => rejections.push({ id: p.id, reasons: ["WANT_OTHER"], note: "" }));
    }
    setBusy(true);
    try {
      const p = await api.sendFeedback(code, accepted, rejections);
      setPrep(p);
      setMarks(initMarks(p));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    const p = await api.reset(code);
    setPrep(p);
    setMarks(initMarks(p));
  }

  if (err)
    return (
      <main className="mx-auto min-h-screen w-full max-w-md px-5 pt-12">
        <Link href="/" className="text-sm font-medium text-primary">‹ Back</Link>
        <p className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">Couldn’t load this account.</p>
      </main>
    );
  if (!prep)
    return <main className="mx-auto min-h-screen w-full max-w-md px-5 pt-12 text-muted-foreground">Loading…</main>;

  const a = prep.account;
  const pitches = prep.pitches;
  const decided = pitches.filter((p) => marks[p.id]?.decision).length;
  const anyNo = pitches.some((p) => marks[p.id]?.decision === "no");

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-32">
      {/* header */}
      <header className="pt-12">
        <Link
          href="/"
          className="grid size-10 place-items-center rounded-full bg-card text-xl text-foreground ring-1 ring-border transition active:scale-95"
          aria-label="Back to accounts"
        >
          ‹
        </Link>

        <div className="mt-5 flex items-start gap-3">
          <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-secondary text-2xl ring-1 ring-primary/25">
            <span aria-hidden>{a.emoji}</span>
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-[26px] font-semibold leading-[1.1] tracking-[-0.02em] text-balance text-foreground">
              {a.name}
            </h1>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${toneCls(a.tone)}`}>
                {a.status}
              </span>
              {a.alerts?.map((al, i) => (
                <span key={i} className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${toneCls(al.tone)}`}>
                  <span aria-hidden>{al.icon}</span> {al.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* stats */}
      <section className="mt-6 grid grid-cols-3 gap-2.5" aria-label="Key stats">
        {prep.stats.map((s, i) => (
          <div key={i} className="rounded-2xl border border-border bg-card p-3 text-center shadow-[0_6px_18px_-16px_rgba(33,29,23,0.5)]">
            <div className="font-serif text-[19px] font-semibold leading-none text-foreground">{s.value}</div>
            <div className="mt-1.5 text-[11px] font-medium leading-tight text-muted-foreground">{s.label}</div>
          </div>
        ))}
      </section>

      {/* what's going on */}
      <section className="mt-4 rounded-3xl border border-border bg-card p-4 shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)]">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">What&apos;s going on</h2>
        <ul className="mt-3 flex flex-col gap-2.5">
          {prep.highlights.map((h, i) => (
            <li key={i} className="flex items-center gap-3 text-[15px] leading-snug text-foreground">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-base" aria-hidden>{h.icon}</span>
              <span className="text-pretty">{h.label}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* what I've learned */}
      {prep.learned.length > 0 && (
        <motion.section layout className="mt-4 rounded-2xl border border-primary/25 bg-secondary/60 p-3.5">
          <div className="flex items-center gap-2">
            <span className="text-sm" aria-hidden>📚</span>
            <h2 className="text-[13px] font-semibold text-primary">What I&apos;ve learned</h2>
            <button onClick={reset} className="ml-auto text-[12px] font-semibold text-muted-foreground transition active:text-foreground">
              ↺ reset
            </button>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {prep.learned.map((c, i) => (
              <span key={i} className="rounded-full bg-card px-2.5 py-1 text-[12px] font-medium text-secondary-foreground ring-1 ring-border">
                <span aria-hidden>{c.icon}</span> {c.label}
              </span>
            ))}
          </div>
        </motion.section>
      )}

      {/* pitches */}
      <section className="mt-7">
        <div className="flex items-baseline justify-between">
          <h2 className="font-serif text-[20px] font-semibold tracking-[-0.01em] text-foreground">3 ways to pitch</h2>
          <span className="text-[12px] font-medium text-muted-foreground">{decided}/{pitches.length} picked</span>
        </div>
        <p className="mt-1 text-[14px] leading-relaxed text-muted-foreground">Keep the good ones, skip the rest.</p>

        <div className="mt-4 flex flex-col gap-3.5">
          {pitches.length === 0 ? (
            <p className="rounded-3xl border border-border bg-card p-6 text-center text-[15px] text-muted-foreground">
              🎉 That’s every idea for now — tap <button onClick={reset} className="font-semibold text-primary">start over</button> to reset.
            </p>
          ) : (
            pitches.map((p, i) => (
              <Pitch
                key={p.id}
                pitch={p}
                index={i}
                reasons={reasons}
                mark={marks[p.id]}
                onDecision={setDecision}
                onToggleReason={toggleReason}
              />
            ))
          )}
        </div>
      </section>

      {/* sticky action */}
      <div className="fixed inset-x-0 bottom-0 z-10">
        <div className="mx-auto max-w-md bg-gradient-to-t from-background via-background to-transparent px-5 pb-6 pt-8">
          <button
            type="button"
            onClick={refresh}
            disabled={busy}
            className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-primary text-[16px] font-semibold text-primary-foreground shadow-[0_12px_30px_-12px_rgba(154,107,31,0.7)] transition active:scale-[0.99] disabled:opacity-60"
          >
            {busy ? (
              <>Working…</>
            ) : anyNo ? (
              <><span aria-hidden>✨</span> Show me 3 fresh pitches</>
            ) : decided > 0 ? (
              <><span aria-hidden>✅</span> Save picks &amp; show 3 more</>
            ) : (
              <><span aria-hidden>✨</span> Show me 3 fresh pitches</>
            )}
          </button>
        </div>
      </div>
    </main>
  );
}
