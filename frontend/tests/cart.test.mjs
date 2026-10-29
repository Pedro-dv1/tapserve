import assert from 'node:assert/strict';
import { test } from 'node:test';
import { afterFailedSubmission, decodeCart, emptyCart, orderPayload } from '../src/features/customer/cart.ts';

const line = { id: crypto.randomUUID(), product_id: crypto.randomUUID(), name: 'Produto', unit_price: '12.35', quantity: 2, option_ids: [crypto.randomUUID()], notes: 'Sem pimenta', participant_name: 'Ana' };
const cart = { ...emptyCart(), items: [line] };

test('stored cart is bounded; authoritative prices and statuses never enter the order payload', () => {
  assert.deepEqual(decodeCart(JSON.parse(JSON.stringify(cart))), cart);
  const payload = orderPayload({ ...cart, items: [{ ...line, unit_price: '0.01', status: 'DELIVERED', unit_id: 'foreign' }] });
  assert.deepEqual(payload, { idempotency_key: cart.idempotency_key, items: [{ product_id: line.product_id, quantity: 2, option_ids: line.option_ids, notes: line.notes, participant_name: line.participant_name }] });
  for (const bad of [{ ...cart, pending: 'false' }, { ...cart, idempotency_key: 'bad' }, { ...cart, items: Array(51).fill(line) }, ...[0, 100, 1.5].map(quantity => ({ ...cart, items: [{ ...line, quantity }] })), { ...cart, items: [{ ...line, notes: 'a'.repeat(501) }] }]) assert.throws(() => decodeCart(bad));
});

test('uncertain confirmation keeps its key and data locked, including a rejected retry or an absent receipt', () => {
  const unknown = afterFailedSubmission(cart);
  assert.equal(unknown.pending, true);
  assert.equal(unknown.idempotency_key, cart.idempotency_key);
  assert.deepEqual(unknown.items, cart.items);
  for (const status of [400, 404, 409, 429, 500]) assert.equal(afterFailedSubmission(unknown, status).pending, true);
  assert.equal(afterFailedSubmission(cart, 400).pending, false);
  assert.equal(afterFailedSubmission(cart, 500).pending, true);
});
