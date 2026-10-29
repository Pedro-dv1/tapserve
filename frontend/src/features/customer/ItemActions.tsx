import { randomUUID } from '../../lib/uuid.ts';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Button, LoadingSkeleton, QuantitySelector } from '../../components/Interface';
import Toast from '../../components/Toast';
import Modal from '../../components/Modal';
import Feedback from '../../components/Feedback';
import { ApiError, record, request, text } from '../../lib/api';
import type { Item } from './orderData';
import { decodeDetail } from './menuData';
import type { ProductDetail } from './menuData';
import { OptionChoices } from './ProductSelection';
import { FulfillmentSelector } from '../../components/Fulfillment';

type Participant = { id: string; display_name: string };
export default function ItemActions({ item, manual = false, canEdit, canCancel, participants, changed }: { item: Item; manual?: boolean; canEdit: boolean; canCancel: boolean; participants?: Participant[]; changed: (updated?: unknown) => void }) {
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState<'edit' | 'cancel' | null>(null);
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [selected, setSelected] = useState(item.option_ids);
  const [quantity, setQuantity] = useState(item.quantity);
  const [notes, setNotes] = useState(item.notes);
  const [fulfillment, setFulfillment] = useState(item.fulfillment_mode);
  const [participant, setParticipant] = useState(item.participant_id ?? '');
  const [version, setVersion] = useState(item.version);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<{ mode: 'edit' | 'cancel'; body: Record<string, unknown> } | null>(null);
  const [conflict, setConflict] = useState(false);
  const mutation = useRef(false);
  useEffect(() => {
    if (mode !== 'edit') return;
    const controller = new AbortController();
    const path = manual ? `/api/v1/staff/products/${item.product_id}/choices/` : `/api/v1/public/products/${item.product_id}/`;
    void request(path, 'GET', undefined, controller.signal).then(decodeDetail).then(value => { if (!controller.signal.aborted) setProduct(value); }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar as opções.'); });
    return () => controller.abort();
  }, [mode, item.product_id, manual]);
  function open(next: 'edit' | 'cancel') {
    if (mutation.current || pending && pending.mode !== next) return;
    if (!pending) {
      setSelected(item.option_ids); setQuantity(item.quantity); setNotes(item.notes); setFulfillment(item.fulfillment_mode);
      setParticipant(item.participant_id ?? ''); setVersion(item.version); setProduct(null); setError(''); setConflict(false);
    }
    setMode(next);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (mutation.current || !mode || conflict || !(mode === 'edit' ? canEdit : canCancel)) return;
    const values = new FormData(event.currentTarget);
    const body = pending?.body ?? { idempotency_key: randomUUID(), expected_version: version, ...((manual || mode === 'cancel') ? { reason: String(values.get('reason') ?? '') } : {}), ...(mode === 'edit' ? { quantity, notes, option_ids: selected, fulfillment_mode: fulfillment, ...(participants ? { participant_id: participant || null } : {}) } : {}) };
    const wasPending = pending !== null;
    mutation.current = true; setPending({ mode, body }); setBusy(true); setError('');
    try {
      const result = record(await request(`/api/v1/${manual ? 'staff' : 'public'}/items/${item.id}/${mode === 'cancel' ? 'cancel/' : ''}`, mode === 'cancel' ? 'POST' : 'PATCH', body));
      text(result.id); setPending(null); setMode(null); setMessage(mode === 'edit' ? 'Alterações salvas.' : 'Pedido cancelado.'); changed(result);
    } catch (cause: unknown) {
      if (!wasPending && cause instanceof ApiError && cause.status >= 400 && cause.status < 500) setPending(null);
      if (cause instanceof ApiError && cause.status === 409) { setConflict(!wasPending); changed(); }
      setError(cause instanceof ApiError && cause.status === 409 ? `${cause.message} Feche e abra novamente para revisar o pedido atualizado.` : cause instanceof ApiError && cause.status === 400 ? Object.values(cause.fields).join(' ') || 'Confira os dados da alteração.' : `${cause instanceof Error ? cause.message : 'Não foi possível confirmar.'} Tente novamente com os mesmos dados.`);
    } finally { mutation.current = false; setBusy(false); }
  }
  if (['DELIVERED', 'CANCELLED', 'REJECTED'].includes(item.status) && !mode) return null;
  return <><Toast message={message} clear={setMessage} /><div className="actions">{canEdit && <Button secondary disabled={busy || pending !== null && pending.mode !== 'edit'} onClick={() => open('edit')}>Alterar item</Button>}{canCancel && <Button className="ui-danger" disabled={busy || pending !== null && pending.mode !== 'cancel'} onClick={() => open('cancel')}>{manual ? 'Cancelar item' : 'Cancelar pedido'}</Button>}{!manual && !canEdit && !canCancel && <p>Para alterar este item, chame um atendente na aba Mesa.</p>}</div>
    {mode && <Modal open title={mode === 'cancel' ? 'Cancelar pedido?' : 'Alterar item'} description={mode === 'cancel' ? 'Tem certeza de que deseja cancelar este pedido?' : ''} busy={busy} close={() => setMode(null)}><form onSubmit={event => { void submit(event); }} aria-busy={busy}>
      <p><strong>{item.name}</strong>{item.option_names.length > 0 && <><br />{item.option_names.join(', ')}</>}</p>
      {error && <Feedback tone="error">{error}</Feedback>}
      {!(mode === 'edit' ? canEdit : canCancel) && <Feedback tone="warning">Este item não permite mais esta alteração. Volte para acompanhar o pedido.</Feedback>}
      <fieldset disabled={busy || pending !== null || conflict}>
        {mode === 'edit' && <><p>Quantidade</p><QuantitySelector quantity={quantity} disabled={busy || pending !== null || conflict} change={setQuantity} name={item.name} /><label>Observações (opcional)<textarea name="notes" maxLength={500} value={notes} onChange={event => setNotes(event.target.value)} rows={3} /></label>{participants && <label>Participante<select value={participant} onChange={event => setParticipant(event.target.value)}><option value="">Sem participante</option>{item.participant_id && !participants.some(person => person.id === item.participant_id) && <option value={item.participant_id}>{item.participant_name ?? 'Participante atual'}</option>}{participants.map(person => <option value={person.id} key={person.id}>{person.display_name}</option>)}</select></label>}{product && (product.takeaway_enabled || fulfillment === 'TAKEAWAY') && <FulfillmentSelector value={fulfillment} change={setFulfillment} disabled={busy || pending !== null || conflict || !manual && item.status !== 'NEW'} />}{product ? <OptionChoices groups={product.groups} selected={selected} setSelected={setSelected} busy={busy || pending !== null || conflict} /> : <LoadingSkeleton variant="options" />}</>}
        {(manual || mode === 'cancel') && <label>Motivo (opcional)<textarea name="reason" maxLength={300} placeholder="Informe o motivo, se desejar..." rows={3} /></label>}
      </fieldset>
      <div className="dialog-actions"><Button secondary type="button" disabled={busy} onClick={() => setMode(null)}>Voltar</Button><Button className={mode === 'cancel' ? 'ui-danger' : ''} type="submit" disabled={busy || conflict || (mode === 'edit' ? !canEdit || product === null : !canCancel)}>{busy ? 'Salvando…' : pending ? 'Repetir com os mesmos dados' : mode === 'cancel' ? 'Confirmar cancelamento' : 'Salvar alterações'}</Button></div>
    </form></Modal>}
  </>;
}
