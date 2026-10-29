import { randomUUID } from '../../lib/uuid.ts';
import { startTransition, useState, ViewTransition } from 'react';
import { Button, EmptyState, Icon, ParticipantChip, PriceAction, ProductImage, QuantitySelector, StickyActionBar } from '../../components/Interface';
import { cents, formatCents, NOTE_LIMIT } from './menuData';
import type { Cart, CartLine } from './cart';
import { FulfillmentBadge } from '../../components/Fulfillment';

export default function CartPage({ cart, busy, change, edit, menu, send, verify }: { cart: Cart; busy: boolean; change: (cart: Cart) => void; edit: (line: CartLine) => void; menu: () => void; send: () => void; verify: () => void }) {
  const [notesOpen, setNotesOpen] = useState(Boolean(cart.notes));
  const total = formatCents(cart.items.reduce((sum, line) => sum + cents(line.unit_price) * line.quantity, 0));
  const count = cart.items.reduce((sum, line) => sum + line.quantity, 0);
  const people = new Set(cart.items.filter(line => line.participant_name).map(line => line.participant_id || line.participant_name)).size;
  const locked = busy || cart.pending;
  function update(items: CartLine[]) { if (!locked) change({ ...cart, items, idempotency_key: randomUUID() }); }
  return <section className="cart-page"><div className="page-heading"><h1>Carrinho</h1><p>Revise seus itens antes de enviar</p></div>
    {cart.items.length === 0 ? <EmptyState title="Seu carrinho está vazio" action={<Button onClick={menu}>Ver cardápio</Button>}>Escolha algo no cardápio para começar.</EmptyState> : <>
      <div className="cart-overview"><span><Icon name="cart" />{count} {count === 1 ? 'item' : 'itens'}</span><span><Icon name="users" />{people} {people === 1 ? 'participante' : 'participantes'}</span></div>
      <ul className="cart-items">{cart.items.map(line => <li className="cart-item" key={line.id}>
        <ProductImage id={line.product_id} name={line.name} hasImage={line.has_image ?? true} />
        <div className="cart-item-content"><div className="cart-item-title"><h2>{line.name}</h2><strong className="price">{formatCents(cents(line.unit_price) * line.quantity)}</strong></div>
          {line.participant_name && <ParticipantChip name={line.participant_name} />}
          <FulfillmentBadge mode={line.fulfillment_mode} showDineIn={cart.items.some(item => item.fulfillment_mode === 'TAKEAWAY')} />
          <p className="cart-options">{line.option_names?.length ? line.option_names.join(', ') : line.option_ids.length ? 'Opções selecionadas' : 'Sem alterações'}</p>{line.notes && <p className="cart-notes">Observação: {line.notes}</p>}
          <div className="cart-controls"><QuantitySelector name={line.name} quantity={line.quantity} disabled={locked} change={quantity => update(cart.items.map(item => item.id === line.id ? { ...item, quantity } : item))} />
            <div className="item-tools"><button className="icon-button" disabled={locked} aria-label={`Editar ${line.name}`} onClick={() => edit(line)}><Icon name="edit" size={18} /></button><button className="icon-button remove-item" disabled={locked} aria-label={`Remover ${line.name}`} onClick={() => update(cart.items.filter(item => item.id !== line.id))}><Icon name="trash" size={18} /></button></div>
          </div>
        </div>
      </li>)}</ul>
      <button className="general-note" disabled={locked} aria-expanded={notesOpen} onClick={() => startTransition(() => setNotesOpen(value => !value))}><Icon name="message" /><span>{cart.notes ? 'Editar observação geral' : 'Adicionar observação geral'}</span><Icon name="chevron" size={16} /></button>
      {notesOpen && <ViewTransition default="none" enter="motion-panel" exit="motion-panel"><div className="notes-editor"><label htmlFor="order-notes">Observação deste pedido</label><div><textarea id="order-notes" maxLength={NOTE_LIMIT} placeholder="Uma orientação para este envio" disabled={locked} value={cart.notes ?? ''} onChange={event => change({ ...cart, notes: event.target.value, idempotency_key: randomUUID() })} /><span>{cart.notes?.length ?? 0}/{NOTE_LIMIT}</span></div></div></ViewTransition>}
      <div className="cart-summary"><dl><div><dt>Subtotal</dt><dd>{total}</dd></div><div className="summary-total"><dt>Total estimado</dt><dd>{total}</dd></div></dl><p>Disponibilidade e preços serão conferidos no envio. Os valores finais da conta aparecerão na revisão da mesa.</p></div>
      {cart.pending && <div className="pending-order" role="status"><p>Este envio aguarda confirmação. Consulte o resultado antes de alterar o carrinho.</p><Button secondary disabled={busy} onClick={verify}>Verificar envio pendente</Button></div>}
      <StickyActionBar><Button secondary onClick={menu}>Continuar escolhendo</Button><PriceAction price={total} disabled={busy} onClick={send}>{busy ? 'Enviando…' : cart.pending ? 'Repetir envio' : 'Enviar pedido'}</PriceAction></StickyActionBar>
    </>}
  </section>;
}
