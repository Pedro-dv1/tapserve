import { useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button, CustomerHeader, Icon, StickyActionBar } from '../../../frontend/src/components/Interface';
import MenuBrowser from '../../../frontend/src/features/customer/MenuBrowser';
import ProductSelection from '../../../frontend/src/features/customer/ProductSelection';
import type { Participant, ProductDraft } from '../../../frontend/src/features/customer/ProductSelection';
import CartPage from '../../../frontend/src/features/customer/CartPage';
import OrdersPage from '../../../frontend/src/features/customer/OrdersPage';
import ServiceRequests from '../../../frontend/src/features/customer/ServiceRequests';
import type { Cart, CartLine } from '../../../frontend/src/features/customer/cart';
import type { Batch } from '../../../frontend/src/features/customer/orderData';
import type { OrderStatus } from '../../../frontend/src/features/customer/orderStatus';
import { cents, formatCents } from '../../../frontend/src/features/customer/menuData';
import type { PublicContext } from '../../../frontend/src/lib/api';
import { resetDemo } from './api';
import '../../../frontend/src/design-system/base.css';
import '../../../frontend/src/design-system/customer.css';
import '../../../frontend/src/design-system/motion.css';
import './product-demo.css';

const context: PublicContext = { device_id: 'local-demo', company_name: 'TapServe Demo', unit_name: 'Unidade Centro Demo', expires_at: '2099-01-01', point: { id: 'local-table', number: 8, name: 'Mesa 08', type: 'TABLE', active: true, access_enabled: true, token_version: 1, nfc_enabled: true, qr_enabled: false, block_new_devices: false } };
type Screen = 'home' | 'menu' | 'product' | 'cart' | 'orders' | 'table';
const stages: OrderStatus[] = ['NEW', 'PREPARING', 'READY', 'DELIVERED'];
function ProductDemo() {
  const [screen, setScreen] = useState<Screen>('menu');
  const [product, setProduct] = useState('');
  const [editing, setEditing] = useState<CartLine>();
  const [cart, setCart] = useState<Cart>({ items: [], pending: false, idempotency_key: 'local' });
  const [batches, setBatches] = useState<Batch[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [participantName, setParticipantName] = useState('');
  const [revision, setRevision] = useState(0);
  const [stage, setStage] = useState(0);
  const [reset, setReset] = useState(0);
  const drafts = useRef<Record<string, ProductDraft>>({});
  const count = cart.items.reduce((sum, line) => sum + line.quantity, 0);
  const total = formatCents(cart.items.reduce((sum, line) => sum + cents(line.unit_price) * line.quantity, 0));
  async function register(name: string) {
    const person = participants.find(person => person.display_name === name.trim()) ?? { id: crypto.randomUUID(), display_name: name.trim() };
    if (!person.display_name || person.display_name.length > 100) throw new Error('Informe um nome de até 100 caracteres.');
    setParticipants(values => values.some(value => value.id === person.id) ? values : [...values, person]);
    return person;
  }
  function remove(person: Participant) {
    setParticipants(values => values.filter(value => value.id !== person.id));
    setCart(value => ({ ...value, items: value.items.map(line => line.participant_id === person.id ? { ...line, participant_id: null, participant_name: '' } : line) }));
  }
  function navigate(next: Screen) { setScreen(next); window.scrollTo(0, 0); }
  function open(identifier: string, line?: CartLine) { setProduct(identifier); setEditing(line); navigate('product'); }
  function restart() { resetDemo(); setCart({ items: [], pending: false, idempotency_key: 'local' }); setBatches([]); setParticipants([]); setParticipantName(''); setStage(0); setRevision(value => value + 1); setReset(value => value + 1); drafts.current = {}; navigate('menu'); }
  function changeStage(next: number) { setStage(next); setBatches(values => values.map((batch, index) => index === 0 ? { ...batch, items: batch.items.map(item => ({ ...item, status: stages[next] ?? 'NEW' })) } : batch)); }
  function send() {
    if (!cart.items.length) return;
    setBatches(previous => [{ id: crypto.randomUUID(), created_at: new Date().toISOString(), notes: cart.notes ?? '', items: cart.items.map(line => ({ id: line.id, product_id: line.product_id, name: line.name, quantity: line.quantity, notes: line.notes, version: 1, option_ids: line.option_ids, option_names: line.option_names ?? [], can_customer_change: false, editable_until: '', line_total: (cents(line.unit_price) * line.quantity / 100).toFixed(2), status: 'NEW', participant_id: line.participant_id ?? null, participant_name: line.participant_name || null, delivered_by_id: null, fulfillment_mode: line.fulfillment_mode ?? 'DINE_IN' })) }, ...previous]);
    setCart({ items: [], pending: false, idempotency_key: 'local' }); setStage(0); navigate('orders');
  }
  return <><div className="demo-controls"><span>Ambiente demonstrativo · sem envio real</span><button onClick={restart}>Reiniciar demonstração</button></div><main className="customer-root"><div className={`customer-app page-${screen}`}>
    <CustomerHeader context={context} pointName="Mesa 08" {...(screen === 'product' ? { back: () => navigate('menu') } : {})} />
    <div className="demo-view" key={`${screen}-${reset}`}>
      {screen === 'home' && <><section className="customer-home"><h1>Boas-vindas à mesa.</h1><p>Escolha com calma. Estamos por aqui para ajudar.</p><Button className="home-menu" onClick={() => navigate('menu')}><Icon name="book" size={25} /><span>Ver cardápio</span><Icon name="arrow" /></Button></section><div className="home-service-slot"><ServiceRequests quick view="home" revision={revision} sessionStatus={batches.length ? 'OPEN' : null} changed={() => setRevision(value => value + 1)} />{!batches.length && <p className="home-note">O atendimento começa ao confirmar seu primeiro pedido.</p>}</div></>}
      {screen === 'menu' && <MenuBrowser open={open} />}
      {screen === 'product' && <ProductSelection identifier={product} initial={drafts.current[editing?.id ?? product]} editing={editing} participants={participants} saveDraft={draft => { drafts.current[editing?.id ?? product] = draft; }} register={register} remove={remove} locked={false} confirm={line => { setCart(value => ({ ...value, items: editing ? value.items.map(item => item.id === editing.id ? line : item) : [...value.items, line] })); delete drafts.current[editing?.id ?? product]; navigate('cart'); }} />}
      {screen === 'cart' && <CartPage cart={cart} busy={false} change={setCart} edit={line => open(line.product_id, line)} menu={() => navigate('menu')} send={send} verify={() => navigate('orders')} />}
      {screen === 'orders' && <><OrdersPage batches={batches} participants={participants.filter((person): person is { id: string; display_name: string } => person.id !== null)} loading={false} timeZone="America/Sao_Paulo" refresh={() => {}} menu={() => navigate('menu')} />{batches.length > 0 && <div className="demo-state-controls"><p>Avance apenas o estado desta simulação.</p><Button secondary disabled={stage === 0} onClick={() => changeStage(stage - 1)}>Voltar estado</Button><Button disabled={stage === stages.length - 1} onClick={() => changeStage(stage + 1)}>Avançar estado</Button></div>}</>}
      {screen === 'table' && <><section className="table-page"><div className="page-heading"><h1>Mesa</h1><p>Seu atendimento em um só lugar</p></div><div className="table-summary"><span className="table-symbol"><Icon name="table" size={28} /></span><div><strong>Mesa 08</strong></div><span className="table-status">{batches.length ? 'Em atendimento' : 'Livre'}</span></div><section className="table-card"><div className="section-heading"><h2><Icon name="users" />Participantes</h2><span>{participants.length}</span></div><p className="muted">Identifique quem está pedindo na mesa.</p>{participants.length ? <div className="participant-chips">{participants.map(person => <span className="participant-chip" key={person.id}><Icon name="user" size={18} />{person.display_name}<button className="participant-remove" aria-label={`Remover ${person.display_name}`} onClick={() => remove(person)}><Icon name="close" size={16} /></button></span>)}</div> : <p className="muted">Nenhum participante adicionado.</p>}<form className="person-editor" onSubmit={event => { event.preventDefault(); void register(participantName); setParticipantName(''); }}><label htmlFor="table-participant">Nome temporário</label><div><input id="table-participant" required maxLength={100} placeholder="Nome do participante" value={participantName} onChange={event => setParticipantName(event.target.value)} /><Button disabled={!participantName.trim()}>Adicionar</Button></div></form></section></section><ServiceRequests revision={revision} sessionStatus={batches.length ? 'OPEN' : null} view="table" changed={() => setRevision(value => value + 1)} /></>}
    </div>
    {screen !== 'product' && screen !== 'home' && <nav className="customer-navigation" aria-label="Atendimento">{(['home', 'menu', 'cart', 'orders', 'table'] as const).map((tab, index) => <button key={tab} aria-current={screen === tab ? 'page' : undefined} className={screen === tab ? 'selected' : ''} onClick={() => navigate(tab)}><Icon name={(['home', 'book', 'cart', 'receipt', 'table'] as const)[index] ?? 'book'} />{['Início', 'Cardápio', 'Carrinho', 'Pedidos', 'Mesa'][index]}</button>)}</nav>}
    {screen === 'menu' && count > 0 && <StickyActionBar><div className="menu-cart-bar"><span className="cart-icon-count"><Icon name="cart" size={26} /><span className="cart-badge" aria-label={`${count} no carrinho`}>{count}</span></span><strong>{total}</strong><Button onClick={() => navigate('cart')}>Ver carrinho <Icon name="arrow" size={18} /></Button></div></StickyActionBar>}
  </div></main></>;
}
const root = document.getElementById('product-root');
if (root) createRoot(root).render(<ProductDemo />);
