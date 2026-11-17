import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

for (const [path, title, count] of [['privacidade', 'Política de Privacidade', 18], ['termos', 'Termos de Uso', 22]]) {
  test(`${path}: complete public document, section navigation and honest publication status`, () => {
    const html = readFileSync(new URL(`../dist/${path}/index.html`, import.meta.url), 'utf8');
    assert.match(html, new RegExp(`<h1>${title}</h1>`));
    assert.equal((html.match(/<section\b/g) ?? []).length, count + 1);
    assert.match(html, /<time dateTime="2026-11-14"/);
    assert.match(html, /PREENCHER ANTES DA PUBLICAÇÃO: razão social/);
    assert.match(html, /PREENCHER ANTES DA PUBLICAÇÃO: CNPJ ou CPF/);
    assert.match(html, /PREENCHER ANTES DA PUBLICAÇÃO: endereço completo/);
    assert.match(html, /Vigência: \[PREENCHER ANTES DA PUBLICAÇÃO\]/);
    assert.match(html, /aria-current="page"/);
    assert.doesNotMatch(html, /Este documento ainda está em revisão|<form\b|type="checkbox"/);
    const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
    assert.equal(new Set(ids).size, ids.length, 'unique anchors');
    for (const [, fragment] of html.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.includes(fragment), `${path}: #${fragment}`);
    for (const [, id] of html.matchAll(/aria-labelledby="([^"]+)"/g)) assert.ok(ids.includes(id), `${path}: ${id}`);
    for (const destination of ['/privacidade', '/termos']) assert.ok(html.includes(`href="${destination}"`));
    for (const host of ['www2.camara.leg.br', 'www.gov.br/anpd']) assert.ok(html.includes(host));
    assert.match(html, /mailto:pedrocarrega5@gmail.com/);
    for (const [, attributes] of html.matchAll(/<a\b([^>]*target="_blank"[^>]*)>/g)) assert.match(attributes, /rel="noopener noreferrer"/);
  });
}
