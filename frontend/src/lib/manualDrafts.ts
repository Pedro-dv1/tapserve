import type { StaffContext } from './api.ts';
import { record, text } from './api.ts';

type Store = Pick<Storage, 'length' | 'key' | 'getItem' | 'setItem' | 'removeItem'>;
export function manualDraftKey(context: StaffContext, point: string, session: string | null) {
  return `tapserve:manual:v2:${context.unit_id}:${context.staff.id}:${point}:${session ?? 'unoccupied'}`;
}
export function pendingManualKey(context: StaffContext, point: string) {
  return `tapserve:manual-pending:${context.unit_id}:${context.staff.id}:${point}`;
}
export function readPendingManual(raw: string | null): string | null {
  if (!raw) return null;
  const key = text(record(JSON.parse(raw) as unknown).idempotency_key);
  if (!/^[0-9a-f-]{36}$/.test(key)) throw new Error('Identificador de envio pendente inválido.');
  return key;
}
export function clearManualDrafts(storage: Store) {
  // Pending markers contain only an opaque receipt key; notes and participants are removed.
  const keys = Array.from({ length: storage.length }, (_, i) => storage.key(i));
  for (const key of keys) if (key?.startsWith('tapserve:manual:')) storage.removeItem(key);
}
