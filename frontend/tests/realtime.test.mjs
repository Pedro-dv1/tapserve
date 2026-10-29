import assert from 'node:assert/strict';
import { test } from 'node:test';
import { realtimeSnapshot, subscribeRealtime } from '../src/lib/realtime.ts';

test('one socket per audience, deduplication, reconnection snapshot and complete cleanup', async () => {
  const previous = Object.fromEntries(['window', 'document', 'navigator', 'location', 'WebSocket', 'fetch'].map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const timers = new Map(); let sequence = 0; const sockets = [];
  const window = new EventTarget();
  window.setTimeout = (callback, delay) => { timers.set(++sequence, { callback, delay, interval: false }); return sequence; };
  window.setInterval = (callback, delay) => { timers.set(++sequence, { callback, delay, interval: true }); return sequence; };
  window.clearInterval = window.clearTimeout = id => timers.delete(id);
  class Socket {
    static CLOSING = 2;
    readyState = 0; closed = false;
    constructor(url) { this.url = url; sockets.push(this); }
    open() { this.readyState = 1; this.onopen?.(); }
    message(value) { this.onmessage?.({ data: JSON.stringify(value) }); }
    send(value) { this.sent = JSON.parse(value); }
    close(code = 1000) { this.closed = true; this.readyState = 3; this.onclose?.({ code }); }
  }
  const document = new EventTarget(); document.visibilityState = 'visible';
  for (const [name, value] of Object.entries({ window, document, navigator: { onLine: true }, location: { protocol: 'https:', host: 'example.test' }, WebSocket: Socket, fetch: async () => new Response('{}') })) Object.defineProperty(globalThis, name, { configurable: true, value });
  function runTimeout(delay) { const found = [...timers].find(([, timer]) => !timer.interval && (delay === undefined || timer.delay === delay)); assert.ok(found); timers.delete(found[0]); found[1].callback(); }
  try {
    const first = subscribeRealtime('public', () => {}); const second = subscribeRealtime('public', () => {});
    assert.equal(sockets.length, 1); assert.equal(sockets[0].url, 'wss://example.test/ws/v1/public/');
    sockets[0].open();
    assert.equal(realtimeSnapshot('public').revision, 0);
    sockets[0].message({ type: 'refresh', event_id: null, kind: 'SNAPSHOT_REQUIRED' });
    const initial = realtimeSnapshot('public').revision;
    sockets[0].message({ type: 'refresh', event_id: '5', kind: 'ITEM_STATUS_CHANGED' });
    sockets[0].message({ type: 'refresh', event_id: '5', kind: 'ITEM_STATUS_CHANGED' });
    sockets[0].message({ type: 'heartbeat' });
    assert.deepEqual(sockets[0].sent, { type: 'heartbeat_ack' });
    assert.equal(realtimeSnapshot('public').revision, initial + 1);
    const before = realtimeSnapshot('public');
    sockets[0].message({ type: 'refresh', event_id: '6', kind: 'CALL_ASSIGNED' });
    assert.equal(realtimeSnapshot('public').ordersRevision, before.ordersRevision);
    assert.equal(realtimeSnapshot('public').catalogRevision, before.catalogRevision);
    assert.equal(realtimeSnapshot('public').callsRevision, before.callsRevision + 1);
    sockets[0].message({ type: 'refresh', event_id: '7', kind: 'CATALOG_CHANGED' });
    assert.equal(realtimeSnapshot('public').ordersRevision, before.ordersRevision);
    assert.equal(realtimeSnapshot('public').catalogRevision, before.catalogRevision + 1);
    const afterEvents = realtimeSnapshot('public').revision;
    first(); assert.equal(sockets[0].closed, false);
    sockets[0].close(1006); await new Promise(resolve => setImmediate(resolve));
    runTimeout(); assert.equal(sockets.length, 2); sockets[1].open();
    assert.equal(realtimeSnapshot('public').revision, afterEvents);
    sockets[1].message({ type: 'refresh', event_id: null, kind: 'SNAPSHOT_REQUIRED' });
    assert.equal(realtimeSnapshot('public').revision, afterEvents + 1);
    sockets[1].close(4401); await new Promise(resolve => setImmediate(resolve));
    assert.match(realtimeSnapshot('public').status, /Acesso/);
    assert.equal([...timers.values()].filter(timer => !timer.interval).length, 0);
    second(); runTimeout(100); assert.equal(timers.size, 0);
    const stop = subscribeRealtime('staff', () => {}); sockets.at(-1).open();
    for (let attempt = 1; attempt <= 6; attempt++) {
      sockets.at(-1).close(1006); await new Promise(resolve => setImmediate(resolve));
      if (attempt < 6) { runTimeout(); sockets.at(-1).open(); }
    }
    assert.match(realtimeSnapshot('staff').status, /indisponíveis/);
    const revision = realtimeSnapshot('staff').revision;
    [...timers.values()].find(timer => timer.interval && timer.delay === 30_000).callback();
    assert.equal(realtimeSnapshot('staff').revision, revision + 1);
    const count = sockets.length; window.dispatchEvent(new Event('online')); assert.equal(sockets.length, count + 1);
    stop(); runTimeout(100); assert.equal(timers.size, 0);
    // Visibility can resume while the previous socket is still closing.
    const release = subscribeRealtime('public', () => {}); const closing = sockets.at(-1);
    closing.open(); closing.readyState = Socket.CLOSING;
    document.dispatchEvent(new Event('visibilitychange'));
    assert.notEqual(sockets.at(-1), closing);
    assert.equal([...timers.values()].filter(timer => timer.interval).length, 2);
    closing.close(1006); sockets.at(-1).open();
    release(); runTimeout(100); assert.equal(timers.size, 0);
    // A stalled authentication check must not prevent bounded reconnect or leak its timer.
    globalThis.fetch = async (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true }));
    const finish = subscribeRealtime('public', () => {}); sockets.at(-1).open(); sockets.at(-1).close(1006);
    runTimeout(5000); await new Promise(resolve => setImmediate(resolve));
    assert.equal([...timers.values()].filter(timer => !timer.interval).length, 1);
    runTimeout(); assert.equal(sockets.at(-1).readyState, 0);
    finish(); runTimeout(100); assert.equal(timers.size, 0);
  } finally {
    for (const [name, descriptor] of Object.entries(previous)) { if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name]; }
  }
});
