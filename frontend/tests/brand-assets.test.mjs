import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { test } from 'node:test';

test('official brand URLs resolve to static assets independently of the page route', () => {
  const frontend = new URL('../', import.meta.url);
  const sources = readdirSync(new URL('src/', frontend), { recursive: true })
    .filter(file => /\.(tsx?|css)$/.test(file))
    .map(file => readFileSync(new URL(`src/${file.replaceAll('\\', '/')}`, frontend), 'utf8'));
  sources.push(readFileSync(new URL('index.html', frontend), 'utf8'));
  const paths = sources.flatMap(source => [...source.matchAll(/(?:src|href)="([^"]*TapServe[^"\s]*\.(?:png|svg))"/g)].map(match => match[1]));
  assert.ok(paths.length > 10);
  for (const path of paths) {
    assert.match(path, /^\/brand\/TapServe-(?:logo-wordmark\.png|icon\.svg)$/);
    const asset = readFileSync(new URL(`public${path}`, frontend));
    if (path.endsWith('.png')) assert.equal(asset.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    else assert.match(asset.toString('utf8'), /<svg\b/);
    for (const route of ['/mesa/cardapio', '/admin/production', '/staff/operation', '/platform']) {
      assert.equal(new URL(path, `http://localhost:5173${route}`).pathname, path);
    }
  }
});
