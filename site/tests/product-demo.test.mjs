import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { products, request, resetDemo } from '../src/demo/api.ts';

test('QA catalogue uses actual product validation and honours categories and accent-insensitive search', async () => {
  assert.equal(products.length, 3);
  for (const product of products) {
    assert.equal(product.has_image, true);
    const image = readFileSync(new URL(`../public/assets/catalog/${product.id}.webp`, import.meta.url));
    assert.equal(image.toString('ascii', 0, 4), 'RIFF');
    assert.equal(image.toString('ascii', 8, 12), 'WEBP');
  }
  const categories = await request('/api/v1/public/categories/');
  const category = categories.results.find(item => item.name === 'Bebidas');
  const drinks = await request(`/api/v1/public/menu/?category=${category.id}`);
  assert.ok(drinks.results.length > 0);
  assert.ok(drinks.results.every(product => !product.name.includes('Burger')));
  const result = await request('/api/v1/public/menu/?search=hamburguer');
  assert.ok(result.results.some(product => product.name === 'Hambúrguer Clássico'));
  assert.equal((await request('/api/v1/public/menu/?search=missing-123')).results.length, 0);
  const unpictured = JSON.parse(readFileSync(new URL('../src/data/product-catalog.json', import.meta.url), 'utf8')).products.find(product => !product.has_image);
  await assert.rejects(request(`/api/v1/public/products/${unpictured.id}/`), /indisponível/);
});

test('local quote keeps product selection rules, quantity limits and integer money totals', async () => {
  const product = products.find(product => product.name === 'Hambúrguer Clássico');
  await assert.rejects(request('/api/v1/public/quote/', 'POST', { product_id: product.id, option_ids: [], quantity: 1 }), /Ponto da carne/);
  const point = product.groups.find(group => group.name === 'Ponto da carne').options.find(option => option.name === 'Ao ponto');
  const cheese = product.groups.flatMap(group => group.options).find(option => option.name === 'Queijo');
  const quote = await request('/api/v1/public/quote/', 'POST', { product_id: product.id, option_ids: [point.id, cheese.id], quantity: 2 });
  assert.equal(quote.unit_price, '28.90');
  assert.equal(quote.options.length, 2);
  for (const quantity of [0, 100, 1.5, '2']) await assert.rejects(request('/api/v1/public/quote/', 'POST', { product_id: product.id, option_ids: [point.id], quantity }));
  await assert.rejects(request('/api/v1/public/quote/', 'POST', { product_id: product.id, option_ids: ['unknown'], quantity: 1 }));
});

test('unsupported operations fail closed; demo calls stay in memory and reset clears them', async () => {
  resetDemo();
  await assert.rejects(request('/api/v1/public/orders/', 'POST', {}), /não faz parte/);
  await assert.rejects(request('https://example.com/'), /não faz parte/);
  await assert.rejects(request('/api/v1/public/service-requests/', 'POST', { kind: 'unknown', message: '' }));
  const call = await request('/api/v1/public/service-requests/', 'POST', { kind: 'ATTENDANT', message: 'Exemplo' });
  assert.equal(call.status, 'OPEN');
  assert.equal((await request('/api/v1/public/service-requests/')).count, 1);
  const cancelled = await request(`/api/v1/public/service-requests/${call.id}/cancel/`, 'POST', {});
  assert.equal(cancelled.status, 'CANCELLED');
  assert.equal((await request('/api/v1/public/service-requests/')).count, 0);
  resetDemo();
  assert.equal((await request('/api/v1/public/service-requests/')).count, 0);
});
