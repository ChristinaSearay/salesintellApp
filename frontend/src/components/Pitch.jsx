"use client";

import { AnimatePresence, motion } from "framer-motion";

const BADGE_TONE = {
  "Save the account": "bg-danger-soft text-danger",
  "Win back": "bg-danger-soft text-danger",
  "Try something new": "bg-info-soft text-info",
  "Add to their order": "bg-good-soft text-good",
  "Protect the order": "bg-warn-soft text-warn",
  "Build trust": "bg-secondary text-secondary-foreground",
};

export default function Pitch({ pitch: p, index, reasons, mark, onDecision, onToggleReason }) {
  const decision = mark?.decision;
  const selected = mark?.reasons || [];

  const ring =
    decision === "good"
      ? "border-good/45 ring-2 ring-good/15"
      : decision === "no"
        ? "border-danger/30 ring-2 ring-danger/10"
        : "border-border";

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
      className={`overflow-hidden rounded-3xl border bg-card shadow-[0_8px_24px_-18px_rgba(33,29,23,0.55)] transition-colors ${ring}`}
    >
      <div className="p-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] font-semibold text-muted-foreground">
            0{index + 1}
          </span>
          <span
            className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
              BADGE_TONE[p.badge] || "bg-secondary text-secondary-foreground"
            }`}
          >
            {p.badge}
          </span>
          {decision === "good" && (
            <span className="ml-auto text-sm" aria-label="accepted">
              👍
            </span>
          )}
          {decision === "no" && (
            <span className="ml-auto text-sm" aria-label="rejected">
              👎
            </span>
          )}
        </div>

        <h3 className="mt-2.5 font-serif text-[18px] font-semibold leading-snug tracking-[-0.01em] text-foreground text-pretty">
          {p.title}
        </h3>

        {p.products?.length > 0 && (
          <ul className="mt-3 flex flex-col gap-2">
            {p.products.map((pr, i) => (
              <li
                key={i}
                className="flex items-center gap-2.5 rounded-2xl border border-border bg-background/60 px-3 py-2.5"
              >
                <span
                  className={`size-2 shrink-0 rounded-full ${pr.inStock ? "bg-good" : "bg-warn"}`}
                  aria-hidden
                />
                <span className="min-w-0 flex-1 truncate text-[14px] font-medium text-foreground">
                  {pr.name}
                </span>
                <span className="whitespace-nowrap font-serif text-[15px] font-semibold text-foreground">
                  {pr.price}
                </span>
              </li>
            ))}
          </ul>
        )}

        {p.offer && (
          <div className="mt-3 flex gap-2 rounded-2xl bg-warn-soft px-3 py-2.5 text-[13px] font-medium leading-snug text-warn">
            <span aria-hidden>🎁</span>
            <span>{p.offer}</span>
          </div>
        )}
      </div>

      {/* decision buttons */}
      <div className="grid grid-cols-2 gap-px bg-border">
        <button
          type="button"
          onClick={() => onDecision(p.id, "good")}
          className={`flex min-h-[54px] items-center justify-center gap-2 text-[15px] font-semibold transition ${
            decision === "good"
              ? "bg-good text-good-foreground"
              : "bg-card text-muted-foreground active:bg-good-soft"
          }`}
        >
          <span aria-hidden>👍</span> Pitch it
        </button>
        <button
          type="button"
          onClick={() => onDecision(p.id, "no")}
          className={`flex min-h-[54px] items-center justify-center gap-2 text-[15px] font-semibold transition ${
            decision === "no"
              ? "bg-danger text-danger-foreground"
              : "bg-card text-muted-foreground active:bg-danger-soft"
          }`}
        >
          <span aria-hidden>👎</span> Skip
        </button>
      </div>

      {/* reject reasons */}
      <AnimatePresence initial={false}>
        {decision === "no" && (
          <motion.div
            key="reasons"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t border-border bg-background/50"
          >
            <div className="p-4">
              <div className="mb-2.5 text-[13px] font-semibold text-foreground">
                Quick — why skip it?
              </div>
              <div className="flex flex-wrap gap-2">
                {reasons.map((r) => {
                  const on = selected.includes(r.name);
                  return (
                    <button
                      key={r.name}
                      type="button"
                      onClick={() => onToggleReason(p.id, r.name)}
                      className={`rounded-full px-3 py-1.5 text-[13px] font-medium transition ${
                        on
                          ? "bg-danger text-danger-foreground"
                          : "bg-card text-secondary-foreground ring-1 ring-border active:bg-secondary"
                      }`}
                    >
                      <span aria-hidden>{r.icon}</span> {r.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}
