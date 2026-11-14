import assert from 'node:assert/strict';
import { chromium, firefox, webkit } from 'playwright';

// Component integration only: every API is intercepted, so no lab data is mutated.
const origin = process.env.TAPSERVE_UI_ORIGIN || 'http://127.0.0.1:5173';
if (!/^http:\/\/127\.0\.0\.1:(5173|5178)$/.test(origin)) throw new Error('Use a reviewed local Vite origin.');
const engine = process.env.TAPSERVE_UI_ENGINE || 'chrome';
const launchers = { chrome: () => chromium.launch({ channel: 'chrome', headless: true, chromiumSandbox: true }), edge: () => chromium.launch({ channel: 'msedge', headless: true, chromiumSandbox: true }), firefox: () => firefox.launch({ headless: true }), webkit: () => webkit.launch({ headless: true }) };
if (!Object.hasOwn(launchers, engine)) throw new Error('Unknown browser engine');
const browser = await launchers[engine]();
const errors = [];
const context = await browser.newContext({ baseURL: origin });
await context.addInitScript(() => {
  window.__qaTransitionStarts = 0;
  if (!document.startViewTransition) return;
  const start = document.startViewTransition.bind(document);
  document.startViewTransition = (...args) => { window.__qaTransitionStarts++; return start(...args); };
});
const policy = { customer_edit_window_minutes: 10, table_takeaway_enabled: true, leftover_packaging_enabled: false, menu_layout: 'EDITORIAL' };
const call = { id: 'qa-call', kind: 'CUTLERY', message: '', status: 'OPEN', point_name: 'Mesa 01', assigned_to_id: null, assignee_name: null, can_customer_cancel: true };
const writes = [];
let concurrentPolicy = { ...policy };
let cancellations = [];
await context.route('**/api/**', async route => {
  const request = route.request(), pathname = new URL(request.url()).pathname;
  const json = (value, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) });
  if (pathname === '/api/v1/csrf/') return json({ csrf_token: 'synthetic-test-only' });
  if (pathname.endsWith('/mfa/')) return json({ enabled: true, recovery_codes_remaining: 4 });
  if (pathname.endsWith('/unit-logo/')) return json({ logo_url: null, max_bytes: 100000 });
  if (pathname.endsWith('/order-policy/')) {
    if (request.method() === 'GET') return json(concurrentPolicy);
    const body = request.postDataJSON(); writes.push(body);
    if (body.expected_window_minutes !== concurrentPolicy.customer_edit_window_minutes) return json({ error: { message: 'O registro mudou. Confira a versão atual.' } }, 409);
    concurrentPolicy = { customer_edit_window_minutes: body.customer_edit_window_minutes, table_takeaway_enabled: body.table_takeaway_enabled, leftover_packaging_enabled: body.leftover_packaging_enabled, menu_layout: body.menu_layout };
    return json(concurrentPolicy);
  }
  if (pathname.endsWith('/cancel/')) { cancellations.push(request.postDataJSON()); return json({ ...call, status: 'CANCELLED', can_customer_cancel: false }); }
  if (pathname.endsWith('/service-requests/')) return json({ count: cancellations.length ? 0 : 1, next: null, previous: null, results: cancellations.length ? [] : [call] });
  throw new Error(`Unexpected API request: ${pathname}`);
});
await context.route('**/__ui-regression__?*', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="pt-BR"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div><script type="module" src="/tests/ui-harness.tsx"></script></body></html>' }));
const page = await context.newPage();
page.on('pageerror', error => {
  errors.push(error.message);
  console.error('UI_PAGEERROR', JSON.stringify({ url: page.url(), message: error.message, stack: error.stack, cause: String(error.cause) }));
});
page.setDefaultTimeout(10000);
const open = name => page.goto(`/__ui-regression__?case=${name}`);
const settle = () => page.waitForFunction(() => !CSS.supports('selector(:active-view-transition)') || !document.documentElement.matches(':active-view-transition'));
const focused = locator => locator.evaluate(node => node === document.activeElement);
try {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await open('pagination');
  const released = page.getByRole('navigation', { name: 'Páginas: Contraste', exact: true }).getByRole('button', { name: 'Próxima', exact: true });
  assert(await released.isDisabled());
  await released.evaluate(node => {
    getComputedStyle(node).opacity;
    const observer = new MutationObserver(() => {
      if (node.disabled) return;
      const style = getComputedStyle(node);
      node.dataset.releasedContrast = JSON.stringify({ disabled: node.disabled, opacity: Number(style.opacity), color: style.color, background: style.backgroundColor });
      observer.disconnect();
    });
    observer.observe(node, { attributes: true, attributeFilter: ['disabled'] });
  });
  await page.getByRole('button', { name: 'Liberar controles', exact: true }).click();
  const release = JSON.parse(await released.getAttribute('data-released-contrast'));
  assert.equal(release.disabled, false);
  const rgb = color => color.match(/[\d.]+/g).slice(0, 3).map(Number);
  const foreground = rgb(release.color), background = rgb(release.background);
  const luminance = values => values.map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
  const painted = foreground.map((v, i) => v * release.opacity + background[i] * (1 - release.opacity));
  const ratio = (luminance(background) + .05) / (luminance(painted) + .05);
  assert(ratio >= 4.5, `SQA-BUG-007 enabled control contrast: ${JSON.stringify({ ...release, ratio })}`);
  console.log('PASS SQA-BUG-007: enabled Pagination has readable contrast immediately after busy clears');
  await open('search-label');
  const searchButton = page.getByRole('button', { name: /Filtrar opções/ });
  const visibleSearch = (await searchButton.innerText()).trim().toLocaleLowerCase('pt-BR');
  const accessibleSearch = (await searchButton.getAttribute('aria-label')).toLocaleLowerCase('pt-BR');
  assert(visibleSearch && accessibleSearch.includes(visibleSearch), `SQA-BUG-008 visible label ${visibleSearch} absent from accessible name ${accessibleSearch}`);
  console.log('PASS SQA-BUG-008: SearchCombobox accessible name includes its visible label');
  await open('account');
  for (const close of ['Escape', 'button']) {
    const profile = page.getByRole('button', { name: /^Perfil de / });
    await profile.click(); await page.getByRole('button', { name: 'Segurança da conta', exact: true }).click();
    const dialog = page.getByRole('dialog'); await dialog.getByText(/Verificação em duas etapas ativa/).waitFor();
    for (const key of ['Tab', 'Shift+Tab']) { await page.keyboard.press(key); assert(await dialog.evaluate(node => node.contains(document.activeElement))); }
    if (close === 'Escape') await page.keyboard.press('Escape'); else await dialog.getByRole('button', { name: 'Fechar', exact: true }).click();
    await dialog.waitFor({ state: 'hidden' }); assert(await focused(profile));
    await page.keyboard.press('Tab'); assert(await focused(page.getByRole('button', { name: 'Próximo controle', exact: true })));
    await page.keyboard.press('Shift+Tab'); assert(await focused(profile));
  }
  console.log('PASS SQA-BUG-001: account focus, Tab, Shift+Tab, Escape and close button');
  await open('detached'); await page.getByRole('button', { name: 'Perfil removível' }).click(); await page.getByRole('button', { name: 'Abrir', exact: true }).click();
  await page.getByRole('dialog').waitFor(); await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({ state: 'hidden' }); assert(await focused(page.getByRole('button', { name: 'Perfil removível' })));
  await open('policy'); await page.getByRole('button', { name: 'Editar configuração', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Janela de correções em minutos').fill('30'); await dialog.getByLabel('Motivo', { exact: true }).fill('Rascunho preservado');
  concurrentPolicy.customer_edit_window_minutes = 20;
  await dialog.getByRole('button', { name: 'Salvar alterações' }).click();
  await dialog.getByRole('alert').waitFor(); assert(await focused(dialog.getByRole('alert')));
  assert.equal(await dialog.getByLabel('Janela de correções em minutos').inputValue(), '30');
  assert.equal(await dialog.getByLabel('Motivo', { exact: true }).inputValue(), 'Rascunho preservado');
  assert.equal(writes[0].expected_window_minutes, 10);
  assert(await dialog.getByRole('button', { name: 'Salvar alterações' }).isDisabled());
  await dialog.getByRole('button', { name: 'Conferir configuração atual' }).click(); await dialog.getByText(/Configuração atual: 20 minutos/).waitFor();
  await dialog.getByRole('button', { name: 'Usar esta versão como referência e manter rascunho' }).click();
  assert.equal(await dialog.getByLabel('Janela de correções em minutos').inputValue(), '30');
  await dialog.getByRole('button', { name: 'Salvar alterações' }).click(); await dialog.waitFor({ state: 'hidden' });
  assert.equal(writes[1].expected_window_minutes, 20); assert.equal(writes[1].customer_edit_window_minutes, 30); assert.notEqual(writes[1].idempotency_key, writes[0].idempotency_key);
  console.log('PASS SQA-BUG-003: conflict in dialog, focus, preserved draft, explicit review and save');
  await open('kds');
  for (const width of [320, 390, 768, 1366]) {
    await page.setViewportSize({ width, height: 800 });
    await page.getByRole('button', { name: 'Recusar', exact: true }).click();
    const dialog = page.getByRole('dialog'); await dialog.waitFor();
    const heading = await dialog.getByRole('heading', { level: 2 }).boundingBox(); assert(heading.width > 120);
    const back = dialog.getByRole('button', { name: 'Voltar', exact: true }); await back.scrollIntoViewIfNeeded();
    assert(await back.evaluate(node => { const r = node.getBoundingClientRect(); return node.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)); }));
    await back.click(); await dialog.waitFor({ state: 'hidden' });
    await page.getByRole('button', { name: 'Recusar', exact: true }).click(); await dialog.waitFor(); await page.keyboard.press('Tab'); await page.keyboard.press('Shift+Tab'); await page.keyboard.press('Escape'); await dialog.waitFor({ state: 'hidden' });
  }
  console.log('PASS SQA-BUG-004: long name, four viewports, mouse hit-testing, scrolling and keyboard');
  await open('calls'); await page.getByRole('button', { name: 'Cancelar chamado', exact: true }).click();
  await page.getByRole('dialog').getByLabel('Motivo (opcional)').fill('Talheres recebidos');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancelar chamado', exact: true }).click();
  await page.getByRole('dialog').waitFor({ state: 'hidden' }); assert.equal(cancellations[0].reason, 'Talheres recebidos');
  console.log('PASS SQA-BUG-006: actual component sends optional reason');
  for (const reducedMotion of ['no-preference', 'reduce']) {
    await page.emulateMedia({ reducedMotion }); await open('transition');
    for (let i = 0; i < 8; i++) {
      const name = i % 2 === 0 ? 'Carrinho' : 'Cardápio';
      // Observe before clicking: a completed transition cannot be observed by a later poll.
      const active = reducedMotion === 'no-preference' && await page.evaluate(() => CSS.supports('selector(:active-view-transition)'))
        ? page.waitForFunction(() => document.documentElement.matches(':active-view-transition')) : null;
      await page.getByRole('button', { name, exact: true }).click();
      if (active) await active;
      await page.setViewportSize({ width: i % 2 === 0 ? 390 : 768, height: 800 });
      await page.getByRole('heading', { name, exact: true }).waitFor(); await settle();
    }
    const starts = await page.evaluate(() => window.__qaTransitionStarts);
    if (reducedMotion === 'reduce') { assert.equal(starts, 0, 'SQA-BUG-009: reduced motion still starts native transitions'); console.log('PASS SQA-BUG-009: reduced motion navigates without native transitions'); }
    else assert(starts >= 8, 'Positive control did not start all navigation transitions');
  }
  assert.deepEqual(errors, []);
  console.log(`PASS SQA-BUG-002: viewport changes, navigation, reduced motion; ${engine} ${browser.version()}, zero pageerrors`);
} finally { await browser.close(); }
