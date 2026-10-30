"use client";

// Photos on a customer's profile — shopfront, displays, whose stock sits next
// to ours — so the next visit (or the call on whether to go back) starts from
// what the shop actually looks like. Shrunk on the phone before upload
// (lib/photo.js); stored by the engine (utils/photos.py).

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { PHOTO, shrinkPhoto } from "@/lib/photo";

export default function PhotoGallery({ code, shopName }) {
  const [photos, setPhotos] = useState(null);
  const [draft, setDraft] = useState(null);       // { image, thumb, preview }
  const [caption, setCaption] = useState("");
  const [viewing, setViewing] = useState(null);   // a photo from the list
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const picker = useRef(null);

  useEffect(() => {
    api.getPhotos(code).then(setPhotos).catch((e) => setErr(String(e.message || e)));
  }, [code]);

  async function pick(e) {
    const file = e.target.files?.[0];
    e.target.value = "";            // picking the same photo again still fires
    if (!file) return;
    setErr(null);
    try {
      setDraft(await shrinkPhoto(file));
    } catch (ex) {
      setErr(String(ex.message || ex));
    }
  }

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      setPhotos(await api.addPhoto(code, draft.image, draft.thumb, caption.trim()));
      setDraft(null);
      setCaption("");
    } catch (ex) {
      setErr(String(ex.message || ex));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      setPhotos(await api.deletePhoto(code, viewing.id));
      close();
    } catch (ex) {
      setErr(String(ex.message || ex));
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setViewing(null);
    setConfirmDelete(false);
  }

  const count = photos?.length || 0;

  return (
    <section className="mt-4 rounded-3xl border border-border bg-card p-4 shadow-[0_8px_24px_-18px_rgba(33,29,23,0.5)]">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Photos</h2>
        {count > 0 && <span className="text-[12px] font-medium text-muted-foreground">{count}</span>}
      </div>

      {photos && count === 0 && !draft && (
        <p className="mt-2 text-[13px] leading-snug text-muted-foreground">
          Snap the shopfront or how our stock is displayed — handy when deciding whether to go back.
        </p>
      )}

      {count > 0 && (
        <ul className="mt-3 grid grid-cols-3 gap-2">
          {photos.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => setViewing(p)}
                className="block aspect-square w-full overflow-hidden rounded-xl bg-secondary ring-1 ring-border transition active:scale-[0.98]"
                aria-label={p.caption || `Photo from ${p.when}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.thumb} alt="" loading="lazy" className="size-full object-cover" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {draft ? (
        <div className="mt-3.5 border-t border-border pt-3.5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={draft.preview} alt="" className="max-h-64 w-full rounded-xl object-contain bg-secondary" />
          <input
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            maxLength={PHOTO.MAX_CAPTION}
            placeholder={`Caption (optional) — e.g. "Our cabinet by the door at ${shopName}"`}
            className="mt-2.5 h-11 w-full rounded-xl border border-border bg-background px-3 text-[16px] text-foreground outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-primary/30"
          />
          {err && <p className="mt-1.5 text-[13px] font-medium text-danger">{err}</p>}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={save}
              disabled={busy}
              className="h-11 flex-1 rounded-xl bg-primary text-[14px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:opacity-50"
            >
              {busy ? "Uploading…" : "Save photo"}
            </button>
            <button
              type="button"
              onClick={() => { setDraft(null); setCaption(""); setErr(null); }}
              disabled={busy}
              className="h-11 rounded-xl px-4 text-[14px] font-semibold text-muted-foreground ring-1 ring-border"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          {err && <p className="mt-2 text-[13px] font-medium text-danger">{err}</p>}
          <button
            type="button"
            onClick={() => picker.current?.click()}
            className="mt-3.5 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-secondary/70 text-[14px] font-semibold text-foreground ring-1 ring-primary/25 transition active:scale-[0.99]"
          >
            <span aria-hidden>📷</span> Add photo
          </button>
        </>
      )}
      {/* accept="image/*" gives a phone the camera or the library; iPhones hand
          over HEIC shots as JPEG through this input. */}
      <input ref={picker} type="file" accept="image/*" onChange={pick} className="hidden" />

      {viewing && (
        <div
          className="fixed inset-0 z-30 flex flex-col bg-black px-4 pb-6 pt-12"
          role="dialog"
          aria-modal="true"
          onClick={close}
        >
          <div className="mx-auto flex w-full max-w-md flex-1 flex-col" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              onClick={close}
              className="ml-auto grid size-10 place-items-center rounded-full bg-white/10 text-xl text-white"
              aria-label="Close"
            >
              ✕
            </button>
            <div className="mt-3 flex min-h-0 flex-1 items-center justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={viewing.src} alt={viewing.caption} className="max-h-full max-w-full rounded-xl object-contain" />
            </div>
            {viewing.caption && <p className="mt-3 text-[15px] leading-snug text-white">{viewing.caption}</p>}
            <p className="mt-1 text-[12px] text-white/60">{viewing.when}</p>
            <button
              type="button"
              onClick={() => (confirmDelete ? remove() : setConfirmDelete(true))}
              disabled={busy}
              className={`mt-3 h-11 w-full rounded-xl text-[14px] font-semibold transition active:scale-[0.99] disabled:opacity-50 ${
                confirmDelete ? "bg-danger text-danger-foreground" : "bg-white/10 text-white"
              }`}
            >
              {busy ? "Deleting…" : confirmDelete ? "Tap again to delete" : "🗑 Delete photo"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
