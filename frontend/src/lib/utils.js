import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names (used by shadcn/ui + v0 components). */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
