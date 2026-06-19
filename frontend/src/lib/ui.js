// Shared tone → Tailwind class mapping for status pills / alerts.
export const TONE = {
  good: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warn: "bg-amber-50 text-amber-700 ring-amber-200",
  danger: "bg-red-50 text-red-700 ring-red-200",
  info: "bg-blue-50 text-blue-700 ring-blue-200",
  cold: "bg-slate-100 text-slate-600 ring-slate-200",
  neutral: "bg-neutral-100 text-neutral-600 ring-neutral-200",
};

export const toneCls = (t) => TONE[t] || TONE.neutral;
