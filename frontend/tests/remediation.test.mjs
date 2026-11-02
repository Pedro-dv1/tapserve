import assert from 'node:assert/strict';
import { test } from 'node:test';
import { clearManualDrafts, manualDraftKey, pendingManualKey, readPendingManual } from '../src/lib/manualDrafts.ts';
import { decodeAdmission } from '../src/lib/api.ts';
import { afterFailedSubmission } from '../src/features/customer/cart.ts';

test('manual drafts isolate operator, unit and occupation; logout removes notes and keeps only receipt keys', () => {
  const first = { staff: { id: 'staff-a' }, unit_id: 'unit-a' };
  const other = { staff: { id: 'staff-b' }, unit_id: 'unit-a' };
  const key = manualDraftKey(first, 'point-a', 'session-a');
  assert.notEqual(key, manualDraftKey(other, 'point-a', 'session-a'));
  assert.notEqual(key, manualDraftKey({ ...first, unit_id: 'unit-b' }, 'point-a', 'session-a'));
  assert.notEqual(key, manualDraftKey(first, 'point-a', 'session-b'));
  assert.notEqual(key, manualDraftKey(first, 'point-a', null));
  const id = crypto.randomUUID();
  const marker = pendingManualKey(first, 'point-a');
  assert.notEqual(marker, pendingManualKey(other, 'point-a'));
  const values = new Map([[key, JSON.stringify({ notes: 'private synthetic note', participant_name: 'Synthetic' })], [marker, JSON.stringify({ idempotency_key: id })], ['tapserve:manual:legacy', 'private legacy note']]);
  const storage = { get length() { return values.size; }, key(i) { return [...values.keys()][i] ?? null; }, removeItem(key) { values.delete(key); }, getItem(key) { return values.get(key) ?? null; }, setItem(key, value) { values.set(key, value); } };
  clearManualDrafts(storage);
  assert.equal(values.size, 1);
  assert.equal(readPendingManual(storage.getItem(marker)), id);
  assert.equal([...values.values()].some(value => value.includes('private')), false);
  assert.equal(afterFailedSubmission({ idempotency_key: id, pending: false, items: [] }, undefined).pending, true);
  assert.equal(afterFailedSubmission({ idempotency_key: id, pending: true, items: [] }, 409).pending, true);
  assert.throws(() => readPendingManual('malformed'));
  assert.throws(() => readPendingManual('{"idempotency_key":"invalid"}'));
});

test('pending admission decoder accepts no table data as authenticated context', () => {
  const value = { admission_id: crypto.randomUUID(), status: 'PENDING', expires_at: new Date().toISOString(), verification_code: 'ABCDEF12' };
  assert.equal(decodeAdmission(value).status, 'PENDING');
  for (const change of [{ status: 'AUTHENTICATED' }, { admission_id: 'invalid' }, { expires_at: 'never' }, { verification_code: '<script>' }]) assert.throws(() => decodeAdmission({ ...value, ...change }));
  assert.deepEqual(Object.keys(decodeAdmission({ ...value, session: { private: true } })).sort(), Object.keys(value).sort());
});
