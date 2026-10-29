import { randomUUID } from '../../lib/uuid.ts';
﻿import { addTransitionType, startTransition, useEffect, useRef, useState } from 'react';
import { ApiError, decodePoint, record, request, text } from '../../lib/api';
import type { PublicContext } from '../../lib/api';
import { Button, CustomerHeader, EmptyState, ErrorState, Icon, LoadingSkeleton, StickyActionBar, tableLabel } from '../../components/Interface';
import MenuBrowser from './MenuBrowser';
import { cents, formatCents } from './menuData';
import { afterFailedSubmission, decodeCart, emptyCart, orderPayload } from './cart';
import type { Cart, CartLine } from './cart';
import { useRealtime } from '../../lib/useRealtime';
import ServiceRequests from './ServiceRequests';
import ProductSelection from './ProductSelection';
import type { Participant, ProductDraft } from './ProductSelection';
import CartPage from './CartPage';
import OrdersPage from './OrdersPage';
import '../../design-system/customer.css';
import { customerRoute } from '../../app/routes';
import NotFound from '../../app/NotFound';
import Modal from '../../components/Modal';
import Feedback from '../../components/Feedback';
import ActionPopup from '../../components/ActionPopup';

import { decodeBatches, decodeItem, decodeSession, latestItem } from './orderData';
import type { Batch, Session } from './orderData';
function routeFromLocation() {
  const route = customerRoute(window.location.pathname);
  return { ...route, edit: route.tab === 'product' ? new URLSearchParams(window.location.search).get('edit') : null };
}
export default function CustomerWorkspace({ context }: { context: PublicContext }) {
  const realtime = useRealtime('public');
  const [currentPoint, setCurrentPoint] = useState(context.point);
  const [packagingEnabled, setPackagingEnabled] = useState(context.leftover_packaging_enabled === true);
  const storageKey = `tapserve-cart:${context.device_id}`;
  const [restored] = useState(() => { try { const value = sessionStorage.getItem(storageKey); return { cart: value ? decodeCart(JSON.parse(value) as unknown) : emptyCart(), error: '' }; } catch { return { cart: emptyCart(), error: 'Não foi possível recuperar o carrinho salvo. Inicie uma nova seleção para continuar.' }; } });
  const [cart, setCart] = useState<Cart>(restored.cart);
  const [restoreError, setRestoreError] = useState(restored.error);
  const [route, setRoute] = useState(routeFromLocation);
  const [session, setSession] = useState<Session | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const mutation = useRef(false);
  const loaded = useRef(false);
  const [loading, setLoading] = useState(true);
  const [invalid, setInvalid] = useState(false);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [message, setMessage] = useState<{ text: string; tab: string } | null>(null);
  const [storageError, setStorageError] = useState('');
  const [localParticipants, setLocalParticipants] = useState<Participant[]>([]);
  const [participantName, setParticipantName] = useState('');
  const [removing, setRemoving] = useState<Participant | null>(null);
  const [removeError, setRemoveError] = useState('');
  const [logoFailed, setLogoFailed] = useState(false);
  const drafts = useRef<Record<string, ProductDraft>>({});
  const lastSession = useRef<string | null>(null);
  useEffect(() => {
    const changed = () => { startTransition(() => { addTransitionType('navigation'); setRoute(routeFromLocation()); }); setMessage(null); window.scrollTo(0, 0); };
    window.addEventListener('popstate', changed);
    return () => window.removeEventListener('popstate', changed);
  }, []);
  useEffect(() => {
    if (restoreError || invalid) return;
    try { sessionStorage.setItem(storageKey, JSON.stringify(cart)); setStorageError(''); }
    catch { setStorageError('O navegador não permitiu salvar o carrinho. Mantenha esta página aberta para preservar a seleção.'); }
  }, [cart, storageKey, restoreError, invalid]);
  useEffect(() => {
    if (invalid) return;
    const controller = new AbortController(); let inFlight = false;
    function revoke() {
      try { sessionStorage.removeItem(storageKey); } catch { setStorageError('Não foi possível limpar os dados locais.'); }
      setInvalid(true); setCart(emptyCart()); setBatches([]); setSession(null); drafts.current = {};
    }
    async function orders() {
      const results: Batch[] = [];
      for (let page = 1; page <= 10; page++) {
        const data = decodeBatches(await request(`/api/v1/public/orders/?page=${page}`, 'GET', undefined, controller.signal));
        results.push(...data.results);
        if (!data.next) return results;
      }
      throw new Error('Não foi possível conferir todos os pedidos. Tente atualizar.');
    }
    async function load() {
      if (inFlight) return;
      inFlight = true; if (!loaded.current) setLoading(true);
      try {
        const [sessionContext, orderData] = await Promise.all([request('/api/v1/public/session/', 'GET', undefined, controller.signal).then(value => { const row = record(value); return { packagingEnabled: row.leftover_packaging_enabled === true, session: decodeSession(value), point: row.point === undefined ? context.point : decodePoint(row.point) }; }), orders()]);
        if (controller.signal.aborted) return;
        const sessionData = sessionContext.session; setCurrentPoint(sessionContext.point); setPackagingEnabled(sessionContext.packagingEnabled);
        if (lastSession.current && lastSession.current !== sessionData?.id) { revoke(); return; }
        lastSession.current = sessionData?.id ?? null;
        loaded.current = true; setSession(value => value && sessionData && value.id === sessionData.id && value.version > sessionData.version ? value : sessionData);
        setBatches(previous => {
          const current = new Map(previous.flatMap(batch => batch.items.map(item => [item.id, item] as const)));
          return orderData.map(batch => ({ ...batch, items: batch.items.map(item => latestItem(current.get(item.id), item)) }));
        });
        if (sessionData) {
          setCart(value => {
            if (value.pending || !value.items.some(line => line.participant_id && !sessionData.participants.some(person => person.id === line.participant_id))) return value;
            return { ...value, idempotency_key: randomUUID(), items: value.items.map(line => line.participant_id && !sessionData.participants.some(person => person.id === line.participant_id) ? { ...line, participant_id: null, participant_name: '' } : line) };
          });
        } setLoadError('');
      } catch (cause: unknown) {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && [401, 403].includes(cause.status)) revoke();
        setLoadError(cause instanceof Error ? cause.message : 'Não foi possível atualizar o atendimento.');
      } finally { inFlight = false; if (!controller.signal.aborted) setLoading(false); }
    }
    void load(); const timer = window.setInterval(() => { void load(); }, 10_000);
    const expiry = window.setTimeout(revoke, Math.max(0, new Date(context.expires_at).getTime() - Date.now()));
    return () => { controller.abort(); window.clearInterval(timer); window.clearTimeout(expiry); };
  }, [reload, realtime.ordersRevision, realtime.catalogRevision, storageKey, context.expires_at, context.point, invalid]);

  function navigate(path: string) {
    window.history.pushState(null, '', path); startTransition(() => { addTransitionType('navigation'); setRoute(routeFromLocation()); }); setError(''); setMessage(null); window.scrollTo(0, 0);
  }
  function notify(text: string, tab = route.tab) { setMessage({ text, tab }); }
  function change(value: Cart) { if (!busy && !cart.pending && !restoreError && !invalid) setCart(value); }
  function save(line: CartLine) {
    if (restoreError || invalid || cart.pending) throw new Error('Atualize seu acesso ou confira o envio pendente antes de alterar o carrinho.');
    const editing = route.edit && cart.items.some(item => item.id === route.edit);
    if (!editing && cart.items.length >= 50) throw new Error('Limite de 50 seleções no carrinho.');
    setCart({ ...cart, items: editing ? cart.items.map(item => item.id === route.edit ? line : item) : [...cart.items, line], idempotency_key: randomUUID(), pending: false });
    delete drafts.current[route.edit ?? route.product];
    navigate('/customer/cart'); notify(editing ? 'Item atualizado.' : 'Adicionado ao carrinho.', 'cart');
  }
  async function send() {
    if (mutation.current || invalid || restoreError || cart.items.length === 0) return;
    mutation.current = true; const submitted = { ...cart, pending: true }; setCart(submitted); setBusy(true); setError(''); setMessage(null);
    // Save the uncertainty lock before transport, including reload during an in-flight request.
    try { sessionStorage.setItem(storageKey, JSON.stringify(submitted)); } catch { setStorageError('Mantenha a página aberta até conferir a confirmação do pedido.'); }
    try {
      const receipt = record(await request('/api/v1/public/orders/', 'POST', orderPayload(submitted))); text(record(receipt.batch).id);
      setCart(emptyCart()); navigate('/customer/orders'); notify('Pedido confirmado.', 'orders'); setReload(value => value + 1);
    } catch (cause: unknown) {
      const preserved = afterFailedSubmission(cart, cause instanceof ApiError ? cause.status : undefined); setCart(preserved);
      setError((cause instanceof Error ? cause.message : 'Não foi possível confirmar.') + (preserved.pending ? ' O carrinho foi preservado. Verifique o envio antes de alterá-lo.' : ' O carrinho foi preservado. Confira produtos, opções e participantes e tente novamente.'));
      if (cause instanceof ApiError && [401, 403].includes(cause.status)) setReload(value => value + 1);
    } finally { mutation.current = false; setBusy(false); }
  }
  async function verify() {
    if (mutation.current) return; mutation.current = true; setBusy(true); setError('');
    try { const receipt = record(await request(`/api/v1/public/order-receipts/${cart.idempotency_key}/`)); text(record(receipt.batch).id); setCart(emptyCart()); navigate('/customer/orders'); notify('Pedido localizado e confirmado.', 'orders'); setReload(value => value + 1); }
    catch (cause: unknown) { setError(cause instanceof ApiError && cause.status === 404 ? 'O envio ainda não foi localizado. Aguarde ou repita com os mesmos dados.' : cause instanceof Error ? cause.message : 'Não foi possível verificar.'); }
    finally { mutation.current = false; setBusy(false); }
  }
  async function register(name: string): Promise<Participant> {
    if (invalid || cart.pending) throw new Error('Não é possível alterar participantes neste momento.');
    const existing = session?.participants.find(person => person.display_name === name);
    if (existing) return existing;
    if (!session) { const person = { id: null, display_name: name }; setLocalParticipants(values => values.some(value => value.display_name === name) ? values : [...values, person]); return person; }
    const row = record(await request('/api/v1/public/session/participants/', 'POST', { display_name: name }));
    const person = { id: text(row.id), display_name: text(row.display_name) };
    setSession(value => value ? { ...value, participants: [...value.participants.filter(item => item.id !== person.id), person] } : null);
    return person;
  }
  async function addParticipant() {
    if (mutation.current || !participantName.trim()) return;
    mutation.current = true; setBusy(true); setError('');
    try { await register(participantName.trim()); setParticipantName(''); notify('Participante adicionado.'); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível adicionar participante.'); }
    finally { mutation.current = false; setBusy(false); }
  }
  async function removeParticipant(person: Participant) {
    if (mutation.current || cart.pending || invalid || restoreError) return;
    mutation.current = true; setBusy(true); setRemoveError('');
    try {
      if (person.id) await request(`/api/v1/public/session/participants/${person.id}/`, 'DELETE', {});
      setSession(value => value ? { ...value, participants: value.participants.filter(item => item.id !== person.id) } : null);
      setLocalParticipants(values => values.filter(item => item.display_name !== person.display_name));
      setCart(value => ({ ...value, idempotency_key: randomUUID(), items: value.items.map(line => line.participant_id === person.id && person.id !== null || line.participant_name === person.display_name ? { ...line, participant_id: null, participant_name: '' } : line) }));
      for (const draft of Object.values(drafts.current)) if (draft.participant_name === person.display_name) { draft.participant_name = ''; draft.participant_id = null; }
      setReload(value => value + 1);
      setRemoving(null); notify('Participante removido.');
    } catch (cause: unknown) { setRemoveError(cause instanceof Error ? cause.message : 'Não foi possível remover este participante. Tente novamente.'); }
    finally { mutation.current = false; setBusy(false); }
  }
  const participants: Participant[] = [...(session?.participants ?? [])];
  for (const person of localParticipants) if (!participants.some(value => value.display_name === person.display_name)) participants.push(person);
  for (const line of cart.items) if (line.participant_name && !participants.some(person => person.display_name === line.participant_name)) participants.push({ id: line.participant_id ?? null, display_name: line.participant_name });
  const pointName = tableLabel(currentPoint.number ? `Mesa ${currentPoint.number}` : currentPoint.name, currentPoint.type);
  const editing = cart.items.find(item => item.id === route.edit);
  const menu = () => navigate('/customer/menu');
  const back = () => route.edit ? navigate('/customer/cart') : menu();
  const confirmRemoval = (person: Participant) => { if (mutation.current || cart.pending || invalid || restoreError) return; setRemoveError(''); setRemoving(person); };
  const total = formatCents(cart.items.reduce((sum, line) => sum + cents(line.unit_price) * line.quantity, 0));
  const count = cart.items.reduce((sum, line) => sum + line.quantity, 0);
  if (invalid) return <div className="customer-app"><CustomerHeader context={{ ...context, point: currentPoint }} pointName={pointName} /><EmptyState title="Atendimento indisponível">Seu acesso expirou, foi revogado ou a sessão foi encerrada. Abra novamente o NFC ou QR do ponto, ou solicite ajuda à equipe.</EmptyState></div>;
  if (route.tab === 'not-found') return <NotFound />;
  return <div className={`customer-app page-${route.tab}`}><CustomerHeader context={{ ...context, point: currentPoint }} pointName={pointName} {...(route.tab === 'product' ? { back } : {})} />
    {realtime.status && <p className="connection-warning" role="status">{realtime.status}</p>}{error && <ErrorState message={error} />}{loadError && <ErrorState message={loadError} retry={() => setReload(value => value + 1)} />}
    {restoreError && <ErrorState message={restoreError} retry={() => setRestoreError('')} />}{storageError && <ErrorState message={storageError} />}<ActionPopup notice={message?.tab === route.tab ? { title: message.text, message: 'Alteração concluída.' } : null} close={() => setMessage(null)} />
    {route.tab === 'home' && <section className="customer-home">{context.unit_logo_url && !logoFailed && <img className="establishment-logo" src={context.unit_logo_url} alt={`Logo de ${context.unit_name}`} onError={() => setLogoFailed(true)} />}<h1>{context.point.type === 'TABLE' ? 'Boas-vindas à mesa.' : 'Boas-vindas.'}</h1><p>Escolha com calma. Estamos por aqui para ajudar.</p><Button className="home-menu" onClick={menu}><Icon name="book" size={25} /><span>Ver cardápio</span><Icon name="arrow" /></Button></section>}
    <div hidden={route.tab !== 'menu'}><MenuBrowser active={route.tab === 'menu'} revision={`${context.device_id}:${context.point.id}:${context.point.menu ?? ''}:${session?.id ?? ''}:${session?.status ?? ''}:${realtime.catalogRevision}:${reload}`} open={id => navigate(`/customer/products/${id}`)} /></div>
    {route.tab === 'product' && (route.edit && !editing ? <EmptyState title="Item não encontrado" action={<Button onClick={() => navigate('/customer/cart')}>Ver carrinho</Button>}>Este item não está mais no seu carrinho.</EmptyState> : <ProductSelection key={route.edit ?? route.product} identifier={route.product} initial={drafts.current[route.edit ?? route.product]} editing={editing} participants={participants} saveDraft={draft => { drafts.current[route.edit ?? route.product] = draft; }} register={register} remove={confirmRemoval} confirm={save} locked={busy || cart.pending || Boolean(restoreError)} />)}
    {route.tab === 'cart' && <CartPage cart={cart} busy={busy || Boolean(restoreError)} change={change} edit={line => navigate(`/customer/products/${line.product_id}?edit=${line.id}`)} menu={menu} send={() => { void send(); }} verify={() => { void verify(); }} />}
    {route.tab === 'orders' && <OrdersPage batches={batches} participants={session?.participants ?? []} loading={loading} unavailable={Boolean(loadError)} timeZone={context.unit_timezone ?? 'America/Sao_Paulo'} refresh={updated => { if (updated) { const item = decodeItem(updated); setBatches(values => values.map(batch => ({ ...batch, items: batch.items.map(value => value.id === item.id ? latestItem(value, item) : value) }))); } setReload(value => value + 1); }} menu={menu} />}
    {route.tab === 'table' && <section className="table-page">
      <div className="page-heading"><h1>Mesa</h1><p>Seu atendimento em um só lugar</p></div>
      <div className="table-summary"><span className="table-symbol"><Icon name="table" size={28} /></span><div><strong>{pointName}</strong></div><span className="table-status">{session ? 'Em atendimento' : 'Livre'}</span></div>
      {loading && !session && participants.length === 0 ? <LoadingSkeleton variant="table" /> : <section className="table-card"><div className="section-heading"><h2><Icon name="users" />Participantes</h2><span>{participants.length}</span></div><p className="muted">Identifique quem está pedindo na mesa.</p>{participants.length === 0 ? <p className="muted">Nenhum participante adicionado.</p> : <div className="participant-chips">{participants.map(person => <span className="participant-chip" key={person.id ?? person.display_name}><Icon name="user" size={18} />{person.display_name}<button className="participant-remove" type="button" disabled={busy || cart.pending} aria-label={`Remover ${person.display_name}`} onClick={() => confirmRemoval(person)}><Icon name="close" size={16} /></button></span>)}</div>}<form className="person-editor" onSubmit={event => { event.preventDefault(); void addParticipant(); }}><label htmlFor="table-participant">Nome temporário</label><div><input id="table-participant" required maxLength={100} placeholder="Nome do participante" value={participantName} onChange={event => setParticipantName(event.target.value)} /><Button type="submit" disabled={busy || !participantName.trim()}>Adicionar</Button></div></form></section>}
    </section>}
    <div hidden={route.tab !== 'home' && route.tab !== 'table'} className={route.tab === 'home' ? 'home-service-slot' : undefined}><ServiceRequests packagingEnabled={packagingEnabled} view={route.tab} quick={route.tab !== 'table'} revision={realtime.callsRevision} sessionStatus={session?.status ?? null} unavailable={loading || Boolean(loadError)} changed={() => setReload(value => value + 1)} />{route.tab === 'home' && !session && <p className="home-note">O atendimento começa ao confirmar seu primeiro pedido.</p>}</div>
    <Modal open={removing !== null} title="Remover participante?" description={`Tem certeza de que deseja remover ${removing?.display_name ?? 'este participante'} da mesa?`} busy={busy} close={() => setRemoving(null)}><p>Os itens do carrinho ficarão sem participante. Participantes com pedidos confirmados precisam permanecer no histórico.</p>{removeError && <Feedback tone="error">{removeError}</Feedback>}<div className="dialog-actions"><Button secondary disabled={busy} onClick={() => setRemoving(null)}>Cancelar</Button><Button className="ui-danger" disabled={busy || cart.pending || invalid || Boolean(restoreError)} onClick={() => { if (removing) void removeParticipant(removing); }}>{busy ? 'Removendo…' : 'Remover participante'}</Button></div></Modal>
    {route.tab !== 'product' && <nav className="customer-navigation" aria-label="Atendimento">{(['home', 'menu', 'cart', 'orders', 'table'] as const).map((tab, index) => <button key={tab} aria-current={route.tab === tab ? 'page' : undefined} className={route.tab === tab ? 'selected' : ''} onClick={() => navigate(tab === 'home' ? '/customer' : `/customer/${tab}`)}><Icon name={tab === 'home' ? 'home' : tab === 'menu' ? 'book' : tab === 'cart' ? 'cart' : tab === 'orders' ? 'receipt' : 'table'} />{['Início', 'Cardápio', 'Carrinho', 'Pedidos', 'Mesa'][index]}</button>)}</nav>}
    {route.tab === 'menu' && count > 0 && <StickyActionBar><div className="menu-cart-bar"><span className="cart-icon-count"><Icon name="cart" size={26} /><span key={count} className="cart-badge" aria-label={`${count} no carrinho`}>{count}</span></span><strong>{total}</strong><Button onClick={() => navigate('/customer/cart')}>Ver carrinho <Icon name="arrow" size={18} /></Button></div></StickyActionBar>}
  </div>;
}
