"use client";

// Screen 2 — Visit prep. Live data + the accept/reject → re-suggest learning
// loop, all driven by api.js (which talks to the Python engine). A functional
// starting point; restyle with v0 later.

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
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

export default function VisitPage() {
  const { code } = useParams();
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

  const anyNo = Object.values(marks).some((x) => x.decision === "no");

  async function submit() {
    const accepted = [];
    const rejections = [];
    for (const [id, x] of Object.entries(marks)) {
      if (x.decision === "good") accepted.push(id);
      else if (x.decision === "no") rejections.push({ id, reasons: x.reasons.length ? x.reasons : ["WANT_OTHER"], note: "" });
    }
    if (!accepted.length && !rejections.length) return;
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

  if (err) {
    return (
      <main className="mx-auto min-h-screen max-w-md bg-neutral-50 p-5">
        <Link href="/" className="text-sm text-emerald-700">‹ Back</Link>
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">Couldn’t load ({err}).</p>
      </main>
    );
  }
  if (!prep) {
    return <main className="mx-auto min-h-screen max-w-md bg-neutral-50 p-5 text-neutral-400">Loading…</main>;
  }

  const a = prep.account;

  return (
    <main className="mx-auto min-h-screen max-w-md bg-neutral-50 pb-28">
      <header className="bg-gradient-to-br from-emerald-700 to-emerald-900 px-4 pb-5 pt-11 text-white">
        <div className="flex items-center gap-2">
          <Link href="/" className="grid h-9 w-9 place-items-center rounded-full bg-white/15 text-xl">‹</Link>
          <div className="min-w-0">
            <div className="truncate text-lg font-bold">{a.name}</div>
            <div className="truncate text-[13px] text-emerald-100/90">{a.emoji} {a.status.label}</div>
          </div>
        </div>
      </header>

      <div className="space-y-5 p-4">
        {/* stats */}
        <div className="grid grid-cols-3 gap-2">
          {prep.stats.map((s, i) => (
            <div key={i} className="rounded-2xl border border-neutral-200 bg-white p-3 text-center shadow-sm">
              <div className="text-[17px] font-extrabold leading-none">{s.value}</div>
              <div className="mt-1 text-[11px] font-medium text-neutral-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* what's going on */}
        <section className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap gap-2">
            {prep.highlights.map((h, i) => (
              <span key={i} className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold text-neutral-700">
                {h.icon} {h.label}
              </span>
            ))}
          </div>
          {prep.story && <p className="text-sm leading-relaxed text-neutral-600">{prep.story}</p>}
        </section>

        {/* learned */}
        {prep.learned.length > 0 && (
          <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-bold text-emerald-800">📚 What I’ve learned</span>
              <button onClick={reset} className="text-[13px] font-semibold text-emerald-700">↺ Start over</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {prep.learned.map((c, i) => (
                <span key={i} className="rounded-full border border-emerald-200 bg-white px-2.5 py-1 text-xs font-semibold">
                  {c.icon} {c.label}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* pitches */}
        <div>
          <h2 className="text-lg font-bold">3 things to pitch</h2>
          <p className="text-sm text-neutral-500">Keep the good ones 👍, swap the rest 👎.</p>
        </div>

        <div className="space-y-4">
          {prep.pitches.length === 0 ? (
            <p className="rounded-2xl border border-neutral-200 bg-white p-6 text-center text-neutral-500">
              🎉 That’s every idea for now — tap “Start over” to reset.
            </p>
          ) : (
            prep.pitches.map((p, i) => (
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
      </div>

      {/* sticky action */}
      <div className="fixed inset-x-0 bottom-0 mx-auto max-w-md bg-gradient-to-t from-neutral-50 via-neutral-50 to-transparent p-4">
        <button
          onClick={submit}
          disabled={busy}
          className={`h-14 w-full rounded-2xl text-[17px] font-bold text-white shadow-lg transition disabled:opacity-60 ${
            anyNo ? "bg-emerald-700 active:bg-emerald-800" : "bg-amber-600 active:bg-amber-700"
          }`}
        >
          {busy ? "Thinking…" : anyNo ? "✨ Show me 3 better" : "✅ Save these 3"}
        </button>
      </div>
    </main>
  );
}
