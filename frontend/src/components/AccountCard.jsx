import Link from "next/link";
import { toneCls } from "@/lib/ui";

export default function AccountCard({ account: a, index = 0 }) {
  const flagged = a.alerts?.some((al) => al.tone === "danger");

  return (
    <Link
      href={`/visit/${a.code}`}
      style={{ animationDelay: `${index * 70}ms` }}
      className="animate-rise group relative block overflow-hidden rounded-3xl border border-border bg-card p-4 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_8px_24px_-16px_rgba(33,29,23,0.45)] transition active:scale-[0.985]"
    >
      {/* warm gold edge that hints "needs attention" */}
      {flagged && <span className="absolute left-0 top-0 h-full w-1 bg-danger/80" aria-hidden />}

      <div className="flex items-center gap-3.5">
        <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-secondary text-2xl ring-1 ring-primary/25">
          <span aria-hidden>{a.emoji}</span>
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate font-serif text-[19px] font-semibold leading-tight tracking-[-0.01em] text-foreground">
            {a.name}
          </h3>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${toneCls(a.tone)}`}>
              {a.status}
            </span>
            {a.alerts?.map((al, i) => (
              <span
                key={i}
                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${toneCls(al.tone)}`}
              >
                <span aria-hidden>{al.icon}</span> {al.label}
              </span>
            ))}
          </div>
        </div>

        <span
          className="text-2xl font-light text-muted-foreground transition group-active:translate-x-0.5"
          aria-hidden
        >
          ›
        </span>
      </div>
    </Link>
  );
}
