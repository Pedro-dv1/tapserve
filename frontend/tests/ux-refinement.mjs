import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const browser = await chromium.launch({ channel: 'chrome', headless: true, chromiumSandbox: true });
const page = await browser.newPage({ baseURL: process.env.TAPSERVE_QA_URL ?? 'http://127.0.0.1:5175', reducedMotion: 'reduce' });
const errors = []; page.on('pageerror', error => errors.push(error.message));
const output = new URL('../../.local/ux-validation/', import.meta.url); await mkdir(output, { recursive: true });
try {
  // Serve a blank document through Vite, then mount real components without a live account.
  await page.route('**/__ux-test', route => route.fulfill({ contentType: 'text/html', body: '<html lang="pt-BR"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><script type="module" src="/tests/ux-harness.tsx"></script></body></html>' }));
  await page.goto('/__ux-test');
  const modal = page.getByRole('dialog', { name: 'Editar cadastro', exact: true });
  const notice = page.getByRole('dialog', { name: 'Alterações não salvas' });
  const edit = () => page.getByRole('button', { name: 'Editar', exact: true }).click();
  const close = () => modal.getByRole('button', { name: 'Fechar', exact: true }).click();
  await edit(); await close(); await modal.waitFor({ state: 'hidden' });
  await edit(); await modal.getByLabel('Nome', { exact: true }).fill('Modificado'); await close(); await notice.waitFor();
  await notice.getByRole('button', { name: 'Continuar editando' }).click();
  assert.equal(await modal.getByLabel('Nome', { exact: true }).inputValue(), 'Modificado');
  await close(); await notice.getByRole('button', { name: 'Descartar', exact: true }).click();
  await modal.waitFor({ state: 'hidden' }); assert.equal(await page.locator('[data-persisted]').textContent(), 'Original');
  await edit(); await modal.getByLabel('Nome', { exact: true }).fill('Outro'); await modal.getByLabel('Nome', { exact: true }).fill('Original'); await close(); await modal.waitFor({ state: 'hidden' });
  await edit(); await modal.getByLabel('Preço').fill('10'); await close(); await modal.waitFor({ state: 'hidden' });
  await edit(); await modal.getByRole('button', { name: 'Remover opção' }).click(); await modal.getByRole('button', { name: 'Restaurar opção' }).click(); await close(); await modal.waitFor({ state: 'hidden' });
  await edit(); await modal.getByLabel('Imagem').setInputFiles({ name: 'photo.png', mimeType: 'image/png', buffer: Buffer.from('fixture') }); await close(); await notice.waitFor(); await notice.getByRole('button', { name: 'Continuar editando' }).click();
  assert.equal(await modal.getByLabel('Imagem').evaluate(input => input.files[0].name), 'photo.png');
  await modal.getByLabel('Imagem').setInputFiles([]); await close(); await modal.waitFor({ state: 'hidden' });
  await page.getByLabel('Falhar salvamento').check(); await edit(); await modal.getByLabel('Nome', { exact: true }).fill('Preservado'); await modal.getByRole('button', { name: 'Cancelar', exact: true }).click(); await notice.getByRole('button', { name: 'Salvar alterações' }).click();
  await modal.getByRole('alert').waitFor(); assert.equal(await modal.getByLabel('Nome', { exact: true }).inputValue(), 'Preservado');
  assert.equal(await page.locator('[data-writes]').textContent(), '0');
  await notice.getByRole('button', { name: 'Continuar editando' }).click(); await close(); await notice.getByRole('button', { name: 'Descartar', exact: true }).click(); await modal.waitFor({ state: 'hidden' });
  await page.getByLabel('Falhar salvamento').uncheck(); await edit(); await modal.getByLabel('Nome', { exact: true }).fill('Salvo'); await page.keyboard.press('Escape'); await notice.waitFor();
  await notice.getByRole('button', { name: 'Salvar alterações' }).click(); await modal.waitFor({ state: 'hidden' });
  assert.equal(await page.locator('[data-persisted]').textContent(), 'Salvo'); assert.equal(await page.locator('[data-writes]').textContent(), '1');
  console.log('PASS A: unchanged, restored values/numbers/lists, files, continue, discard, Escape, success and failed save.');
  const search = page.getByRole('combobox', { name: 'Buscar produto' }); await search.fill('ham'); await page.getByRole('option').first().waitFor();
  await search.press('ArrowDown'); await search.press('Enter'); assert.equal(await page.locator('[data-chosen]').textContent(), 'Hambúrguer artesanal');
  await search.fill('duplo'); await search.press('Enter'); assert.equal(await page.locator('[data-search]').textContent(), 'duplo');
  await search.fill('inexistente'); await page.getByText('Nenhuma correspondência encontrada.').waitFor(); await search.press('Escape'); assert.equal(await search.getAttribute('aria-expanded'), 'false');
  await search.fill(''); await search.press('Enter'); assert.equal(await page.locator('[data-search]').textContent(), '');
  console.log('PASS B: keyboard suggestions, explicit Enter search, empty results, Escape and clearing.');
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}`);
    const claim = await page.getByRole('button', { name: 'Assumir chamado' }).boundingBox(); const cancel = await page.getByRole('button', { name: 'Cancelar chamado' }).boundingBox();
    assert.ok(Math.abs(claim.height - cancel.height) <= 1); assert.ok(cancel.y >= claim.y + claim.height + 10 || cancel.x >= claim.x + claim.width + 10);
    await edit();
    assert.equal(await modal.evaluate(node => getComputedStyle(node).backgroundColor === getComputedStyle(node.querySelector('header')).backgroundColor), true);
    assert.notEqual(await modal.getByRole('button', { name: 'Fechar', exact: true }).evaluate(node => getComputedStyle(node).backgroundColor), 'rgba(0, 0, 0, 0)');
    await modal.getByLabel('Nome', { exact: true }).fill('Responsivo'); await close(); await notice.waitFor();
    const box = await notice.boundingBox(); assert.ok(box.x >= 0 && box.x + box.width <= width && box.y + box.height <= 900 - 76);
    await page.screenshot({ path: new URL(`pending-${width}.png`, output).pathname.replace(/^\/([A-Za-z]:)/, '$1') });
    await notice.getByRole('button', { name: 'Descartar', exact: true }).click(); await modal.waitFor({ state: 'hidden' });
  }
  await page.getByRole('button', { name: 'Experimentar' }).click(); assert.equal(await page.locator('[data-chosen]').textContent(), 'test');
  assert.deepEqual(errors, []);
  console.log('PASS C/D/H: consistent modal surface, close button, call geometry, compact safe-area prompt and popular product interaction at four widths; no browser errors.');
} finally { await browser.close(); }
