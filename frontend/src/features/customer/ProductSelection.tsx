import { randomUUID } from '../../lib/uuid.ts';
import { startTransition, useEffect, useRef, useState, ViewTransition } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { record, request, text } from '../../lib/api';
import { Button, ErrorState, Icon, LoadingSkeleton, PopularityBadge, PriceAction, QuantitySelector, StickyActionBar } from '../../components/Interface';
import { brl, cents, decodeDetail, formatCents, NOTE_LIMIT, selectionError, selectionTotal } from './menuData';
import type { Group, ProductDetail } from './menuData';
import type { CartLine } from './cart';
import ProductGallery from './ProductGallery';
import { FulfillmentSelector } from '../../components/Fulfillment';
import type { FulfillmentMode } from './fulfillment';

export type Participant = { id: string | null; display_name: string };
export type ProductDraft = { quantity: number; option_ids: string[]; notes: string; participant_name: string; participant_id: string | null; fulfillment_mode: FulfillmentMode };
export default function ProductSelection({ identifier, initial, editing, participants, saveDraft, register, remove, confirm, locked }: {
  identifier: string; initial: ProductDraft | undefined; editing: CartLine | undefined; participants: Participant[];
  saveDraft: (draft: ProductDraft) => void; register: (name: string) => Promise<Participant>;
  remove: (person: Participant) => void;
  confirm: (line: CartLine) => void; locked: boolean;
}) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [draft, setDraft] = useState<ProductDraft>(initial ?? { quantity: editing?.quantity ?? 1, option_ids: editing?.option_ids ?? [], notes: editing?.notes ?? '', participant_name: editing?.participant_name ?? '', participant_id: editing?.participant_id ?? null, fulfillment_mode: editing?.fulfillment_mode ?? 'DINE_IN' });
  const [newPerson, setNewPerson] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const errorRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const controller = new AbortController(); setError('');
    void request(`/api/v1/public/products/${identifier}/`, 'GET', undefined, controller.signal).then(decodeDetail).then(data => { if (!controller.signal.aborted) setProduct(data); }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Produto indisponível. Volte ao cardápio.'); });
    return () => controller.abort();
  }, [identifier, reload]);
  useEffect(() => {
    if (draft.participant_name && !participants.some(person => person.display_name === draft.participant_name)) {
      const next = { ...draft, participant_name: '', participant_id: null }; setDraft(next); saveDraft(next);
    }
  }, [participants, draft, saveDraft]);
  function update(value: ProductDraft) { setDraft(value); saveDraft(value); }
  const setSelected: Dispatch<SetStateAction<string[]>> = value => update({ ...draft, option_ids: typeof value === 'function' ? value(draft.option_ids) : value });
  async function addPerson() {
    if (submitting.current || !name.trim()) return;
    submitting.current = true; setBusy(true); setError('');
    try { const person = await register(name.trim()); update({ ...draft, participant_name: person.display_name, participant_id: person.id }); setName(''); setNewPerson(false); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível adicionar participante.'); }
    finally { submitting.current = false; setBusy(false); }
  }
  async function add() {
    if (submitting.current || locked || !product) return;
    const invalid = selectionError(product, draft.option_ids);
    if (invalid) { setError(invalid); window.requestAnimationFrame(() => errorRef.current?.focus()); return; }
    submitting.current = true; setBusy(true); setError('');
    try {
      const row = record(await request('/api/v1/public/quote/', 'POST', { product_id: identifier, quantity: draft.quantity, option_ids: draft.option_ids, fulfillment_mode: draft.fulfillment_mode }));
      const price = text(row.unit_price); cents(price);
      if (!Array.isArray(row.options)) throw new Error('Resposta inválida do serviço.');
      confirm({ id: editing?.id ?? randomUUID(), product_id: identifier, name: text(row.name), has_image: product.has_image, option_names: row.options.map((option: unknown) => text(record(option).name)), unit_price: price, quantity: draft.quantity, option_ids: draft.option_ids, notes: draft.notes, participant_name: draft.participant_name, participant_id: draft.participant_id, fulfillment_mode: draft.fulfillment_mode, price_confirmed: true });
    } catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível conferir a seleção.'); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <section className="product-page">
    <div ref={errorRef} tabIndex={-1}>{error && <ErrorState message={error} {...(!product ? { retry: () => setReload(value => value + 1) } : {})} />}</div>
    {!product ? !error && <LoadingSkeleton product /> : <>
      <ProductGallery product={product} />
      {product.most_ordered && <PopularityBadge />}
      <div className="product-title"><h1>{product.name}</h1><strong className="price">{brl(product.base_price)}</strong></div>
      {product.description && <p className="product-description">{product.description}</p>}
      <section className="product-information" aria-label="Informações do produto">{product.long_description && <p>{product.long_description}</p>}<dl>{product.serving_info && <div><dt>Porção</dt><dd>{product.serving_info}</dd></div>}{product.ingredients && <div><dt>Ingredientes</dt><dd>{product.ingredients}</dd></div>}<div><dt>Alergênicos</dt><dd>{product.allergen_info || 'Não informado pelo restaurante. Consulte a equipe.'}</dd></div></dl></section>
      {(product.takeaway_enabled || draft.fulfillment_mode === 'TAKEAWAY') && <FulfillmentSelector value={draft.fulfillment_mode} change={fulfillment_mode => update({ ...draft, fulfillment_mode })} disabled={busy || locked} />}
      <div className="product-quantity"><span>Quantidade</span><QuantitySelector name={product.name} quantity={draft.quantity} disabled={busy || locked} change={quantity => update({ ...draft, quantity })} /></div>
      <section className="participant-picker"><div className="section-heading"><h2>Quem vai pedir?</h2><span>Opcional</span></div>
        <div className="participant-chips" aria-label="Quem vai consumir">
          {participants.map(person => <span className={`participant-chip ${draft.participant_name === person.display_name ? 'selected' : ''}`} key={person.id ?? person.display_name}><button className="participant-choice" aria-pressed={draft.participant_name === person.display_name} disabled={busy || locked} onClick={() => update({ ...draft, participant_name: draft.participant_name === person.display_name ? '' : person.display_name, participant_id: draft.participant_name === person.display_name ? null : person.id })}><Icon name="user" size={18} />{person.display_name}</button><button className="participant-remove" type="button" aria-label={`Remover ${person.display_name}`} disabled={busy || locked} onClick={() => remove(person)}><Icon name="close" size={16} /></button></span>)}
          {draft.participant_name && !participants.some(person => person.display_name === draft.participant_name) && <button className="participant-chip selected" aria-pressed="true" disabled={busy || locked} onClick={() => update({ ...draft, participant_name: '', participant_id: null })}><Icon name="user" size={18} />{draft.participant_name}</button>}
          <button className="participant-chip" aria-expanded={newPerson} disabled={busy || locked} onClick={() => startTransition(() => setNewPerson(value => !value))}><Icon name="plus" size={18} />Outra pessoa</button>
        </div>
        {newPerson && <ViewTransition default="none" enter="motion-panel" exit="motion-panel"><form className="person-editor" onSubmit={event => { event.preventDefault(); void addPerson(); }}><label htmlFor="new-participant">Nome temporário</label><div><input id="new-participant" required maxLength={100} value={name} autoComplete="off" disabled={busy} onChange={event => setName(event.target.value)} /><Button disabled={busy || !name.trim()}>Adicionar</Button></div></form></ViewTransition>}
      </section>
      <OptionChoices groups={product.groups} selected={draft.option_ids} setSelected={setSelected} busy={busy || locked} />
      <div className="notes-editor"><label htmlFor="product-notes">Alguma observação?</label><div><textarea id="product-notes" maxLength={NOTE_LIMIT} placeholder="Ex.: sem cebola, ponto da carne, etc." rows={2} value={draft.notes} disabled={busy || locked} onChange={event => update({ ...draft, notes: event.target.value })} /><span>{draft.notes.length}/{NOTE_LIMIT}</span></div></div>
      {locked && <ErrorState message="Verifique o envio pendente no carrinho antes de alterar a seleção." />}
      <StickyActionBar><PriceAction price={formatCents(selectionTotal(product, draft.option_ids, draft.quantity))} disabled={busy || locked} onClick={() => { void add(); }}>{busy ? 'Conferindo…' : editing ? 'Salvar alterações' : 'Adicionar ao carrinho'}</PriceAction></StickyActionBar>
    </>}
  </section>;
}

export function OptionChoices({ groups, selected, setSelected, busy }: { groups: Group[]; selected: string[]; setSelected: Dispatch<SetStateAction<string[]>>; busy: boolean }) {
  return <>{groups.map(group => <fieldset className="option-group" key={group.id}><legend>{group.name}</legend><p className="group-hint">{group.required ? 'Obrigatório' : 'Opcional'} · {group.selection_type === 'SINGLE' ? 'Escolha 1 opção' : `Escolha de ${group.min_choices} a ${group.max_choices}`}</p><div className="option-grid">
    {group.selection_type === 'SINGLE' && group.min_choices === 0 && <label className={`option-card ${!group.options.some(option => selected.includes(option.id)) ? 'selected' : ''}`}><input type="radio" name={group.id} disabled={busy} checked={!group.options.some(option => selected.includes(option.id))} onChange={() => setSelected(values => values.filter(value => !group.options.some(option => option.id === value)))} /><span className="option-copy"><strong>Sem adicional</strong><span>Sem acréscimo</span></span><span className="option-check"><Icon name="check" size={13} /></span></label>}
    {group.options.map(option => {
      const checked = selected.includes(option.id);
      const atMaximum = !checked && group.selection_type === 'MULTIPLE' && group.options.filter(choice => selected.includes(choice.id)).length >= group.max_choices;
      return <label className={`option-card ${checked ? 'selected' : ''} ${atMaximum || busy ? 'disabled' : ''}`} key={option.id}>
        <input type={group.selection_type === 'SINGLE' ? 'radio' : 'checkbox'} name={group.id} checked={checked} disabled={busy || atMaximum} onChange={event => setSelected(values => group.selection_type === 'SINGLE' ? [...values.filter(value => !group.options.some(choice => choice.id === value)), option.id] : event.target.checked ? [...values, option.id] : values.filter(value => value !== option.id))} />
        <span className="option-copy"><strong>{option.name}</strong><span>+ {brl(option.additional_price)}</span></span><span className="option-check"><Icon name="check" size={13} /></span>
      </label>;
    })}</div></fieldset>)}</>;
}
