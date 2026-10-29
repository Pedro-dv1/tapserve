import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, getHealth, decodeContext, decodeStaff, decodeRoles, decodeStaffPage, request, decodeRefresh } from '../src/lib/api.ts';

const originalFetch = globalThis.fetch;

test('notification decoder accepts only bounded refresh messages', () => {
  assert.deepEqual(decodeRefresh({ type: 'refresh', event_id: '123', kind: 'ORDER_CREATED' }), { event_id: '123', kind: 'ORDER_CREATED' });
  assert.equal(decodeRefresh({ type: 'refresh', event_id: null, kind: 'SNAPSHOT_REQUIRED' }).event_id, null);
  for (const value of [null, { type: 'status', status: 'DELIVERED' }, { type: 'refresh', event_id: 'injected', kind: 'ORDER_CREATED' }, { type: 'refresh', event_id: '1', kind: 'x'.repeat(100) }]) assert.throws(() => decodeRefresh(value));
});

test('health decoder accepts only the implemented contract', async () => {
  globalThis.fetch = async () => Response.json({ status: 'ok', database: 'ok' });
  try { assert.deepEqual(await getHealth(new AbortController().signal), { status: 'ok', database: 'ok' }); }
  finally { globalThis.fetch = originalFetch; }
});

for (const data of [null, { status: 'ok' }, { status: 'fake', database: 'ok' }, { status: 'ok', database: 1 }]) {
  test(`reject invalid health shape: ${JSON.stringify(data)}`, async () => {
    globalThis.fetch = async () => Response.json(data);
    try { await assert.rejects(getHealth(new AbortController().signal), /Resposta inválida/); }
    finally { globalThis.fetch = originalFetch; }
  });
}

test('503 remains an explicit service failure', async () => {
  globalThis.fetch = async () => Response.json({ status: 'unavailable' }, { status: 503 });
  try { await assert.rejects(getHealth(new AbortController().signal), (error) => error instanceof ApiError && error.status === 503); }
  finally { globalThis.fetch = originalFetch; }
});

test('transport errors are not converted to successful health', async () => {
  globalThis.fetch = async () => { throw new TypeError('connection failed'); };
  try { await assert.rejects(getHealth(new AbortController().signal), /connection failed/); }
  finally { globalThis.fetch = originalFetch; }
});

test('staff contracts reject missing grants, wrong active flag and invalid strength', () => {
  const staff = { id: 'identifier', name: 'Ana', login_code: 'ana', role: 'WAITER', active: true, permissions: ['VIEW_OPERATION'] };
  assert.deepEqual(decodeStaff(staff), staff);
  assert.throws(() => decodeStaff({ ...staff, active: 'true' }));
  assert.throws(() => decodeStaff({ ...staff, permissions: [1] }));
  assert.throws(() => decodeContext({ staff, auth_strength: 'admin' }));
  assert.deepEqual(decodeRoles([{ id: 'role', name: 'WAITER', permissions: [] }]), [{ id: 'role', name: 'WAITER', permissions: [] }]);
  assert.equal(decodeStaffPage({ count: 1, next: null, previous: null, results: [staff] }).results.length, 1);
  assert.throws(() => decodeStaffPage({ count: -1, results: [] }));
});

test('cookie mutations obtain CSRF and send one request without automatic replay', async () => {
  const calls = [];
  globalThis.fetch = async (path, options) => {
    calls.push([path, options]);
    return path.endsWith('/csrf/') ? Response.json({ csrf_token: 'masked-token' }) : new Response(null, { status: 204 });
  };
  try {
    assert.equal(await request('/api/v1/staff/logout/', 'POST', {}), null);
    assert.equal(calls.length, 2);
    assert.equal(calls[1][1].credentials, 'same-origin');
    assert.equal(calls[1][1].headers['X-CSRFToken'], 'masked-token');
    assert.equal(calls[1][1].body, '{}');
  } finally { globalThis.fetch = originalFetch; }
});

test('rate limit and forbidden responses retain their status', async () => {
  for (const status of [400, 401, 403, 409, 422, 429, 500]) {
    globalThis.fetch = async () => new Response(null, { status });
    try { await assert.rejects(request('/api/v1/staff/me/'), cause => cause instanceof ApiError && cause.status === status); }
    finally { globalThis.fetch = originalFetch; }
  }
  await assert.rejects(request('https://foreign.example/api/v1/'), /Endereço/);
});
