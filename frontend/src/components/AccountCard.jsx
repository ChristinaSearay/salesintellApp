import Link from "next/link";
import { toneCls } from "@/lib/ui";

export default function AccountCard({ account: a }) {
  return (
    <Link
      href={`/visit/${a.code}`}
      className="flex items-center gap-3 rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm transition active:scale-[0.99]"
    >
      <div className="min-w-0 flex-1">
        <div className="text-[17px] font-semibold leading-tight">{a.name}</div>
        <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium">
          <span className={`rounded-full px-2.5 py-1 ring-1 ${toneCls(a.status.tone)}`}>
            {a.emoji} {a.status.label}
          </span>
          {a.alerts.map((al, i) => (
            <span key={i} className={`rounded-full px-2.5 py-1 ring-1 ${toneCls(al.tone)}`}>
              {al.icon} {al.label}
            </span>
          ))}
        </div>
      </div>
      <span className="text-2xl font-light text-neutral-300">›</span>
    </Link>
  );
}
