import { useEffect, useId, useRef } from 'react';
import { Icon } from './Interface';

export default function PendingChanges({ open, busy, keep, discard, save }: { open: boolean; busy: boolean; keep: () => void; discard: () => void; save: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  const heading = useId(), description = useId();
  useEffect(() => {
    const node = panel.current;
    if (!open) { node?.hidePopover(); return; }
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    node?.showPopover(); node?.querySelector<HTMLButtonElement>('[data-continue]')?.focus();
    return () => { node?.hidePopover(); if (trigger?.isConnected) trigger.focus({ preventScroll: true }); };
  }, [open]);
  return <div ref={panel} popover="manual" className="pending-changes" role="dialog" aria-labelledby={heading} aria-describedby={description} aria-busy={busy} onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); if (!busy) keep(); } }}>
    <div className="pending-heading"><Icon name="info" /><strong id={heading}>Alterações não salvas</strong></div>
    <p id={description}>Você modificou algumas informações. Deseja salvar antes de sair?</p>
    <div className="dialog-actions"><button type="button" className="ui-danger" disabled={busy} onClick={discard}>Descartar</button><button data-continue type="button" className="secondary" disabled={busy} onClick={keep}>Continuar editando</button><button type="button" disabled={busy} onClick={save}>{busy ? 'Salvando…' : 'Salvar alterações'}</button></div>
  </div>;
}
