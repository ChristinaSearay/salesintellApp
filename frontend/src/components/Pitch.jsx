"use client";

export default function Pitch({ pitch: p, index, reasons, mark, onDecision, onToggleReason }) {
  const decision = mark?.decision;
  const selected = mark?.reasons || [];

  const border =
    decision === "good" ? "border-emerald-400 ring-2 ring-emerald-100"
    : decision === "no" ? "border-red-200"
    : "border-neutral-200";

  return (
    <article className={`overflow-hidden rounded-2xl border bg-white shadow-sm transition ${border}`}>
      <div className="p-4">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wide text-amber-600">Pitch {index + 1}</span>
          <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-emerald-700">
            {p.badge}
          </span>
          {decision === "good" && <span className="ml-auto">✅</span>}
          {decision === "no" && <span className="ml-auto">🚫</span>}
        </div>

        <h3 className="mt-2 text-[17px] font-bold leading-snug">{p.title}</h3>
        {p.blurb && <p className="mt-1 text-sm leading-relaxed text-neutral-600">{p.blurb}</p>}

        {p.products?.length > 0 && (
          <ul className="mt-3 space-y-2">
            {p.products.map((pr, i) => (
              <li key={i} className="flex items-center gap-2.5 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <span className={`h-2 w-2 shrink-0 rounded-full ${pr.inStock ? "bg-emerald-500" : "bg-amber-500"}`} />
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{pr.name}</span>
                <span className="whitespace-nowrap text-sm font-bold">{pr.price}</span>
              </li>
            ))}
          </ul>
        )}

        {p.offer && (
          <div className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-[13px] leading-snug text-amber-800">🎁 {p.offer}</div>
        )}
      </div>

      <div className="grid grid-cols-2 border-t border-neutral-200">
        <button
          onClick={() => onDecision(p.id, "good")}
          className={`min-h-[52px] font-bold transition ${decision === "good" ? "bg-emerald-50 text-emerald-700" : "text-neutral-500"}`}
        >
          👍 Good
        </button>
        <button
          onClick={() => onDecision(p.id, "no")}
          className={`min-h-[52px] border-l border-neutral-200 font-bold transition ${decision === "no" ? "bg-red-50 text-red-600" : "text-neutral-500"}`}
        >
          👎 No
        </button>
      </div>

      {decision === "no" && (
        <div className="border-t border-dashed border-red-200 bg-red-50/40 p-4">
          <div className="mb-2 text-sm font-bold">Why not?</div>
          <div className="grid grid-cols-2 gap-2">
            {reasons.map((r) => {
              const on = selected.includes(r.name);
              return (
                <button
                  key={r.name}
                  onClick={() => onToggleReason(p.id, r.name)}
                  className={`min-h-[46px] rounded-xl border px-3 text-left text-[13px] font-semibold transition ${
                    on ? "border-red-400 bg-red-100 text-red-700" : "border-neutral-200 bg-white text-neutral-700"
                  }`}
                >
                  {r.icon} {r.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </article>
  );
}
