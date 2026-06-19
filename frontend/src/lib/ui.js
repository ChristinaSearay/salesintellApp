// Shared tone → Tailwind class mapping for status pills / alert chips.
// All colours come from the design tokens defined in globals.css.
export const TONE = {
  good: "bg-good-soft text-good",
  warn: "bg-warn-soft text-warn",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
  cold: "bg-secondary text-muted-foreground",
  neutral: "bg-muted text-muted-foreground",
};

export const toneCls = (t) => TONE[t] || TONE.neutral;
