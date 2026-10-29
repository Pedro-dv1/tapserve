import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({ channel: 'chrome', headless: true, chromiumSandbox: true });
const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
try {
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await page.getByText('Serviço e banco de dados conectados.').waitFor();
  assert.equal(await page.title(), 'TapServe');
  assert.equal(await page.locator('html').getAttribute('lang'), 'pt-BR');
  assert.equal(await page.locator('link[rel="icon"]').getAttribute('href'), '/brand/TapServe-icon.svg');
  assert.equal(await page.getByRole('img', { name: 'TapServe' }).evaluate((image) => image.naturalWidth > 0), true);
  for (const width of [320, 360, 375, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 800 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `overflow at ${width}px`);
  }
  await page.keyboard.press('Tab');
  assert.equal(await page.getByRole('button', { name: 'Verificar novamente' }).evaluate((button) => button === document.activeElement), true);
  await page.keyboard.press('Enter');
  await page.getByText('Serviço e banco de dados conectados.').waitFor();
  // A real browser transport failure must leave a persistent error and a retry action.
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Verificar novamente' }).click();
  await page.getByRole('alert').waitFor();
  assert.match(await page.getByRole('alert').innerText(), /sem conexão/);
  await context.setOffline(false);
  await page.getByRole('button', { name: 'Verificar novamente' }).click();
  await page.getByText('Serviço e banco de dados conectados.').waitFor();
  assert.deepEqual(errors, []);
  console.log('PASS: live API/PG proxy, brand/favicon, six viewport widths, keyboard, offline/retry; Chrome headless.');
} finally {
  await context.close();
  await browser.close();
}
