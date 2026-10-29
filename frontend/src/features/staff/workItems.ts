import { record, text } from '../../lib/api';
import { cents } from '../customer/menuData';
import type { Item } from '../customer/orderData';
import { statusNames } from '../customer/orderStatus';
import { fulfillmentMode } from '../customer/fulfillment';

export type WorkItem = Item & { session_id: string; points: string[]; sector_name: string; sector_id: string; created_at: string };

export function decodeWorkItems(value: unknown) {
  const row = record(value);
  if (!Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
  return { next: typeof row.next === 'string', results: row.results.map((value: unknown): WorkItem => {
    const item = record(value), snapshot = record(item.snapshot);
    const status = text(item.status);
    if (!Array.isArray(item.point_names) || !Array.isArray(snapshot.options) || typeof item.quantity !== 'number' || !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 99 || typeof item.version !== 'number' || !Number.isInteger(item.version) || item.version < 1 || typeof item.can_customer_change !== 'boolean' || !Object.hasOwn(statusNames, status)) throw new Error('Resposta inválida do serviço.');
    const created = text(item.created_at);
    if (!Number.isFinite(Date.parse(created))) throw new Error('Data do pedido inválida.');
    const total = text(item.line_total); cents(total);
    return {
      id: text(item.id), product_id: text(item.product_id), version: item.version,
      fulfillment_mode: fulfillmentMode(item.fulfillment_mode),
      name: text(snapshot.name), sector_name: text(snapshot.sector_name), sector_id: text(item.sector_id),
      option_ids: snapshot.options.map((value: unknown) => text(record(value).id)),
      option_names: snapshot.options.map((value: unknown) => text(record(value).name)),
      quantity: item.quantity, notes: text(item.notes), status: status as Item['status'],
      line_total: total, created_at: created, session_id: text(item.session_id),
      points: item.point_names.map(text), participant_id: item.participant_id == null ? null : text(item.participant_id), participant_name: item.participant_name === null ? null : text(item.participant_name),
      delivered_by_id: item.delivered_by_id === null ? null : text(item.delivered_by_id),
      editable_until: text(item.editable_until), can_customer_change: item.can_customer_change,
    };
  }) };
}

export function elapsedMinutes(created: string, now: number) { return Math.max(0, Math.floor((now - Date.parse(created)) / 60_000)); }
