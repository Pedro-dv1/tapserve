import assert from 'node:assert/strict';
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { test } from 'node:test';
import { routes } from '../src/data/routes.ts';
import { contact } from '../src/config/contact.ts';

const root = new URL('../', import.meta.url);
test('13 prerendered routes, semantic content, local images/links, legal guards and no contact forms', () => {
  assert.equal(routes.length, 13);
  for (const route of routes) {
    const html = readFileSync(new URL(`dist${route.path === '/' ? '/' : `${route.path}/`}index.html`, root), 'utf8');
    assert.equal((html.match(/<h1\b/g) ?? []).length, 1, route.path);
    assert.match(html, /<meta name="description"/); assert.match(html, /noindex,nofollow/);
    assert.doesNotMatch(html, /<form\b|\/obrigado|rel="canonical"/i);
    assert.match(html, /connect-src 'none'/);
    for (const [, url] of html.matchAll(/(?:src|href)="(\/[^"#?]*)/g)) {
      if (url === '/') continue;
      const local = new URL(`dist${url.startsWith('/assets/') || url.endsWith('.html') ? url : `${url}/index.html`}`, root);
      assert.ok(existsSync(local), `${route.path}: ${url}`);
    }
    if (['/privacidade', '/termos', '/cancelamento'].includes(route.path)) {
      assert.match(html, /em revisão/); assert.doesNotMatch(html, /PENDENTE DE CONFIRMAÇÃO/);
    }
    if (['/contato', '/suporte'].includes(route.path)) {
      assert.equal((html.match(/href="https:\/\/wa\.me\//g) ?? []).length, 1);
      assert.equal((html.match(/href="mailto:/g) ?? []).length, 1);
      const text = html.replace(/<[^>]*>/g, '');
      assert.doesNotMatch(text, /5517997585762|pedrocarrega5@gmail/);
    }
  }
  assert.ok(existsSync(new URL('dist/404.html', root)));
  assert.ok(!existsSync(new URL('dist/cookies', root)));
  assert.ok(!existsSync(new URL('dist/termos-assinatura', root)));
  assert.match(readFileSync(new URL('dist/robots.txt', root), 'utf8'), /Disallow: \//);
});
test('contact destinations and contextual text are exact and contain no visitor data', () => {
  assert.equal(contact.email, 'mailto:pedrocarrega5@gmail.com');
  for (const key of ['commercial', 'support']) { const url = new URL(contact[key]); assert.equal(url.origin + url.pathname, 'https://wa.me/5517997585762'); assert.equal([...url.searchParams].length, 1); }
  assert.match(new URL(contact.commercial).searchParams.get('text'), /solicitar uma demonstração/);
  assert.match(new URL(contact.support).searchParams.get('text'), /preciso de ajuda/);
});
test('site code has no product endpoints, network writes, trackers or persistent storage', () => {
  const files = readdirSync(new URL('src/', root), { recursive: true }).filter(file => /\.(tsx?|css)$/.test(file));
  for (const file of files) {
    const source = readFileSync(new URL(`src/${file.replaceAll('\\', '/')}`, root), 'utf8');
    assert.doesNotMatch(source, /\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(|localStorage|sessionStorage|document\.cookie|dangerouslySetInnerHTML/);
    if (!file.replaceAll('\\', '/').startsWith('demo/')) assert.doesNotMatch(source, /\/api\/|<form\b/);
  }
});
test('public pages contain NFC communication and no removed presentation or pricing links', () => {
  assert.ok(!routes.some(route => route.path === '/planos' || route.path === '/nfc-e-qr-code'));
  for (const route of routes) {
    const html = readFileSync(new URL(`dist${route.path === '/' ? '/' : `${route.path}/`}index.html`, root), 'utf8');
    const visible = html.replace(/<[^>]*>/g, ' ');
    assert.doesNotMatch(visible, /\bQR\b|escanei|Desativar animações|\b0\d\s*\/\s*\d/iu, route.path);
    assert.doesNotMatch(html, /eyebrow|segment-number|hotspot|gallery-options|pricing-card|href="\/planos"/i, route.path);
  }
  assert.ok(!existsSync(new URL('dist/planos/index.html', root)));
  assert.ok(!existsSync(new URL('dist/nfc-e-qr-code/index.html', root)));
  assert.match(readFileSync(new URL('dist/produto-demo.html', root), 'utf8'), /connect-src 'none'/);
});

test('final presentation has the desktop photograph, removed blocks, custom 404 and real-loading fallback', () => {
  const html = path => readFileSync(new URL(`dist/${path}`, root), 'utf8');
  assert.match(html('index.html'), /class="photo faq-photo"/);
  assert.doesNotMatch(html('index.html'), /Demonstração interativa\. Produtos e valores de exemplo/);
  assert.doesNotMatch(html('demonstracao/index.html'), /demo-notice/);
  assert.doesNotMatch(html('funcionalidades/index.html'), /Acesso para cada responsabilidade/);
  assert.match(html('duvidas/index.html'), /faq-page-intro/);
  assert.match(html('404.html'), /Essa página não está no cardápio\./);
  assert.match(html('404.html'), /404 — Página não encontrada/);
  assert.match(html('produto-demo.html'), /B03-logo-symbol\.svg/);
  assert.match(html('produto-demo.html'), /brand-loading-help/);
  assert.match(html('produto-demo.html'), /assets\/brand\/loader\.js/);
  assert.match(html('assets/brand/loader.css'), /prefers-reduced-motion/);
});
