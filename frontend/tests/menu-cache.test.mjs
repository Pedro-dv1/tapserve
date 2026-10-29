import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MenuCache } from '../src/features/customer/menuCache.ts';

test('menu cache reuses fresh filters, expires, invalidates, bounds memory and isolates workspaces', async () => {
  const fetch = globalThis.fetch, now = Date.now;
  let time = 100, calls = 0;
  globalThis.fetch = async () => { calls++; return new Response(JSON.stringify({ results: [{ name: `v${calls}` }], next: null })); };
  Date.now = () => time;
  const cache = new MenuCache(), signal = new AbortController().signal;
  const path = '/api/v1/public/menu/?page=1';
  try {
    const first = await cache.get(path, '0:0', signal);
    assert.deepEqual(await cache.get(path, '0:0', signal), first);
    assert.equal(calls, 1);
    assert.notDeepEqual(await new MenuCache().get(path, '0:0', signal), first);
    assert.equal(calls, 2);
    await cache.get(path, '1:0', signal); assert.equal(calls, 3);
    time += 30_001;
    await cache.get(path, '1:0', signal); assert.equal(calls, 4);
    for (let page = 2; page <= 22; page++) await cache.get(`/api/v1/public/menu/?page=${page}`, '1:0', signal);
    const before = calls;
    await cache.get(path, '1:0', signal); assert.equal(calls, before + 1);
    await assert.rejects(cache.get('/api/v1/public/orders/?page=1', '0', signal));
    await assert.rejects(cache.get('/api/v1/csrf/?', '0', signal));
  } finally { globalThis.fetch = fetch; Date.now = now; }
});

test('menu cache never retains errors, malformed responses or aborted obsolete requests', async () => {
  const original = globalThis.fetch, cache = new MenuCache();
  const path = '/api/v1/public/categories/?page=1', controller = new AbortController();
  let calls = 0;
  try {
    globalThis.fetch = async () => { calls++; return new Response('{}', { status: 503 }); };
    await assert.rejects(cache.get(path, '0', controller.signal));
    globalThis.fetch = async () => { calls++; return new Response('{}'); };
    await assert.rejects(cache.get(path, '0', controller.signal));
    globalThis.fetch = async () => { calls++; controller.abort(); return new Response('{"results":[]}'); };
    await cache.get(path, '0', controller.signal);
    globalThis.fetch = async () => { calls++; return new Response('{"results":[]}'); };
    await cache.get(path, '0', new AbortController().signal);
    assert.equal(calls, 4);
  } finally { globalThis.fetch = original; }
});
