import { randomUUID } from '../../lib/uuid.ts';
import { record, text } from '../../lib/api.ts';
import { fulfillmentMode } from './fulfillment.ts';
import type { FulfillmentMode } from './fulfillment.ts';

export type CartLine = { id: string; product_id: string; name: string; unit_price: string; quantity: number; option_ids: string[]; notes: string; participant_name: string; participant_id?: string | null; option_names?: string[]; has_image?: boolean; fulfillment_mode?: FulfillmentMode; price_confirmed?: boolean };
export type Cart = { items: CartLine[]; idempotency_key: string; pending: boolean; notes?: string };
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function emptyCart(): Cart { return { items: [], idempotency_key: randomUUID(), pending: false }; }
export function decodeCart(value: unknown): Cart {
  const row = record(value);
  if (!Array.isArray(row.items) || row.items.length > 50 || typeof row.pending !== 'boolean' || typeof row.idempotency_key !== 'string' || !uuid.test(row.idempotency_key)) throw new Error('Carrinho inválido.');
  if (row.notes !== undefined && (typeof row.notes !== 'string' || row.notes.length > 500)) throw new Error('Carrinho inválido.');
  return { idempotency_key: row.idempotency_key, pending: row.pending, ...(typeof row.notes === 'string' ? { notes: row.notes } : {}), items: row.items.map((value: unknown) => {
    const line = record(value);
    if (typeof line.id !== 'string' || !uuid.test(line.id) || typeof line.product_id !== 'string' || !uuid.test(line.product_id) || typeof line.quantity !== 'number' || !Number.isInteger(line.quantity) || line.quantity < 1 || line.quantity > 99 || !Array.isArray(line.option_ids) || line.option_ids.length > 100 || !line.option_ids.every((id: unknown) => typeof id === 'string' && uuid.test(id)) || typeof line.unit_price !== 'string' || !/^\d{1,10}\.\d{2}$/.test(line.unit_price)) throw new Error('Carrinho inválido.');
    const name = text(line.name), notes = text(line.notes), participant = text(line.participant_name);
    const mode = fulfillmentMode(line.fulfillment_mode);
    if (line.price_confirmed !== undefined && typeof line.price_confirmed !== 'boolean') throw new Error('Carrinho inválido.');
    if (name.length > 100 || notes.length > 500 || participant.length > 100) throw new Error('Carrinho inválido.');
    if (line.participant_id !== undefined && line.participant_id !== null && (typeof line.participant_id !== 'string' || !uuid.test(line.participant_id))) throw new Error('Carrinho inválido.');
    if (line.has_image !== undefined && typeof line.has_image !== 'boolean') throw new Error('Carrinho inválido.');
    if (line.option_names !== undefined && (!Array.isArray(line.option_names) || line.option_names.length > 100 || !line.option_names.every((value: unknown) => typeof value === 'string' && value.length <= 100))) throw new Error('Carrinho inválido.');
    return { id: line.id, product_id: line.product_id, quantity: line.quantity, unit_price: line.unit_price, name, notes, participant_name: participant, option_ids: line.option_ids as string[], ...(line.fulfillment_mode !== undefined ? { fulfillment_mode: mode } : {}), ...(typeof line.price_confirmed === 'boolean' ? { price_confirmed: line.price_confirmed } : {}), ...(line.participant_id !== undefined ? { participant_id: line.participant_id as string | null } : {}), ...(typeof line.has_image === 'boolean' ? { has_image: line.has_image } : {}), ...(Array.isArray(line.option_names) ? { option_names: line.option_names as string[] } : {}) };
  }) };
}
export function orderPayload(cart: Cart) {
  return { idempotency_key: cart.idempotency_key, ...(cart.notes ? { notes: cart.notes } : {}), items: cart.items.map(line => ({ product_id: line.product_id, quantity: line.quantity, option_ids: line.option_ids, notes: line.notes, ...(line.fulfillment_mode ? { fulfillment_mode: line.fulfillment_mode } : {}), ...(line.price_confirmed ? { expected_unit_price: line.unit_price } : {}), ...(line.participant_id ? { participant_id: line.participant_id } : { participant_name: line.participant_name }) })) };
}
// A rejection of a retry does not prove that the original timed-out request failed.
export function afterFailedSubmission(cart: Cart, status?: number): Cart {
  return { ...cart, pending: cart.pending || status === undefined || status < 400 || status >= 500 };
}
