import { record, text } from '../../lib/api';
import { cents } from './menuData';
import { statusNames } from './orderStatus';
import type { OrderStatus } from './orderStatus';
import { fulfillmentMode } from './fulfillment';
import type { FulfillmentMode } from './fulfillment';

export type Session = { id: string; status: string; version: number; points: { id: string; name: string }[]; participants: { id: string; display_name: string }[] };
export type Item = { id: string; product_id: string; version: number; option_ids: string[]; option_names: string[]; can_customer_change: boolean; editable_until: string; name: string; quantity: number; notes: string; line_total: string; status: OrderStatus; participant_id: string | null; participant_name: string | null; delivered_by_id: string | null; fulfillment_mode: FulfillmentMode };
export type Batch = { origin?: string; staff_name?: string | null; point_names?: string[]; id: string; created_at: string; notes: string; items: Item[] };
export function latestItem(current: Item | undefined, incoming: Item): Item {
  return current && current.version > incoming.version ? current : incoming;
}
export function decodeSession(value: unknown): Session | null {
  const wrapper = record(value); if (wrapper.session === null) return null;
  return decodeSessionValue(wrapper.session);
}
export function decodeSessionValue(value: unknown): Session {
  const row = record(value);
  if (!Array.isArray(row.points) || !Array.isArray(row.participants) || typeof row.version !== 'number') throw new Error('Resposta inválida do serviço.');
  return { id: text(row.id), status: text(row.status), version: row.version, points: row.points.map((value: unknown) => { const point = record(value); return { id: text(point.id), name: text(point.name) }; }), participants: row.participants.filter((value: unknown) => record(value).active !== false).map((value: unknown) => { const person = record(value); return { id: text(person.id), display_name: text(person.display_name) }; }) };
}
export function decodeBatches(value: unknown): { results: Batch[]; next: boolean } {
  const row = record(value); if (!Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
  return { next: typeof row.next === 'string', results: row.results.map((value: unknown) => {
    const batch = record(value); if (!Array.isArray(batch.items)) throw new Error('Resposta inválida do serviço.');
    return { origin: batch.origin === undefined ? 'CUSTOMER' : text(batch.origin), staff_name: batch.staff_name == null ? null : text(batch.staff_name), point_names: Array.isArray(batch.point_names) ? batch.point_names.map(text) : [], id: text(batch.id), created_at: text(batch.created_at), notes: batch.notes === undefined ? '' : text(batch.notes), items: batch.items.map(decodeItem) };
  }) };
}
export function decodeItem(value: unknown): Item {
  const item = record(value); const snapshot = record(item.snapshot);
  if (typeof item.quantity !== 'number' || !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 99 || typeof item.version !== 'number' || !Number.isInteger(item.version) || item.version < 1 || typeof item.can_customer_change !== 'boolean' || !Array.isArray(snapshot.options) || typeof item.status !== 'string' || !Object.hasOwn(statusNames, item.status)) throw new Error('Resposta inválida do serviço.');
  const total = text(item.line_total); cents(total);
  return { id: text(item.id), product_id: text(item.product_id), version: item.version, fulfillment_mode: fulfillmentMode(item.fulfillment_mode), option_ids: snapshot.options.map((value: unknown) => text(record(value).id)), option_names: snapshot.options.map((value: unknown) => text(record(value).name)), can_customer_change: item.can_customer_change, editable_until: text(item.editable_until), name: text(snapshot.name), quantity: item.quantity, notes: text(item.notes), status: item.status as OrderStatus, line_total: total, participant_id: item.participant_id == null ? null : text(item.participant_id), participant_name: item.participant_name === null ? null : text(item.participant_name), delivered_by_id: item.delivered_by_id === null ? null : text(item.delivered_by_id) };
}
