import { formSaveResult, requestEditorClose } from '../../lib/formChanges';
import { useSuccessToast } from '../../components/Toast';
import { randomUUID } from '../../lib/uuid.ts';
import { useEffect, useRef, useState } from 'react';
import { ApiError, record, request } from '../../lib/api';
import { useRealtime } from '../../lib/useRealtime';
import { ErrorState, LoadingSkeleton } from '../../components/Interface';
import { ConnectionStatus, Editor, PageHeader, Pagination, StatusTag } from './StaffUI';
import { StatusAction } from './Operation';
import { decodeWorkItems, elapsedMinutes } from './workItems';
import type { WorkItem } from './workItems';
import { FulfillmentBadge } from '../../components/Fulfillment';

const columns = [{ label: 'Novos', states: ['NEW', 'ACCEPTED'] }, { label: 'Em preparo', states: ['PREPARING'] }, { label: 'Prontos', states: ['READY'] }];
const nextStatus: Record<string, { status: string; label: string }> = { NEW: { status: 'ACCEPTED', label: 'Aceitar item' }, ACCEPTED: { status: 'PREPARING', label: 'Iniciar preparo' }, PREPARING: { status: 'READY', label: 'Marcar pronto' } };
export function ProductionCard({ item, now, refresh }: { item: WorkItem; now: number; refresh: () => void }) {
  const action = nextStatus[item.status];
  return <article className="production-card"><header><h3>{item.points.join(' + ')}</h3><span className="staff-kds-age">{elapsedMinutes(item.created_at, now)} min de espera</span></header><strong className="staff-kds-product">{item.quantity} × {item.name}</strong><div className="staff-item-meta"><FulfillmentBadge mode={item.fulfillment_mode} /><span>{item.sector_name}</span>{item.participant_name && <span>Para {item.participant_name}</span>}<StatusTag attention={item.status === 'NEW'}>{item.status === 'NEW' ? 'Novo item' : item.status === 'ACCEPTED' ? 'Aceito' : item.status === 'PREPARING' ? 'Em preparo' : 'Pronto'}</StatusTag></div>{item.option_names.length > 0 && <p className="staff-item-options">{item.option_names.join(' · ')}</p>}{item.notes && <p className="staff-item-notes">{item.notes}</p>}{action && <StatusAction key={item.status} id={item.id} expected={item.status} target={action.status} label={action.label} changed={refresh} />}{item.status === 'NEW' && <RejectAction item={item} changed={refresh} />}</article>;
}
function RejectAction({ item, changed }: { item: WorkItem; changed: () => void }) {
  const notify = useSuccessToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState('');
  const pending = useRef<{ idempotency_key: string; expected_status: string; status: string; reason: string } | null>(null);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (submitting.current) return;
    const form = event.currentTarget; const reason = String(new FormData(form).get('reason') ?? '').trim();
    const body = pending.current ?? { idempotency_key: randomUUID(), expected_status: 'NEW', status: 'REJECTED', reason };
    pending.current = body; submitting.current = true; setBusy(true); setError('');
    try { const row = record(await request(`/api/v1/staff/items/${item.id}/status/`, 'POST', body)); if (row.status !== 'REJECTED') throw new Error('Resposta inválida.'); formSaveResult(form, true); notify?.('Pedido recusado.'); setOpen(false); changed(); }
    catch (cause: unknown) { formSaveResult(form, false); setError(cause instanceof Error ? cause.message : 'Não foi possível recusar.'); if (cause instanceof ApiError && [400, 409].includes(cause.status)) { pending.current = null; if (cause.status === 409) changed(); } }
    finally { submitting.current = false; setBusy(false); }
  }
  if (!open) return <button className="ui-danger staff-reject" onClick={() => setOpen(true)}>Recusar</button>;
  return <Editor title={`Recusar ${item.name}?`} close={() => setOpen(false)} busy={busy}><form onSubmit={event => { void submit(event); }} aria-busy={busy}><h4>Recusar {item.name}?</h4><label>Motivo da recusa (opcional)<input name="reason" maxLength={300} disabled={busy || pending.current !== null} /></label>{error && <p role="alert" className="error">{error}</p>}<div className="actions"><button type="submit" className="ui-danger" disabled={busy}>{busy ? 'Confirmando…' : 'Confirmar recusa'}</button><button type="button" className="secondary" disabled={busy || pending.current !== null} onClick={requestEditorClose}>Voltar</button></div></form></Editor>;
}
export default function Production() {
  const realtime = useRealtime('staff');
  const [items, setItems] = useState<WorkItem[] | null>(null);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now());
  const [sector, setSector] = useState('');
  const [knownSectors, setKnownSectors] = useState<Record<string, string>>({});
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 10_000); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    const controller = new AbortController(); let inFlight = false;
    async function load() {
      if (inFlight || document.visibilityState === 'hidden') return;
      inFlight = true;
      try {
        const data = decodeWorkItems(await request(`/api/v1/staff/production/items/?page=${page}${sector ? `&sector=${encodeURIComponent(sector)}` : ''}`, 'GET', undefined, controller.signal));
        if (!controller.signal.aborted) { setItems(data.results); setNext(data.next); setError(''); setKnownSectors(values => ({ ...values, ...Object.fromEntries(data.results.map(item => [item.sector_id, item.sector_name])) })); }
      } catch (cause: unknown) { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) { setPage(1); return; } if (cause instanceof ApiError && [401, 403].includes(cause.status)) setItems([]); setError(cause instanceof Error ? cause.message : 'Não foi possível carregar a produção.'); } }
      finally { inFlight = false; }
    }
    void load(); const timer = window.setInterval(() => { void load(); }, 30_000); window.addEventListener('focus', load); window.addEventListener('online', load);
    return () => { controller.abort(); window.clearInterval(timer); window.removeEventListener('focus', load); window.removeEventListener('online', load); };
  }, [page, reload, realtime.revision, sector]);
  const refresh = () => setReload(value => value + 1);
  return <section className="operational-surface">
    <PageHeader title="Produção" description="Itens organizados por etapa, nos setores autorizados para você." />
    <ConnectionStatus status={realtime.status} />
    {error && <ErrorState message={error} retry={refresh} />}
    <div className="staff-toolbar"><label>Setor<select value={sector} onChange={event => { setSector(event.target.value); setPage(1); setItems(null); }}><option value="">Todos os meus setores</option>{Object.entries(knownSectors).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label><span className="muted">Itens mais antigos primeiro</span></div>
    {items === null ? error ? null : <LoadingSkeleton variant="production" /> : <div className="kds-columns">{columns.map(column => {
      const visible = items.filter(item => column.states.includes(item.status));
      return <section className="staff-kds-column" key={column.label}><header><h2>{column.label}</h2><StatusTag>{visible.length} nesta página</StatusTag></header>{visible.length === 0 ? <p className="staff-kds-empty">Nenhum item nesta etapa, nesta página.</p> : visible.map(item => <ProductionCard key={item.id} item={item} now={now} refresh={refresh} />)}</section>;
    })}</div>}
    <Pagination page={page} next={next} label="Produção" change={value => { setPage(value); setItems(null); }} />
  </section>;
}
