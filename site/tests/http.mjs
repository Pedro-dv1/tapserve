import assert from 'node:assert/strict';
import { writeFile, mkdir } from 'node:fs/promises';
import { routes } from '../src/data/routes.ts';

const base = 'http://127.0.0.1:4321';
const results = [];
for (const route of routes) {
  const response = await fetch(base + route.path);
  assert.equal(response.status, 200, route.path);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(response.headers.get('x-frame-options'), 'DENY');
  const html = await response.text();
  assert.match(html, /data-site="tapserve"/);
  const urls = new Set([...html.matchAll(/(?:src|href|content)="(\/assets\/[^" ]+)"/g)].map(match => match[1]));
  for (const [, set] of html.matchAll(/(?:srcSet|srcset)="([^"]+)"/g)) for (const part of set.split(',')) urls.add(part.trim().split(/\s+/)[0]);
  for (const url of urls) {
    const asset = await fetch(base + url, { method: 'HEAD' });
    assert.equal(asset.status, 200, `${route.path}: ${url}`);
    assert.ok(!asset.headers.get('content-type').includes('text/html'), `${url} must be an asset`);
  }
  results.push({ path: route.path, status: response.status, assets: urls.size });
}
for (const missing of ['/inexistente', '/obrigado', '/cookies', '/termos-assinatura']) {
  const response = await fetch(base + missing);
  assert.equal(response.status, 404);
  const html = await response.text();
  assert.match(html, /Essa página não está no cardápio/);
  assert.match(html, /<title>404 — Página não encontrada \| TapServe<\/title>/);
  assert.match(html, /href="\/">Voltar ao início/);
  results.push({ path: missing, status: response.status });
}
const post = await fetch(base + '/demonstracao', { method: 'POST', body: '{}' });
assert.equal(post.status, 405);
assert.equal(post.headers.get('allow'), 'GET, HEAD');
results.push({ path: '/demonstracao', method: 'POST', status: post.status });
const demo = await fetch(base + '/produto-demo.html');
assert.equal(demo.status, 200);
assert.equal(demo.headers.get('x-frame-options'), 'SAMEORIGIN');
assert.match(await demo.text(), /connect-src 'none'/);
await mkdir(new URL('../test-results/', import.meta.url), { recursive: true });
await writeFile(new URL('../test-results/http.json', import.meta.url), JSON.stringify({ date: new Date().toISOString(), results }, null, 2));
console.log(`PASS: ${routes.length} rotas, imagens/srcset/OG/assets, 4 HTTP404, POST405 e headers de segurança.`);
