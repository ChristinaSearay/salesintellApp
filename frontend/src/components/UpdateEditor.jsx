"use client";

// Edit the words of a summarised update — its bullets and the next move — so
// a rep can fix a misspelt name or a wrong detail before (or after) it lands
// in "What's going on". Clearing a bullet drops it.

const FIELD =
  "w-full resize-none rounded-xl border border-border bg-background p-2.5 text-[14.5px] leading-snug text-foreground outline-none focus:ring-2 focus:ring-primary/30";

// Grow with the text so a long bullet is readable on a phone.
const rowsFor = (text) => Math.max(2, Math.ceil((text || "").length / 34));

export default function UpdateEditor({ hooks, advice, onChange }) {
  const setHook = (i, text) => onChange({ hooks: hooks.map((h, j) => (j === i ? text : h)), advice });

  return (
    <div className="mt-3 flex flex-col gap-2">
      {hooks.map((h, i) => (
        <textarea
          key={i}
          value={h}
          onChange={(e) => setHook(i, e.target.value)}
          rows={rowsFor(h)}
          aria-label={`Update line ${i + 1}`}
          className={FIELD}
        />
      ))}
      <button
        type="button"
        onClick={() => onChange({ hooks: [...hooks, ""], advice })}
        className="self-start text-[12.5px] font-semibold text-primary"
      >
        + Add a line
      </button>
      <label className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        Next move
      </label>
      <textarea
        value={advice}
        onChange={(e) => onChange({ hooks, advice: e.target.value })}
        rows={rowsFor(advice)}
        className={FIELD}
      />
    </div>
  );
}
