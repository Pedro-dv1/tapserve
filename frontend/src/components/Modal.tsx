import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { Icon } from './Interface';
import { usePendingChanges } from '../lib/usePendingChanges';
import PendingChanges from './PendingChanges';

export default function Modal({ open, title, description, busy = false, close, children, className = '', guardChanges = false }: { open: boolean; title: string; description?: string; busy?: boolean; close: () => void; children: ReactNode; className?: string; guardChanges?: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useId(); const details = useId();
  const pending = usePendingChanges(dialog, open && guardChanges, busy, close);
  function requestClose() { if (!busy) pending.requestLeave(); }
  useEffect(() => {
    if (!open) return;
    const node = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    node?.showModal(); document.body.style.overflow = 'hidden';
    return () => {
      node?.close(); document.body.style.overflow = overflow;
      const target = trigger?.isConnected ? trigger : document.querySelector<HTMLElement>('.customer-navigation button[aria-current="page"], .back-button');
      target?.focus({ preventScroll: true });
    };
  }, [open]);
  return <dialog ref={dialog} className={`ui-dialog ${className}`} aria-labelledby={heading} aria-describedby={description ? details : undefined} aria-busy={busy} data-dirty={pending.dirty} onCancel={event => { event.preventDefault(); if (pending.visible) pending.continueEditing(); else requestClose(); }}><header><h2 id={heading}>{title}</h2><button type="button" className="icon-button" aria-label="Fechar" disabled={busy || pending.savingBeforeLeave} onClick={requestClose}><Icon name="close" /></button></header>{description && <p id={details}>{description}</p>}{children}{guardChanges && <PendingChanges open={pending.visible} busy={busy || pending.savingBeforeLeave} keep={pending.continueEditing} discard={pending.discard} save={() => { void pending.saveAndLeave(); }} />}</dialog>;
}
