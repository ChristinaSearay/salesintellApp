"use client";

import { useEffect, useState } from "react";
import { api, PROSPECT_OUTCOME } from "@/lib/api";

// A business a rep visited that isn't in Unleashed yet. We check for
// near-duplicates first and show them, so "Temple of the Sun" can't quietly
// become a second record for a shop we already have. Creating is one tap,
// but always the rep's tap — nothing reaches the ERP on its own.
export default function NewCustomer({ name, onCreated, onLink }) {
  const [check, setCheck] = useState(null);
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [contact, setContact] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let live = true;
    api.checkProspect(name)
      .then((c) => { if (live) { setCheck(c); setCode(c.suggestedCode); } })
      .catch((e) => { if (live) setErr(String(e.message || e)); });
    return () => { live = false; };
  }, [name]);

  const create = async () => {
    setBusy(true);
    setErr(null);
    try {
      const made = await api.createProspect({
        name, code, contactName: contact, phone, email,
      });
      onCreated(made);
    } catch (e) {
      setErr(String(e.message || e));
      setBusy(false);
    }
  };

  if (err && !check) {
    return <p className="mt-2 text-[13px] font-medium text-danger">{err}</p>;
  }
  if (!check) {
    return <p className="mt-2 text-[12px] text-muted-foreground">Checking Unleashed…</p>;
  }

  const exists = check.outcome === PROSPECT_OUTCOME.EXISTS;
  const maybe = check.outcome === PROSPECT_OUTCOME.POSSIBLE_DUPLICATE;

  return (
    <div className="mt-2.5 rounded-2xl bg-secondary/60 p-3">
      {(exists || maybe) && (
        <>
          <p className="text-[12.5px] font-semibold text-foreground">
            {exists ? "We already have this customer:" : "This might be one we already have:"}
          </p>
          <div className="mt-1.5 flex flex-col gap-1.5">
            {check.matches.map((m) => (
              <button
                key={m.code}
                type="button"
                onClick={() => onLink(m.code)}
                className="flex items-center justify-between gap-2 rounded-xl bg-card px-3 py-2 text-left text-[13px] ring-1 ring-border transition active:scale-[0.99]"
              >
                <span className="min-w-0 truncate font-medium text-foreground">{m.name}</span>
                <span className="shrink-0 text-[11px] font-semibold text-primary">Use this one</span>
              </button>
            ))}
          </div>
        </>
      )}

      {!exists && (
        <>
          {maybe && (
            <p className="mt-2.5 text-[12px] text-muted-foreground">None of these? Create it as new:</p>
          )}
          {!open ? (
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="mt-2 flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-card text-[13.5px] font-semibold text-foreground ring-1 ring-primary/25 transition active:scale-[0.99]"
            >
              <span aria-hidden>➕</span> Create “{name}” in Unleashed
            </button>
          ) : (
            <div className="mt-2 flex flex-col gap-2">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Customer code
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value.toUpperCase())}
                  className="mt-1 h-10 w-full rounded-xl border border-border bg-background px-3 text-[15px] font-normal normal-case tracking-normal text-foreground outline-none focus:ring-2 focus:ring-primary/30"
                />
              </label>
              <input
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder="Contact name (optional)"
                className="h-10 w-full rounded-xl border border-border bg-background px-3 text-[15px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
              />
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                inputMode="tel"
                placeholder="Mobile (optional)"
                className="h-10 w-full rounded-xl border border-border bg-background px-3 text-[15px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
              />
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                inputMode="email"
                placeholder="Email (optional)"
                className="h-10 w-full rounded-xl border border-border bg-background px-3 text-[15px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
              />
              {err && <p className="text-[13px] font-medium text-danger">{err}</p>}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={create}
                  disabled={busy || !code.trim()}
                  className="h-10 flex-1 rounded-xl bg-primary text-[13.5px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:opacity-50"
                >
                  {busy ? "Creating…" : "Create in Unleashed"}
                </button>
                <button
                  type="button"
                  onClick={() => { setOpen(false); setErr(null); }}
                  disabled={busy}
                  className="h-10 rounded-xl px-3 text-[13.5px] font-semibold text-muted-foreground ring-1 ring-border"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
