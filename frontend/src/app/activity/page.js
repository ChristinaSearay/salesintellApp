"use client";

// Team activity — every note and update the sales team has saved, across all
// customers, newest first and grouped by day: who was contacted, and when.
// Tap a customer to open their page.

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

// Saved-update sources (constants/intel.py IntelSource).
const SOURCE = {
  manual: { icon: "📝", label: "Note" },
  whatsapp: { icon: "💬", label: "WhatsApp" },
};

const dayKey = (d) => d.toLocaleDateString("en-CA"); // YYYY-MM-DD in local time

function dayLabel(d, now) {
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (dayKey(d) === dayKey(now)) return "Today";
  if (dayKey(d) === dayKey(yesterday)) return "Yesterday";
  return d.toLocaleDateString("en-AU", {
    weekday: "short", day: "numeric", month: "short",
    ...(d.getFullYear() === now.getFullYear() ? {} : { year: "numeric" }),
  });
}

// Newest-first feed → [{ label, items }] per local day, order kept.
function byDay(feed) {
  const now = new Date();
  const days = [];
  for (const item of feed) {
    const d = new Date(item.ts);
    const key = dayKey(d);
    if (days.at(-1)?.key !== key) days.push({ key, label: dayLabel(d, now), items: [] });
    days.at(-1).items.push({ ...item, time: d.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit" }) });
  }
  return days;
}

function Entry({ item }) {
  const src = SOURCE[item.source];
  const name = item.known ? (
    <Link href={`/visit/${item.code}`} className="font-serif text-[17px] font-semibold text-foreground">
      {item.name} <span className="text-primary" aria-hidden>›</span>
    </Link>
  ) : (
    <span className="font-serif text-[17px] font-semibold text-foreground">{item.name}</span>
  );
  return (
    <li className="rounded-2xl border border-border bg-card p-3.5 shadow-[0_8px_24px_-20px_rgba(33,29,23,0.55)]">
      <div className="flex items-baseline justify-between gap-3">
        {name}
        <span className="shrink-0 text-[12px] font-medium text-muted-foreground">{item.time}</span>
      </div>
      {src && (
        <span className="mt-0.5 block text-[11px] font-medium text-muted-foreground">
          <span aria-hidden>{src.icon}</span> {src.label}
        </span>
      )}
      <ul className="mt-2 flex flex-col gap-1 text-[14px] leading-snug text-foreground">
        {item.hooks.map((h, i) => <li key={i}>• {h}</li>)}
      </ul>
      {item.advice && (
        <p className="mt-2 text-[12.5px] leading-snug text-muted-foreground">
          <span className="font-semibold">Next move: </span>{item.advice}
        </p>
      )}
    </li>
  );
}

export default function ActivityPage() {
  const [feed, setFeed] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.getActivity().then(setFeed).catch((e) => setErr(String(e)));
  }, []);

  const customers = feed ? new Set(feed.map((f) => f.code)).size : 0;

  return (
    <main className="mx-auto min-h-screen w-full max-w-md px-5 pb-16">
      <header className="pt-12">
        <Link
          href="/"
          className="grid size-10 place-items-center rounded-full bg-card text-xl text-foreground ring-1 ring-border transition active:scale-95"
          aria-label="Back"
        >
          ‹
        </Link>
        <h1 className="mt-5 font-serif text-[30px] font-semibold leading-[1.05] tracking-[-0.02em] text-foreground">
          Activity
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
          {feed
            ? feed.length
              ? `Notes from the team, most recent first — ${feed.length} note${feed.length === 1 ? "" : "s"} across ${customers} customer${customers === 1 ? "" : "s"}.`
              : "No notes yet. Notes saved on a customer show up here, most recent first."
            : err ? "" : "Loading…"}
        </p>
      </header>

      {err && (
        <p className="mt-6 rounded-2xl bg-danger-soft px-4 py-3 text-[14px] font-medium text-danger">
          Can’t reach the engine. Start it with <code className="font-mono">uv run app</code>.
        </p>
      )}

      {feed && byDay(feed).map((day) => (
        <section key={day.key} className="mt-7" aria-label={day.label}>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {day.label}
          </h2>
          <ul className="mt-2.5 flex flex-col gap-2.5">
            {day.items.map((item) => <Entry key={`${item.code}-${item.id}`} item={item} />)}
          </ul>
        </section>
      ))}
    </main>
  );
}
