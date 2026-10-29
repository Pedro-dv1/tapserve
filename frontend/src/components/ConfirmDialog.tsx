import { useRef, useState } from 'react';
import Modal from './Modal';

export default function ConfirmDialog({ title, description, label, confirm, close, destructive = true }: { title: string; description: string; label: string; confirm: (reason: string) => Promise<void>; close: () => void; destructive?: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submitting = useRef(false);
  return <Modal open title={title} description={description} busy={busy} close={close}><form onSubmit={event => {
    event.preventDefault(); if (submitting.current) return;
    const reason = String(new FormData(event.currentTarget).get('reason') ?? '');
    submitting.current = true; setBusy(true); setError('');
    void confirm(reason).then(close).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Não foi possível concluir.')).finally(() => { submitting.current = false; setBusy(false); });
  }} aria-busy={busy}><label>Motivo (opcional)<input name="reason" maxLength={300} disabled={busy} /></label>{error && <p role="alert" className="error">{error}</p>}<div className="dialog-actions"><button type="button" className="secondary" disabled={busy} onClick={close}>Voltar</button><button type="submit" className={destructive ? 'ui-danger' : ''} disabled={busy}>{busy ? 'Confirmando…' : label}</button></div></form></Modal>;
}
