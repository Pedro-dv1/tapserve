import { useState } from 'react';
import { Button, EmptyState, Icon, LoadingSkeleton, ParticipantChip, ProductImage, StickyActionBar } from '../../components/Interface';
import type { Batch, Item } from './orderData';
import { batchStatus, isActiveBatch, publicSteps, statusNames, statusStage } from './orderStatus';
import type { OrderStatus } from './orderStatus';
import ItemActions from './ItemActions';
import { FulfillmentBadge } from '../../components/Fulfillment';

type Participant = { id: string; display_name: string };
export default function OrdersPage({ participants, batches, loading, unavailable = false, timeZone, refresh, menu }: { batches: Batch[]; participants: Participant[]; loading: boolean; unavailable?: boolean; timeZone: string; refresh: (updated?: unknown) => void; menu: () => void }) {
  const [history, setHistory] = useState(false);
  const [limit, setLimit] = useState(10);
  const active = batches.filter(batch => isActiveBatch(batch.items));
  const filtered = history ? batches.filter(batch => !isActiveBatch(batch.items)) : active;
  return <section className="orders-page"><div className="page-heading"><h1>Pedidos</h1><p>Acompanhe o andamento dos seus pedidos</p></div>
    <div className="segmented-control" aria-label="Filtrar pedidos"><button aria-pressed={!history} className={!history ? 'selected' : ''} onClick={() => { setHistory(false); setLimit(10); }}>Em andamento</button><button aria-pressed={history} className={history ? 'selected' : ''} onClick={() => { setHistory(true); setLimit(10); }}>Histórico</button></div>
    {!history && active.length > 0 && <div className="active-orders"><Icon name="receipt" size={24} /><div><strong>{active.length} {active.length === 1 ? 'pedido ativo' : 'pedidos ativos'}</strong><p>Acompanhe abaixo o andamento de cada item.</p></div></div>}
    {unavailable && batches.length === 0 ? null : loading && batches.length === 0 ? <LoadingSkeleton variant="orders" /> : filtered.length === 0 ? <EmptyState key={history ? 'history' : 'active'} title={history ? 'Histórico vazio' : 'Nenhum pedido em andamento'}>{history ? 'Os pedidos concluídos ou cancelados aparecerão aqui.' : 'Seus pedidos aparecerão aqui após a confirmação.'}</EmptyState> : <div className="order-batches">{filtered.slice(0, limit).map(batch => <OrderBatch key={batch.id} batch={batch} timeZone={timeZone} participants={participants} refresh={refresh} />)}</div>}
    <div className="orders-refresh"><button className="plain-action" disabled={loading} onClick={() => refresh()}>{loading ? 'Atualizando…' : 'Atualizar pedidos'}</button>{filtered.length > limit && <Button secondary onClick={() => setLimit(value => value + 10)}>Ver mais pedidos</Button>}</div>
    <StickyActionBar><Button onClick={menu}><Icon name="plus" />Pedir mais</Button></StickyActionBar>

  </section>;
}
function OrderBatch({ batch, timeZone, participants, refresh }: { batch: Batch; timeZone: string; participants: Participant[]; refresh: (updated?: unknown) => void }) {
  const status = batchStatus(batch.items);
  const count = batch.items.reduce((sum, item) => sum + item.quantity, 0);
  return <details className="order-batch" open><summary><div><h2>Pedido {new Date(batch.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone })}</h2><p>{count} {count === 1 ? 'item' : 'itens'} · {new Date(batch.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', timeZone })}</p></div><StatusBadge status={status} /><span className="disclosure-chevron"><Icon name="chevron" size={16} /></span></summary>
    <ul className="order-items">{batch.items.map(item => <OrderItem key={item.id} item={item} participants={participants} refresh={refresh} />)}</ul>
    {batch.notes && <p className="batch-notes"><Icon name="message" size={16} />{batch.notes}</p>}
  </details>;
}
function OrderItem({ item, participants, refresh }: { item: Item; participants: Participant[]; refresh: (updated?: unknown) => void }) {
  return <li className="order-item"><div className="order-item-main"><ProductImage id={item.product_id} name={item.name} /><div className="order-item-content"><h3>{item.quantity > 1 ? `${item.quantity} × ` : ''}{item.name}</h3>{item.participant_name && <ParticipantChip name={item.participant_name} />}<FulfillmentBadge mode={item.fulfillment_mode} /><OrderProgress status={item.status} /></div></div>
    {(item.notes || item.option_names.length > 0 || item.can_customer_change) && <details className="order-item-details"><summary>Detalhes do item</summary>{item.option_names.length > 0 && <p>{item.option_names.join(', ')}</p>}{item.notes && <p>{item.notes}</p>}<ItemActions item={item} participants={participants} canEdit={item.can_customer_change} canCancel={item.can_customer_change} changed={refresh} /></details>}
  </li>;
}
export function StatusBadge({ status }: { status: OrderStatus }) {
  const stage = statusStage(status);
  return <span key={status} className={`status-badge ${['CANCELLED', 'REJECTED'].includes(status) ? 'cancelled' : stage >= 2 ? 'complete' : ''}`}><Icon name={['CANCELLED', 'REJECTED'].includes(status) ? 'info' : stage === 3 ? 'check' : stage === 2 ? 'ready' : 'clock'} size={16} />{statusNames[status]}</span>;
}
export function OrderProgress({ status }: { status: OrderStatus }) {
  if (['CANCELLED', 'REJECTED'].includes(status)) return <span className="cancelled-progress"><Icon name="info" size={16} />{status === 'REJECTED' ? 'Item recusado · não será cobrado' : 'Item cancelado'}</span>;
  const stage = statusStage(status);
  return <ol className="order-progress" aria-label={`Status: ${statusNames[status]}`}>{publicSteps.map((label, index) => <li className={index <= stage ? 'done' : ''} key={label} aria-current={index === stage ? 'step' : undefined}><span className="progress-dot">{index <= stage ? <Icon name="check" size={12} /> : <span />}</span><span className="progress-label">{label}</span></li>)}</ol>;
}
