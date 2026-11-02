import SearchCombobox, { normalizeSearch } from '../../components/SearchCombobox';
import { useEffect, useRef, useState } from 'react';
import { ApiError, record, request } from '../../lib/api';
import type { Point, StaffContext } from '../../lib/api';
import { manualDraftKey, pendingManualKey, readPendingManual } from '../../lib/manualDrafts';
import { randomUUID } from '../../lib/uuid';
import { Editor, Pagination } from './StaffUI';
import { ErrorState, LoadingSkeleton, QuantitySelector } from '../../components/Interface';
import { brl, cents, decodeDetail, decodeProduct, formatCents, selectionError, selectionTotal } from '../customer/menuData';
import type { Product, ProductDetail } from '../customer/menuData';
import { OptionChoices } from '../customer/ProductSelection';
import { afterFailedSubmission, decodeCart, emptyCart, orderPayload } from '../customer/cart';
import type { Cart } from '../customer/cart';
import type { Session } from '../customer/orderData';
import { FulfillmentBadge, FulfillmentSelector } from '../../components/Fulfillment';
import type { FulfillmentMode } from '../customer/fulfillment';
import ConfirmDialog from '../../components/ConfirmDialog';

export default function ManualOrder({ point, session, context, close, changed }: { point: Point; session: Session | null; context: StaffContext; close: () => void; changed: () => void }) {
  const storage = manualDraftKey(context, point.id, session?.id ?? null);
  const pendingStorage = pendingManualKey(context, point.id);
  const [cart, setCart] = useState<Cart>(() => { try { const raw = sessionStorage.getItem(storage); return raw ? decodeCart(JSON.parse(raw)) : emptyCart(); } catch { return emptyCart(); } });
  const [pendingKey, setPendingKey] = useState<string | null>(() => { try { return readPendingManual(sessionStorage.getItem(pendingStorage)); } catch { return 'invalid'; } });
  const [abandon, setAbandon] = useState(false);
  const [products, setProducts] = useState<Product[] | null>(null);
  const [page, setPage] = useState(1), [next, setNext] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [searching, setSearching] = useState(false);
  const [query, setQuery] = useState(''), [search, setSearch] = useState('');
  const [identifier, setIdentifier] = useState(''), [product, setProduct] = useState<ProductDetail | null>(null);
  const [selected, setSelected] = useState<string[]>([]), [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState(''), [participant, setParticipant] = useState('');
  const [fulfillment, setFulfillment] = useState<FulfillmentMode>('DINE_IN');
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [reload, setReload] = useState(0);
  const [storageError, setStorageError] = useState('');
  const saving = useRef(false);
  const confirmed = useRef(false);
  useEffect(() => { if (confirmed.current) return; try { sessionStorage.setItem(storage, JSON.stringify(cart)); setStorageError(''); } catch { setStorageError('O navegador não permitiu preservar o rascunho. Mantenha esta janela aberta até conferir a confirmação do pedido.'); } }, [cart, storage]);
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(normalizeSearch(query)); setPage(1); }, 250); return () => window.clearTimeout(timer); }, [query]);
  useEffect(() => {
    const controller = new AbortController(); setSearching(true);
    void request(`/api/v1/staff/tables/${point.id}/menu/?page=${page}&search=${encodeURIComponent(search)}`, 'GET', undefined, controller.signal).then(record).then(data => {
      if (!Array.isArray(data.results)) throw new Error('Cardápio inválido.');
      if (!controller.signal.aborted) { setSearchError(''); setProducts(data.results.map(decodeProduct)); setNext(typeof data.next === 'string'); }
    }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else { const message = cause instanceof Error ? cause.message : 'Cardápio indisponível.'; setSearchError(message); setError(message); } } }).finally(() => { if (!controller.signal.aborted) setSearching(false); });
    return () => controller.abort();
  }, [point.id, search, page, reload]);
  useEffect(() => {
    if (!identifier) return;
    const controller = new AbortController(); setProduct(null);
    void request(`/api/v1/staff/products/${identifier}/choices/`, 'GET', undefined, controller.signal).then(decodeDetail).then(value => { if (!controller.signal.aborted) { setProduct(value); setSelected([]); setQuantity(1); setNotes(''); setFulfillment('DINE_IN'); } }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Opções indisponíveis.'); });
    return () => controller.abort();
  }, [identifier, reload]);
  function add() {
    if (!product || cart.pending || cart.items.length >= 50) return;
    const invalid = selectionError(product, selected); if (invalid) { setError(invalid); return; }
    const line = { id: randomUUID(), product_id: product.id, name: product.name, unit_price: (selectionTotal(product, selected) / 100).toFixed(2), quantity, option_ids: selected, notes, participant_id: participant || null, participant_name: '', fulfillment_mode: fulfillment, price_confirmed: true };
    setCart(value => ({ ...value, idempotency_key: randomUUID(), items: [...value.items, line] })); setIdentifier(''); setProduct(null); setError('');
  }
  async function submit() {
    if (saving.current || !cart.items.length) return;
    if (pendingKey && pendingKey !== cart.idempotency_key) { setError('Confira o envio anterior antes de iniciar outro pedido.'); return; }
    saving.current = true; setBusy(true); setError('');
    setCart(value => ({ ...value, pending: true }));
    try {
      if (cart.pending || pendingKey) {
        try {
          const receipt = record(await request(`/api/v1/staff/manual-order-receipts/${cart.idempotency_key}/?point=${point.id}`));
          if (receipt.abandoned !== true) record(receipt.batch); confirmed.current = true; sessionStorage.removeItem(storage); sessionStorage.removeItem(pendingStorage); changed(); close(); return;
        } catch (cause: unknown) { if (!(cause instanceof ApiError && cause.status === 404)) throw cause; }
      }
      sessionStorage.setItem(storage, JSON.stringify({ ...cart, pending: true }));
      sessionStorage.setItem(pendingStorage, JSON.stringify({ idempotency_key: cart.idempotency_key }));
      setPendingKey(cart.idempotency_key);
      const data = record(await request('/api/v1/staff/orders/', 'POST', { ...orderPayload(cart), point_id: point.id, expected_session_id: session?.id ?? null }));
      record(data.batch); confirmed.current = true; try { sessionStorage.removeItem(storage); sessionStorage.removeItem(pendingStorage); } catch { /* A confirmed order remains confirmed when storage is unavailable. */ } changed(); close();
    } catch (cause: unknown) {
      const preserved = afterFailedSubmission(cart, cause instanceof ApiError ? cause.status : undefined);
      setCart(preserved);
      if (!preserved.pending) { try { sessionStorage.removeItem(pendingStorage); setPendingKey(null); } catch { /* Keep the conservative pending marker. */ } }
      setError(cause instanceof ApiError && Object.keys(cause.fields).length ? Object.values(cause.fields).join(' ') : cause instanceof Error ? cause.message : 'Não foi possível confirmar o pedido.');
    } finally { saving.current = false; setBusy(false); }
  }
  async function reconcile() {
    if (saving.current || !pendingKey) return;
    saving.current = true; setBusy(true); setError('');
    try { const receipt = record(await request(`/api/v1/staff/manual-order-receipts/${pendingKey}/?point=${point.id}`)); if (receipt.abandoned !== true) record(receipt.batch); confirmed.current = true; sessionStorage.removeItem(pendingStorage); sessionStorage.removeItem(storage); changed(); close(); }
    catch (cause: unknown) { setError(cause instanceof ApiError && cause.status === 404 ? 'O envio anterior ainda não foi localizado. Aguarde e consulte novamente; não envie um novo pedido para evitar duplicidade.' : cause instanceof Error ? cause.message : 'Não foi possível conferir o envio.'); }
    finally { saving.current = false; setBusy(false); }
  }
  return <Editor title={`Novo pedido · ${point.type === 'TABLE' && point.number ? `Mesa ${point.number}` : point.name}`} close={close} busy={busy} guardChanges={false}>
    {storageError && <p className="error" role="alert">{storageError}</p>}
    {error && <ErrorState message={error} retry={() => setReload(value => value + 1)} />}
    {pendingKey && <p role="status">Existe um envio anterior para conferir. <button className="secondary" type="button" disabled={busy} onClick={() => { void reconcile(); }}>Consultar resultado do envio</button></p>}
    {pendingKey && <button className="secondary" type="button" disabled={busy} onClick={() => setAbandon(true)}>Encerrar tentativa sem resultado</button>}
    {abandon && pendingKey && <ConfirmDialog title="Reconciliar tentativa anterior" description="Se o pedido já foi confirmado, ele será localizado e preservado. Caso contrário, esta tentativa será bloqueada no servidor para que um envio atrasado não a confirme depois. O rascunho será descartado." label="Conferir e encerrar tentativa" close={() => setAbandon(false)} confirm={async () => { const receipt = record(await request(`/api/v1/staff/manual-order-receipts/${pendingKey}/`, 'POST', { point: point.id })); if (receipt.abandoned !== true) record(receipt.batch); confirmed.current = true; sessionStorage.removeItem(storage); sessionStorage.removeItem(pendingStorage); changed(); close(); }} />}
    {cart.pending && <p role="status">Confirmação pendente. Repita com os mesmos dados para conferir o pedido sem duplicá-lo.</p>}
    <fieldset disabled={busy || cart.pending || Boolean(pendingKey)}><legend>Produtos do cardápio da mesa</legend><SearchCombobox label="Buscar produto" value={query} change={setQuery} search={value => { setSearch(value); setPage(1); }} suggestions={(products ?? []).map(value => ({ ...value, detail: brl(value.base_price) }))} loading={searching || normalizeSearch(query) !== search} error={searchError} select={value => setIdentifier(value.id)} disabled={busy || cart.pending || Boolean(pendingKey)} />{products ? <><label>Selecionar produto<select value={identifier} onChange={event => setIdentifier(event.target.value)}><option value="">Selecione</option>{products.map(value => <option key={value.id} value={value.id}>{value.name} · {brl(value.base_price)}</option>)}</select></label>{!products.length && <p>Nenhum produto disponível nesta busca.</p>}<Pagination page={page} next={next} change={setPage} /></> : <LoadingSkeleton variant="options" />}
      {identifier && (product ? <><h3>{product.name}</h3>{product.takeaway_enabled && <FulfillmentSelector value={fulfillment} change={setFulfillment} />}<OptionChoices groups={product.groups} selected={selected} setSelected={setSelected} busy={busy || cart.pending} /><QuantitySelector quantity={quantity} change={setQuantity} disabled={busy || cart.pending || Boolean(pendingKey)} name={product.name} /><label>Observações<textarea maxLength={500} value={notes} onChange={event => setNotes(event.target.value)} /></label><label>Participante (opcional)<select value={participant} onChange={event => setParticipant(event.target.value)}><option value="">Sem participante</option>{session?.participants.map(person => <option key={person.id} value={person.id}>{person.display_name}</option>)}</select></label><button type="button" disabled={cart.items.length >= 50} onClick={add}>Adicionar · {formatCents(selectionTotal(product, selected, quantity))}</button></> : <LoadingSkeleton variant="options" />)}
    </fieldset>
    <h3>Itens do novo pedido</h3>{cart.items.length ? <ul className="staff-list">{cart.items.map(line => <li key={line.id}><span><FulfillmentBadge mode={line.fulfillment_mode} />{line.quantity} × {line.name} · {formatCents(cents(line.unit_price) * line.quantity)}{line.notes && <small> · {line.notes}</small>}</span><button className="secondary" type="button" disabled={busy || cart.pending || Boolean(pendingKey)} onClick={() => setCart(value => ({ ...value, idempotency_key: randomUUID(), items: value.items.filter(item => item.id !== line.id) }))}>Remover</button></li>)}</ul> : <p>Adicione os produtos antes de confirmar.</p>}
    <label>Observação do pedido<textarea disabled={busy || cart.pending || Boolean(pendingKey)} maxLength={500} value={cart.notes ?? ''} onChange={event => { const notes = event.target.value; setCart(value => ({ ...value, idempotency_key: randomUUID(), notes })); }} /></label>
    <div className="dialog-actions"><button type="button" className="secondary" disabled={busy} onClick={close}>Voltar</button><button disabled={busy || !cart.items.length || Boolean(pendingKey && pendingKey !== cart.idempotency_key)} onClick={() => { void submit(); }}>{busy ? 'Confirmando…' : cart.pending ? 'Repetir o mesmo pedido' : 'Confirmar pedido'}</button></div>
  </Editor>;
}
