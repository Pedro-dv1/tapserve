import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';

// Real local/QA APIs only. No mutation of orders, catalog, access or staff records.
const browser = await chromium.launch({ channel: 'chrome', headless: true, chromiumSandbox: true });
const context = await browser.newContext({ baseURL: process.env.TAPSERVE_QA_URL ?? 'http://127.0.0.1:5173', reducedMotion: 'reduce' });
try {
  const required = ['COMPANY', 'UNIT', 'USER', 'PASSWORD'];
  for (const key of required) assert.ok(process.env[`TAPSERVE_QA_${key}`], `Missing TAPSERVE_QA_${key}`);
  const output = new URL('../../.local/redesign-after/', import.meta.url);
  await mkdir(output, { recursive: true });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.name));
  await page.goto('/staff/login');
  await page.getByRole('button', { name: 'Responsável: entrar com senha' }).click();
  await page.getByLabel('Código da empresa', { exact: true }).fill(process.env.TAPSERVE_QA_COMPANY);
  await page.getByLabel('Código da unidade', { exact: true }).fill(process.env.TAPSERVE_QA_UNIT);
  await page.getByLabel('Usuário', { exact: true }).fill(process.env.TAPSERVE_QA_USER);
  await page.getByLabel('Senha', { exact: true }).fill(process.env.TAPSERVE_QA_PASSWORD);
  await Promise.all([page.waitForURL(/\/staff(?:\/production|\/operation)?$/), page.getByRole('button', { name: 'Entrar', exact: true }).click()]);
  const routes = [
    ['operation', '/staff/operation', 'Mesas'],
    ['orders', '/staff/orders', 'Pedidos'],
    ['calls', '/staff/calls', 'Chamados'],
    ['more', '/staff/more', 'Mais'],
    ['production', '/staff/production', 'Produção'],
    ['staff', '/staff', 'Funcionários da unidade'],
    ['points', '/staff/points', 'Pontos de atendimento'],
    ['menu', '/staff/menu', 'Cardápio da unidade'],
    ['settings', '/staff/settings', 'Alterações de pedidos'],
  ];
  for (const width of [320, 375, 390, 430, 768, 1024, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [name, route, heading] of routes) {
      await page.goto(route);
      await page.getByRole('heading', { level: 1, name: heading, exact: true }).waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll('.content-skeleton')].every(node => node.getClientRects().length === 0));
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow ${name} ${width}`);
      assert.equal(await page.locator('.staff-navigation a[aria-current="page"]:visible').count(), width >= 768 ? 1 : 0);
      if (width < 768) {
        assert.deepEqual(await page.locator('.staff-mobile-navigation nav a span').allTextContents(), ['Mesas', 'Pedidos', 'Chamados', 'Mais']);
      }

      await page.screenshot({ path: new URL(`${name}-${width}.png`, output).pathname.replace(/^\/([A-Za-z]:)/, '$1'), fullPage: true });
      const create = { staff: 'Cadastrar funcionário', points: 'Cadastrar ponto', menu: '+ Cadastrar produto' }[name];
      if (create) {
        if (name === 'menu') { const selection = page.locator('[name="context_menu"]'); await selection.locator('option').nth(1).waitFor(); if (!await selection.inputValue()) await selection.selectOption({ index: 1 }); }
        await page.getByRole('button', { name: create, exact: true }).click();
        assert.equal(await page.locator('dialog[open]').evaluate(node => node.contains(document.activeElement)), true);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `editor overflow ${name} ${width}`);
        await page.getByRole('button', { name: 'Fechar', exact: true }).click();
      }
      assert.equal(await page.getByRole('alert').count(), 0, `API/permission failure ${name}`);
    }
  }
  await page.goto('/staff/menu');
  for (const name of ['Produtos', 'Categorias', 'Setores de produção', 'Cardápios', 'Grupos de opções', 'Opções']) {
    await page.getByRole('button', { name, exact: true }).click();
    await page.waitForFunction(() => [...document.querySelectorAll('.content-skeleton')].every(node => node.getClientRects().length === 0));
    assert.equal(await page.getByRole('alert').count(), 0);
  }
  await page.goto('/staff/operation');
  await page.getByRole('heading', { level: 1, name: 'Mesas', exact: true }).waitFor();
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Atualizar mesas', exact: true }).click();
  await page.getByRole('alert').first().waitFor({ timeout: 20_000 });
  await context.setOffline(false);
  await page.getByRole('button', { name: 'Atualizar mesas', exact: true }).click();
  await page.getByRole('alert').first().waitFor({ state: 'hidden' });
  await page.getByRole('button', { name: /^Perfil de / }).click();
  await page.locator('#staff-profile-popover').getByRole('button', { name: 'Sair', exact: true }).click();
  await page.waitForURL(/\/staff\/login$/);
  assert.equal((await context.request.get('/api/v1/staff/me/')).status(), 401);
  assert.deepEqual(errors, []);
  console.log('PASS: nine unit routes, nine widths, four destinations, real logout, editor/modal focus, catalog tabs, offline/retry. Screenshots are private .local artifacts.');
} finally {
  await context.close();
  await browser.close();
}
