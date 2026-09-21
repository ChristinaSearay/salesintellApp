"use client";

import { useState } from "react";
import Link from "next/link";
import { api, REASON } from "@/lib/api";

// One customer in the "Needs attention" queue: why they're here, their last
// note, and a note box. Saving a note sends them to the back of the line.
export default function AttentionCard({ account: a, index = 0, onSaved }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [mute, setMute] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const save = async () => {
    setSaving(true);
    setErr(null);
    try {
      onSaved(a, await api.saveNote(a.code, text.trim(), mute), mute);
    } catch (e) {
      setErr(String(e.message || e));
      setSaving(false);
    }
  };

  const overdue = a.reason === REASON.OVERDUE;

  return (
    <article
      style={{ animationDelay: `${index * 70}ms` }}
      className="animate-rise relative overflow-hidden rounded-3xl border border-border bg-card p-4 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_8px_24px_-16px_rgba(33,29,23,0.45)]"
    >
      {overdue && <span className="absolute left-0 top-0 h-full w-1 bg-danger/80" aria-hidden />}

      <Link href={`/visit/${a.code}`} className="group flex items-center gap-3.5 transition active:scale-[0.985]">
        <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-secondary text-2xl ring-1 ring-primary/25">
          <span aria-hidden>{a.emoji}</span>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-serif text-[19px] font-semibold leading-tight tracking-[-0.01em] text-foreground">
            {a.name}
          </h3>
          {a.meta && <p className="mt-0.5 truncate text-[12px] text-muted-foreground">{a.meta}</p>}
        </div>
        <span className="text-2xl font-light text-muted-foreground transition group-active:translate-x-0.5" aria-hidden>
          ›
        </span>
      </Link>

      <p className={`mt-3 flex gap-2 text-[14px] font-semibold leading-snug ${overdue ? "text-danger" : "text-foreground"}`}>
        <span aria-hidden>{overdue ? "⏰" : "📋"}</span>
        <span>{a.why}</span>
      </p>

      {a.lastNote && (
        <p className="mt-2 rounded-2xl bg-secondary/60 px-3 py-2 text-[13px] leading-relaxed text-muted-foreground">
          <span className="font-semibold text-foreground">Last note · {a.lastNote.when}:</span> {a.lastNote.text}
        </p>
      )}

      {open ? (
        <div className="mt-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            autoFocus
            placeholder="What happened? What's working, what isn't…"
            className="w-full rounded-2xl border border-border bg-background p-3 text-[16px] leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
          />

          {/* Two accounts for one shop — a buying-group one they rarely use and
              their own — means some accounts are permanently quiet. Muting is
              per account and lifts itself when an order lands on it. */}
          <label className="mt-2 flex cursor-pointer items-start gap-2.5 rounded-2xl bg-secondary/60 px-3 py-2.5">
            <input
              type="checkbox"
              checked={mute}
              onChange={(e) => setMute(e.target.checked)}
              className="mt-0.5 size-4 shrink-0 accent-[var(--color-primary)]"
            />
            <span className="text-[13px] leading-snug text-foreground">
              <span className="font-semibold">Don’t alert me about this account again</span>
              <span className="block text-[12px] text-muted-foreground">
                Until an order is placed on it — then reminders go back to normal.
              </span>
            </span>
          </label>

          {err && <p className="mt-1.5 text-[13px] font-medium text-danger">{err}</p>}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={save}
              disabled={saving || !text.trim()}
              className="h-11 flex-1 rounded-xl bg-primary text-[14px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:opacity-50"
            >
              {saving ? "Saving…" : mute ? "Save note · stop alerts" : "Save note · next customer"}
            </button>
            <button
              type="button"
              onClick={() => { setOpen(false); setErr(null); }}
              disabled={saving}
              className="h-11 rounded-xl px-4 text-[14px] font-semibold text-muted-foreground ring-1 ring-border"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-secondary text-[14px] font-semibold text-foreground ring-1 ring-primary/25 transition active:scale-[0.99]"
        >
          <span aria-hidden>📝</span> Add a note
        </button>
      )}
    </article>
  );
}
