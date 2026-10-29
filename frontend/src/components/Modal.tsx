import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Icon } from './Interface';

export default function Modal({ open, title, description, busy = false, close, children, className = '', guardChanges = false }: { open: boolean; title: string; description?: string; busy?: boolean; close: () => void; children: ReactNode; className?: string; guardChanges?: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useId(); const details = useId();
  const [dirty, setDirty] = useState(false);
  const [discard, setDiscard] = useState(false);
  function requestClose() { if (busy) return; if (guardChanges && dirty) setDiscard(true); else close(); }
  useEffect(() => {
    if (!open) return;
    const node = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    setDirty(false); setDiscard(false); node?.showModal(); document.body.style.overflow = 'hidden';
    return () => {
      node?.close(); document.body.style.overflow = overflow;
      const target = trigger?.isConnected ? trigger : document.querySelector<HTMLElement>('.customer-navigation button[aria-current="page"], .back-button');
      target?.focus({ preventScroll: true });
    };
  }, [open]);
  return <dialog ref={dialog} className={`ui-dialog ${className}`} aria-labelledby={heading} aria-describedby={description ? details : undefined} aria-busy={busy} onChangeCapture={() => { if (guardChanges) setDirty(true); }} onCancel={event => { event.preventDefault(); requestClose(); }}><header><h2 id={heading}>{title}</h2><button type="button" className="icon-button" aria-label="Fechar" disabled={busy} onClick={requestClose}><Icon name="close" /></button></header>{description && <p id={details}>{description}</p>}{children}{discard && <div className="discard-changes" role="alert"><p>Descartar as alterações não salvas?</p><div className="dialog-actions"><button className="secondary" type="button" onClick={() => setDiscard(false)}>Continuar editando</button><button className="ui-danger" type="button" onClick={close}>Descartar alterações</button></div></div>}</dialog>;
}
