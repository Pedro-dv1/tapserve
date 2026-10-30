import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ApiError, record, request } from '../../lib/api';
import type { StaffContext } from '../../lib/api';
import { useRealtime } from '../../lib/useRealtime';
import { useAutoRefresh } from '../../lib/useAutoRefresh';

const Attention = createContext(false);

export function OrderAttentionProvider({ context, children }: { context: StaffContext; children: ReactNode }) {
  const realtime = useRealtime('staff');
  const [ready, setReady] = useState(false);
  const [reload, setReload] = useState(0);
  const permitted = context.staff.permissions.includes('VIEW_OPERATION') && context.staff.permissions.some(permission => ['CLAIM_DELIVERY', 'COMPLETE_DELIVERY'].includes(permission));
  useAutoRefresh(() => setReload(value => value + 1), permitted);
  useEffect(() => {
    setReady(false);
  }, [context.staff.id]);
  useEffect(() => {
    if (!permitted) return;
    const controller = new AbortController();
    // The delivery endpoint scopes items to the authenticated unit, across all pages.
    void request('/api/v1/staff/deliveries/?attention=true&page=1', 'GET', undefined, controller.signal).then(record).then(data => {
      if (typeof data.count !== 'number' || !Number.isSafeInteger(data.count) || data.count < 0) throw new Error('Contagem inválida.');
      if (!controller.signal.aborted) setReady(data.count > 0);
    }).catch((cause: unknown) => { if (!controller.signal.aborted && cause instanceof ApiError && [401, 403].includes(cause.status)) setReady(false); });
    return () => controller.abort();
  }, [context.staff.id, permitted, reload, realtime.ordersRevision]);
  return <Attention value={permitted && ready}>{children}</Attention>;
}

export function OrderAttention({ href }: { href: string }) {
  const ready = useContext(Attention);
  return ready && href.endsWith('/orders') ? <span className="order-attention" role="status"><span aria-hidden="true">!</span><span className="sr-only">Itens prontos aguardando entrega</span></span> : null;
}
