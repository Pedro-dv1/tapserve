import assert from 'node:assert/strict';
import { test } from 'node:test';
import { lockTag, nfcCapabilities, nfcError, verifyTag, writeTag } from '../src/features/staff/nfc.ts';
import { decodeProduct } from '../src/features/customer/menuData.ts';

test('NFC writes one real URL record and reports rejected operations', async () => {
  const signal = new AbortController().signal; const calls = [];
  await writeTag({ write: async (...args) => calls.push(args) }, 'https://example.com/a/point', signal);
  assert.deepEqual(calls, [[{ records: [{ recordType: 'url', data: 'https://example.com/a/point' }] }, { signal }]]);
  await assert.rejects(writeTag({ write: async () => { throw new DOMException('denied', 'NotAllowedError'); } }, 'https://example.com', signal));
  for (const name of ['NotAllowedError', 'NotSupportedError', 'NotReadableError', 'NetworkError', 'AbortError']) assert.notEqual(nfcError(new DOMException('', name)), '');
  assert.match(nfcError(new DOMException('', 'NotAllowedError')), /negada/);
});

test('NFC verification waits for the actual record, rejects wrong tags and cancels cleanly', async () => {
  const url = 'https://example.com/a/point';
  const event = text => ({ message: { records: [{ recordType: 'url', data: new DataView(new TextEncoder().encode(text).buffer) }] } });
  const reader = { scan: async () => {}, onreading: null, onreadingerror: null };
  const controller = new AbortController();
  const valid = verifyTag(reader, url, controller.signal);
  assert.equal(typeof reader.onreading, 'function'); reader.onreading(event(url)); await valid;
  assert.equal(reader.onreading, null);
  const wrong = verifyTag(reader, url, controller.signal); reader.onreading(event('https://foreign.example')); await assert.rejects(wrong, /não corresponde/);
  const cancelled = verifyTag(reader, url, controller.signal); controller.abort(); await assert.rejects(cancelled, { name: 'AbortError' });
  assert.equal(reader.onreading, null);
  await assert.rejects(verifyTag({ scan: async () => { throw new DOMException('', 'NotAllowedError'); } }, url, new AbortController().signal), { name: 'NotAllowedError' });
});

test('legacy products remain valid without video and invalid video flags fail closed', () => {
  const row = { id: 'product', name: 'Prato', description: '', base_price: '10.00', has_image: true };
  assert.equal(decodeProduct(row).has_video, false);
  assert.equal(decodeProduct({ ...row, has_video: true }).has_video, true);
  assert.throws(() => decodeProduct({ ...row, has_video: 'true' }));
});

test('NFC lock is unavailable without support, verifies before locking, and propagates failure', async () => {
  assert.deepEqual(nfcCapabilities({ isSecureContext: false, NDEFReader: class {} }), { supported: false, canLock: false });
  assert.deepEqual(nfcCapabilities({ isSecureContext: true }), { supported: false, canLock: false });
  class Reader { makeReadOnly() {} }
  assert.deepEqual(nfcCapabilities({ isSecureContext: true, NDEFReader: Reader }), { supported: true, canLock: true });
  const url = 'https://example.com/a/point'; const controller = new AbortController(); let locked = 0;
  const reader = { scan: async () => {}, makeReadOnly: async () => { locked++; }, onreading: null, onreadingerror: null };
  const result = lockTag(reader, url, controller.signal);
  assert.equal(locked, 0);
  reader.onreading({ message: { records: [{ recordType: 'url', data: new DataView(new TextEncoder().encode(url).buffer) }] } });
  await result; assert.equal(locked, 1);
  reader.makeReadOnly = async () => { throw new DOMException('unsupported tag', 'NotSupportedError'); };
  const failed = lockTag(reader, url, controller.signal);
  reader.onreading({ message: { records: [{ recordType: 'url', data: new DataView(new TextEncoder().encode(url).buffer) }] } });
  await assert.rejects(failed, { name: 'NotSupportedError' });
  await assert.rejects(lockTag({ scan: async () => {} }, url, controller.signal), /não suportado/);
});
