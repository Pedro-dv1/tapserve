import assert from 'node:assert/strict';
import { test } from 'node:test';
import { cents, decodeDetail, formatCents, selectionError, selectionTotal } from '../src/features/customer/menuData.ts';
import { batchStatus, isActiveBatch, statusStage } from '../src/features/customer/orderStatus.ts';
import { decodeCart, emptyCart, orderPayload } from '../src/features/customer/cart.ts';
import { fulfillmentMode } from '../src/features/customer/fulfillment.ts';

const cheddar = crypto.randomUUID(), bacon = crypto.randomUUID();
const product = decodeDetail({ id: crypto.randomUUID(), name: 'Burger', description: '', base_price: '34.00', has_image: false, groups: [{ id: crypto.randomUUID(), name: 'Adicionais', selection_type: 'MULTIPLE', required: true, min_choices: 1, max_choices: 2, options: [{ id: cheddar, name: 'Cheddar', additional_price: '4.00' }, { id: bacon, name: 'Bacon', additional_price: '6.00' }] }] });
test('integer cents preserve significant cents; product option limits reject incomplete or stale selections', () => {
  assert.equal(selectionTotal(product, [cheddar]), 3800);
  assert.equal(selectionTotal(product, [cheddar, bacon]), 4400);
  assert.equal(selectionTotal(product, [cheddar, bacon], 3), 13200);
  assert.equal(selectionError(product, [cheddar]), '');
  for (const selection of [[], [cheddar, cheddar], ['foreign']]) assert.notEqual(selectionError(product, selection), '');
  assert.equal(cents('34.90'), 3490);
  assert.equal(formatCents(3490).replace(/\s/g, ' '), 'R$ 34,90');
  for (const value of ['1.999', '-1.00', 'NaN', '0,01']) assert.throws(() => cents(value));
});
test('mixed sectors never mark a batch delivered early; cancellations are not delivered steps or active orders', () => {
  assert.equal(batchStatus([{ status: 'DELIVERED' }, { status: 'PREPARING' }]), 'PREPARING');
  assert.equal(batchStatus([{ status: 'ACCEPTED' }, { status: 'NEW' }]), 'NEW');
  assert.equal(batchStatus([{ status: 'DELIVERING' }, { status: 'READY' }]), 'READY');
  assert.equal(batchStatus([{ status: 'CANCELLED' }, { status: 'READY' }]), 'READY');
  assert.equal(batchStatus([{ status: 'CANCELLED' }]), 'CANCELLED');
  assert.equal(batchStatus([{ status: 'REJECTED' }]), 'REJECTED');
  assert.equal(batchStatus([{ status: 'REJECTED' }, { status: 'READY' }]), 'READY');
  assert.equal(isActiveBatch([{ status: 'REJECTED' }, { status: 'DELIVERED' }]), false);
  assert.equal(isActiveBatch([{ status: 'DELIVERED' }, { status: 'CANCELLED' }]), false);
  assert.equal(isActiveBatch([{ status: 'DELIVERED' }, { status: 'NEW' }]), true);
  assert.deepEqual(['NEW', 'ACCEPTED', 'PREPARING', 'READY', 'DELIVERING', 'DELIVERED', 'CANCELLED'].map(statusStage), [0, 0, 1, 2, 2, 3, -1]);
});
test('cart edit roundtrip retains photo/options/participant and general notes; payload whitelists server inputs', () => {
  const id = crypto.randomUUID(), participant = crypto.randomUUID();
  const cart = { ...emptyCart(), notes: 'Trazer juntos', items: [{ id, product_id: product.id, name: product.name, unit_price: '38.00', quantity: 2, option_ids: [cheddar], option_names: ['Cheddar'], has_image: true, participant_id: participant, participant_name: 'Ana', notes: 'Sem cebola' }] };
  assert.deepEqual(decodeCart(JSON.parse(JSON.stringify(cart))), cart);
  assert.deepEqual(orderPayload(cart).items, [{ product_id: product.id, quantity: 2, option_ids: [cheddar], notes: 'Sem cebola', participant_id: participant }]);
  assert.equal(orderPayload(cart).notes, 'Trazer juntos');
  assert.equal('unit_price' in orderPayload(cart).items[0], false);
  assert.equal('has_image' in orderPayload(cart).items[0], false);
  for (const change of [{ notes: 'x'.repeat(501) }, { items: [{ ...cart.items[0], participant_id: 'other-session' }] }, { items: [{ ...cart.items[0], has_image: 'true' }] }]) assert.throws(() => decodeCart({ ...cart, ...change }));
});

test('mixed fulfillment survives storage and submission without merging identical products', () => {
 const line = { id: crypto.randomUUID(), product_id: product.id, name: product.name, unit_price: '38.00', quantity: 2, option_ids: [cheddar], participant_name: '', notes: '' };
 const cart = { ...emptyCart(), items: [{ ...line, fulfillment_mode: 'DINE_IN', price_confirmed: true }, { ...line, id: crypto.randomUUID(), fulfillment_mode: 'TAKEAWAY', price_confirmed: true }] };
 const restored = decodeCart(JSON.parse(JSON.stringify(cart)));
 assert.deepEqual(restored, cart);
 assert.deepEqual(orderPayload(restored).items.map(item => item.fulfillment_mode), ['DINE_IN', 'TAKEAWAY']);
 assert.deepEqual(orderPayload(restored).items.map(item => item.expected_unit_price), ['38.00', '38.00']);
 assert.equal(fulfillmentMode(undefined), 'DINE_IN');
 assert.throws(() => fulfillmentMode('DELIVERY'));
 assert.throws(() => decodeCart({ ...cart, items: [{ ...line, fulfillment_mode: 'DELIVERY' }] }));
});
