import assert from 'node:assert/strict';
import test from 'node:test';
import config from '../vite.config.js';

function local(profile, backend, port) {
  const before = { ...process.env };
  try {
    process.env.VITE_TAPSERVE_ENV = profile;
    process.env.VITE_BACKEND_URL = backend;
    process.env.VITE_FRONTEND_PORT = String(port);
    return config({ mode: profile === 'dev' ? 'development' : 'qa' });
  } finally { process.env = before; }
}

test('DEV and QA proxy HTTP and WebSocket only to their own backend', () => {
  for (const [profile, api, port] of [['dev', 8004, 5177], ['qa', 8003, 5176]]) {
    const server = local(profile, `http://127.0.0.1:${api}`, port).server;
    assert.equal(server.host, '127.0.0.1');
    assert.equal(server.port, port);
    assert.equal(server.strictPort, true);
    assert.equal(server.proxy['/api'].target, `http://127.0.0.1:${api}`);
    assert.equal(server.proxy['/ws'].target, server.proxy['/api'].target);
    assert.equal(server.proxy['/ws'].rewriteWsOrigin, false);
  }
});

test('mixed environment ports or backend credentials fail before serving', () => {
  assert.throws(() => local('dev', 'http://127.0.0.1:8003', 5177), /same environment/);
  assert.throws(() => local('qa', 'http://127.0.0.1:8003', 5177), /same environment/);
  assert.throws(() => local('qa', 'http://user:secret@127.0.0.1:8003', 5176), /without credentials/);
});
