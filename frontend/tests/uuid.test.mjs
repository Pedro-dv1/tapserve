import assert from 'node:assert/strict';
import { test } from 'node:test';
import { randomUUID } from '../src/lib/uuid.ts';
import { decodeCart, emptyCart } from '../src/features/customer/cart.ts';

test('HTTP LAN UUID fallback preserves secure randomness, version/variant and cart contracts', () => {
  const original = globalThis.crypto;
  let count = 0;
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: { getRandomValues(bytes) { count++; return original.getRandomValues(bytes); } } });
  try {
    const ids = Array.from({ length: 100 }, () => randomUUID());
    assert.equal(new Set(ids).size, 100);
    assert.ok(ids.every(id => /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id)));
    const cart = emptyCart();
    assert.deepEqual(decodeCart(JSON.parse(JSON.stringify(cart))), cart);
    assert.equal(count, 101);
  } finally { Object.defineProperty(globalThis, 'crypto', { configurable: true, value: original }); }
});

test('UUID generation keeps the native implementation when available and fails closed without entropy', () => {
  const original = globalThis.crypto, expected = original.randomUUID();
  try {
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: { randomUUID: () => expected } });
    assert.equal(randomUUID(), expected);
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: { getRandomValues() { throw new Error('entropy unavailable'); } } });
    assert.throws(randomUUID, /entropy unavailable/);
  } finally { Object.defineProperty(globalThis, 'crypto', { configurable: true, value: original }); }
});
