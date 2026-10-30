import { orderMessages } from '../../lib/actionMessages';
import { randomUUID } from '../../lib/uuid.ts';
﻿import { useEffect, useRef, useState } from 'react';
import { ApiError, decodePoint, record, request, text } from '../../lib/api';
import { decodeBatches, decodeSessionValue } from '../customer/orderData';
import type { Item } from '../customer/orderData';
import type { StaffContext } from '../../lib/api';
import { useRealtime } from '../../lib/useRealtime';
import ManualOrder from './ManualOrder';
import Toast, { useSuccessToast } from '../../components/Toast';
import ItemActions from '../customer/ItemActions';
import { EmptyState, ErrorState, LoadingSkeleton } from '../../components/Interface';
import { ConnectionStatus, Pagination, StatusTag } from './StaffUI';
import { brl } from '../customer/menuData';
import { statusNames } from '../customer/orderStatus';
import { FulfillmentBadge } from '../../components/Fulfillment';
import { isManagement } from './navigation';


type Session = ReturnType<typeof decodeSessionValue> & { item_counts: Record<string, number> };
export function decodeOperation(value: unknown) {
  const data = record(value);
  if (!Array.isArray(data.results)) throw new Error('Resposta inválida do serviço.');
  return { next: typeof data.next === 'string', results: data.results.map((value: unknown): Session => {
    const row = record(value), counts = record(row.item_counts);
    if (!Object.keys(statusNames).every(status => typeof counts[status] === 'number' && Number.isSafeInteger(counts[status]) && (counts[status] as number) >= 0)) throw new Error('Resumo da operação inválido.');
    return { ...decodeSessionValue(value), item_counts: counts as Record<string, number> };
  }) };
}
type OperationalPoint = ReturnType<typeof decodePoint> & { session: ReturnType<typeof decodeSessionValue> | null; connected_devices: number; order_count: number; active_order_count: number; subtotal: string; pending_calls: { id: string; kind: string }[] };
export function decodeTables(value: unknown) {
  const data = record(value); if (!Array.isArray(data.results)) throw new Error('Resposta inválida das mesas.');
  return { next: typeof data.next === 'string', results: data.results.map((value: unknown): OperationalPoint => {
    const row = record(value);
    for (const key of ['connected_devices', 'order_count', 'active_order_count']) if (typeof row[key] !== 'number' || !Number.isSafeInteger(row[key]) || (row[key] as number) < 0) throw new Error('Resumo da mesa inválido.');
    if (!Array.isArray(row.pending_calls)) throw new Error('Chamados da mesa inválidos.');
    const subtotal = text(row.subtotal); brl(subtotal);
    return { ...decodePoint(row), session: row.session === null ? null : decodeSessionValue(row.session), connected_devices: row.connected_devices as number, order_count: row.order_count as number, active_order_count: row.active_order_count as number, subtotal, pending_calls: row.pending_calls.map(value => { const call = record(value); return { id: text(call.id), kind: text(call.kind) }; }) };
  }) };
}
const tableFilters = { ALL: 'Todas', OPEN: 'Abertas', CHECK: 'Conta', CLEANING: 'Limpeza', CUTLERY: 'Talheres', PACKAGING: 'Embalagem' };
export default function Operation({ context }: { context: StaffContext }) {
  const realtime = useRealtime('staff');
  const [points, setPoints] = useState<OperationalPoint[] | null>(null);
  const [filter, setFilter] = useState(() => { const value = new URLSearchParams(window.location.search).get('filter') ?? 'ALL'; return Object.hasOwn(tableFilters, value) ? value : 'ALL'; });
  const [page, setPage] = useState(1), [next, setNext] = useState(false), [reload, setReload] = useState(0);
  const [query, setQuery] = useState(''), [search, setSearch] = useState(''), [error, setError] = useState('');
  const [opened, setOpened] = useState<string | null>(null), [manual, setManual] = useState<OperationalPoint | null>(null);
  const [message, setMessage] = useState('');
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(query); setPage(1); }, 250); return () => window.clearTimeout(timer); }, [query]);
  useEffect(() => {
    const controller = new AbortController(); let inFlight = false;
    async function load() {
      if (inFlight || document.visibilityState === 'hidden') return;
      inFlight = true;
      try { const data = decodeTables(await request(`/api/v1/staff/tables/?page=${page}&filter=${filter}&search=${encodeURIComponent(search)}`, 'GET', undefined, controller.signal)); if (!controller.signal.aborted) { setPoints(data.results); setNext(data.next); setError(''); } }
      catch (cause: unknown) { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar as mesas.'); if (cause instanceof ApiError && [401, 403].includes(cause.status)) setPoints(null); } }
      finally { inFlight = false; }
    }
    void load(); const timer = window.setInterval(() => { void load(); }, 30_000); window.addEventListener('focus', load); window.addEventListener('online', load);
    document.addEventListener('visibilitychange', load);
    return () => { controller.abort(); window.clearInterval(timer); window.removeEventListener('focus', load); window.removeEventListener('online', load); document.removeEventListener('visibilitychange', load); };
  }, [page, filter, search, reload, realtime.revision]);
  const refresh = () => setReload(value => value + 1);
  return <section className="operational-surface"><h1 className="sr-only">Mesas</h1><Toast message={message} clear={setMessage} /><ConnectionStatus status={realtime.status} />
    <nav className="table-filters" aria-label="Filtros de mesas">{Object.entries(tableFilters).map(([value, label]) => <button key={value} aria-pressed={filter === value} onClick={() => { setFilter(value); setPage(1); const url = new URL(window.location.href); url.searchParams.set('filter', value); window.history.replaceState(null, '', url); }}>{label}</button>)}</nav>
    <div className="staff-toolbar"><label className="staff-search">Buscar mesa<input type="search" value={query} maxLength={100} placeholder="Número ou nome da mesa" onChange={event => setQuery(event.target.value)} /></label></div>
    {error && <ErrorState message={error} retry={refresh} />}{points === null ? !error && <LoadingSkeleton variant="operation" /> : !points.length ? <EmptyState title="Nenhuma mesa encontrada">Revise a busca ou o filtro selecionado.</EmptyState> : <div className="staff-table-grid">{points.map(point => <article className="session-stack" key={point.id}>
      <header className="staff-session-header"><div><h2>{point.type === 'TABLE' && point.number ? `Mesa ${String(point.number).padStart(2, '0')}` : point.name}</h2>{point.type === 'TABLE' && point.number && point.name && point.name !== `Mesa ${String(point.number).padStart(2, '0')}` && <p>{point.name}</p>}</div><StatusTag attention={Boolean(point.session)}>{point.session ? point.session.status === 'CHECK_REQUESTED' ? 'Conta solicitada' : 'Aberta' : 'Livre'}</StatusTag></header>
      <p>{point.connected_devices} celulares conectados</p><p>{point.order_count} pedidos realizados{point.active_order_count !== point.order_count ? ` · ${point.active_order_count} ativos` : ''}</p><p>Consumo: <strong>{brl(point.subtotal)}</strong></p>
      {point.pending_calls.length > 0 && <a className="pending-call" href={`${isManagement(context) ? '/admin' : '/staff'}/calls?point=${point.id}`}><strong aria-hidden="true">!</strong>{point.pending_calls.length} chamados pendentes</a>}
      <div className="actions"><button className="secondary" aria-expanded={opened === point.id} onClick={() => setOpened(opened === point.id ? null : point.id)}>{opened === point.id ? 'Fechar detalhes' : 'Ver detalhes'}</button>{context.staff.permissions.includes('CREATE_MANUAL_ORDER') && <button onClick={() => setManual(point)}>Novo pedido</button>}</div>
      {opened === point.id && <div className="staff-session-details">{point.session ? <SessionOrders session={{ ...point.session, item_counts: {} }} revision={realtime.ordersRevision + reload} context={context} changed={refresh} /> : <p>A mesa ainda não possui pedidos nesta sessão.</p>}</div>}
    </article>)}</div>}
    <Pagination page={page} next={next} label="Mesas" change={value => { setPage(value); setPoints(null); }} />
    {manual && <ManualOrder point={manual} session={manual.session} close={() => setManual(null)} changed={() => { setMessage('Pedido realizado com sucesso.'); refresh(); }} />}
  </section>;
}

export function SessionOrders({ session, revision, context, changed: refreshParent }: { session: Session; revision: number; context: StaffContext; changed?: () => void }) {
  const [batches, setBatches] = useState<ReturnType<typeof decodeBatches> | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void request(`/api/v1/staff/sessions/${session.id}/orders/?page=${page}`, 'GET', undefined, controller.signal).then(decodeBatches).then(data => { if (!controller.signal.aborted) { setBatches(data); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os pedidos.'); } });
    return () => controller.abort();
  }, [session.id, session.version, page, revision, refresh]);
  const changed = () => { setRefresh(value => value + 1); refreshParent?.(); };
  return <>{error && <ErrorState message={error} retry={changed} />}{batches ? <>{batches.results.map(batch => <section key={batch.id}><h3 className="staff-batch-heading">Pedido às {new Date(batch.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</h3>{batch.notes && <p className="staff-item-notes">{batch.notes}</p>}<ul className="staff-order-items">{batch.items.map(item => <li key={item.id}><ItemContent item={item} /><DeliveryAction item={item} participants={session.participants} context={context} changed={changed} /></li>)}</ul></section>)}<Pagination page={page} next={batches.next} label="Pedidos da mesa" change={value => { setPage(value); setBatches(null); }} /></> : !error && <LoadingSkeleton variant="orders" />}</>;
}

export function ItemContent({ item }: { item: Item }) {
  return <><div className="staff-item-heading"><h3>{item.quantity} × {item.name}</h3><strong>{['CANCELLED', 'REJECTED'].includes(item.status) ? 'Não cobrado' : brl(item.line_total)}</strong></div><div className="staff-item-meta"><FulfillmentBadge mode={item.fulfillment_mode} /><StatusTag attention={item.status === 'READY'}>{statusNames[item.status]}</StatusTag>{item.participant_name && <span>Para {item.participant_name}</span>}</div>{item.option_names.length > 0 && <p className="staff-item-options">{item.option_names.join(' · ')}</p>}{item.notes && <p className="staff-item-notes">{item.notes}</p>}</>;
}

export function DeliveryAction({ item, context, changed, participants }: { item: Item; context: StaffContext; changed: () => void; participants?: Session['participants'] }) {
  const target = item.status === 'READY' && context.staff.permissions.includes('CLAIM_DELIVERY') ? 'DELIVERING' : item.status === 'DELIVERING' && item.delivered_by_id === context.staff.id && context.staff.permissions.includes('COMPLETE_DELIVERY') ? 'DELIVERED' : null;
  return <div className="staff-item-actions">{target ? <StatusAction key={item.status} id={item.id} expected={item.status} target={target} label={target === 'DELIVERING' ? 'Assumir entrega' : 'Marcar entregue'} changed={changed} /> : item.status === 'DELIVERING' ? <p>{item.delivered_by_id === context.staff.id ? 'Entrega em andamento com você.' : 'Entrega assumida por outro funcionário.'}</p> : null}{(context.staff.permissions.includes('EDIT_ORDER') || context.staff.permissions.includes('CANCEL_ORDER')) && <ItemActions item={item} {...(participants ? { participants } : {})} manual canEdit={['NEW', 'ACCEPTED'].includes(item.status) && context.staff.permissions.includes('EDIT_ORDER')} canCancel={!['DELIVERED', 'CANCELLED', 'REJECTED'].includes(item.status) && context.staff.permissions.includes('CANCEL_ORDER')} changed={changed} />}</div>;
}

export function StatusAction({ id, expected, target, label, changed }: { id: string; expected: string; target: string; label: string; changed: () => void }) {
  const notify = useSuccessToast();
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [key] = useState(() => randomUUID());
  async function submit() {
    if (submitting.current || confirmed) return;
    submitting.current = true; setBusy(true); setError('');
    try { const data = record(await request(`/api/v1/staff/items/${id}/status/`, 'POST', { idempotency_key: key, expected_status: expected, status: target })); if (data.status !== target) throw new Error('Resposta inválida do serviço.'); setConfirmed(true); notify?.(orderMessages[target] ?? 'Estado do pedido atualizado.'); changed(); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível atualizar.'); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <div>{error && <ErrorState message={`${error} Confira o estado atual ou repita esta ação.`} retry={changed} />}{!confirmed && <button className={target === 'DELIVERING' || target === 'READY' ? 'staff-primary-attention' : ''} disabled={busy} onClick={() => { void submit(); }}>{busy ? 'Atualizando…' : label}</button>}</div>;
}
