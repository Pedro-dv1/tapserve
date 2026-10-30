import { useEffect, useState } from 'react';
import { ApiError, request } from '../../lib/api';
import type { StaffContext } from '../../lib/api';
import { useRealtime } from '../../lib/useRealtime';
import { decodeBatches } from '../customer/orderData';
import type { Batch } from '../customer/orderData';
import { statusNames } from '../customer/orderStatus';
import { EmptyState, ErrorState, LoadingSkeleton } from '../../components/Interface';
import { ConnectionStatus, PageHeader, Pagination } from './StaffUI';
import { DeliveryAction, ItemContent } from './Operation';

export default function StaffOrders({ context }: { context: StaffContext }) {
  const realtime = useRealtime('staff');
  const [batches, setBatches] = useState<Batch[] | null>(null);
  const [status, setStatus] = useState(''), [page, setPage] = useState(1), [next, setNext] = useState(false);
  const [error, setError] = useState(''), [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let inFlight = false;
    async function load() {
      if (inFlight || document.visibilityState === 'hidden') return;
      inFlight = true;
      try { const data = decodeBatches(await request(`/api/v1/staff/orders/?page=${page}${status ? `&status=${status}` : ''}`, 'GET', undefined, controller.signal)); if (!controller.signal.aborted) { setBatches(data.results); setNext(data.next); setError(''); } }
      catch (cause: unknown) { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Pedidos indisponíveis.'); if (cause instanceof ApiError && [401, 403].includes(cause.status)) setBatches(null); } }
      finally { inFlight = false; }
    }
    void load(); const timer = window.setInterval(() => { void load(); }, 30_000); window.addEventListener('focus', load); window.addEventListener('online', load); document.addEventListener('visibilitychange', load);
    return () => { controller.abort(); window.clearInterval(timer); window.removeEventListener('focus', load); window.removeEventListener('online', load); document.removeEventListener('visibilitychange', load); };
  }, [page, status, reload, realtime.ordersRevision]);
  const refresh = () => setReload(value => value + 1);
  return <section className="operational-surface"><PageHeader title="Pedidos" description="Pedidos da unidade, enviados pelos clientes e pela equipe." /><ConnectionStatus status={realtime.status} />
    <label>Estado dos itens<select value={status} onChange={event => { setStatus(event.target.value); setPage(1); setBatches(null); }}><option value="">Todos os estados</option>{Object.entries(statusNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    {error && <ErrorState message={error} retry={refresh} />}{batches === null ? !error && <LoadingSkeleton variant="orders" /> : !batches.length ? <EmptyState title="Nenhum pedido encontrado">Os novos pedidos aparecerão automaticamente aqui.</EmptyState> : batches.map(batch => <article className="session-stack" key={batch.id}><header><h2>{batch.point_names?.join(' + ') || 'Pedido da unidade'}</h2><p>Pedido #{batch.id.slice(0, 8)} · <time dateTime={batch.created_at}>{new Date(batch.created_at).toLocaleString('pt-BR')}</time></p><p>{batch.origin === 'MANUAL' ? `Manual${batch.staff_name ? ` · ${batch.staff_name}` : ''}` : 'Cliente'}</p></header>{batch.notes && <p className="staff-item-notes">{batch.notes}</p>}<ul className="staff-order-items">{batch.items.map(item => <li key={item.id}><ItemContent item={item} /><DeliveryAction item={item} context={context} changed={refresh} /></li>)}</ul></article>)}
    <Pagination page={page} next={next} label="Pedidos" change={value => { setPage(value); setBatches(null); }} />
  </section>;
}
