import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

// Browser interactions use controlled API responses; real authorization/storage are covered by pytest.
const browser = await chromium.launch({ channel: 'chrome', headless: true, chromiumSandbox: true });
const context = await browser.newContext({ baseURL: process.env.TAPSERVE_TEST_ORIGIN ?? 'http://127.0.0.1:5173' });
const id = crypto.randomUUID(), person = crypto.randomUUID();
const logo = await readFile(new URL('../public/brand/TapServe-logo-wordmark.png', import.meta.url));
const output = new URL('../../.local/customer-refinement/', import.meta.url);
await mkdir(output, { recursive: true });
const point = { id, name: 'Mesa 07 de demonstração', type: 'TABLE', active: true, access_enabled: true, token_version: 1, nfc_enabled: true, qr_enabled: true, block_new_devices: false };
const publicContext = { device_id: crypto.randomUUID(), point, company_name: 'Restaurante', unit_name: 'Centro', expires_at: '2099-01-01T00:00:00Z', unit_timezone: 'America/Sao_Paulo', unit_logo_url: '/api/v1/public/unit-logo/image/?v=0123456789abcdef' };
const session = { id: crypto.randomUUID(), version: 1, status: 'OPEN', points: [{ id, name: point.name }], participants: [{ id: person, display_name: 'Ana', active: true }] };
const productId = crypto.randomUUID(), itemId = crypto.randomUUID();
const orderItem = { id: itemId, product_id: productId, version: 1, snapshot: { name: 'Lanche', options: [] }, quantity: 2, notes: 'Sem sal', status: 'NEW', unit_price: '12.35', line_total: '24.70', can_customer_change: true, editable_until: '2099-01-01T00:00:00Z', participant_id: person, participant_name: 'Ana', delivered_by_id: null };
const batches = [{ id: crypto.randomUUID(), created_at: new Date().toISOString(), notes: '', items: [orderItem] }];
let itemWrites = [], mutationGate = null;
let calls = [], posts = [], deleteCount = 0, failDelete = false, failCall = false, gate = null, contextStatus = 200, logoUrl = null, logoWrites = 0;
const receipts = new Map();
await context.route('**/api/v1/**', async route => {
  const req = route.request(), path = new URL(req.url()).pathname, method = req.method();
  const reply = (json, status = 200) => route.fulfill({ status, json });
  const failure = (message, status) => reply({ error: { message } }, status);
  if (path.endsWith('/csrf/')) return reply({ csrf_token: 'browser-test' });
  if (path === '/api/v1/public/context/' || path === '/api/v1/public/access/') return contextStatus === 200 ? reply(publicContext) : failure('Indisponível', contextStatus);
  if (path.includes('/unit-logo/image/')) return route.fulfill({ contentType: 'image/png', body: logo });
  if (path === '/api/v1/public/session/') return reply({ session });
  if (path === '/api/v1/public/orders/') return reply({ results: batches, next: null, previous: null });
  if (path === '/api/v1/public/menu/' || path === '/api/v1/public/categories/') return reply({ results: [], next: null, previous: null });
  if (path === `/api/v1/public/products/${productId}/`) return reply({ id: productId, name: 'Lanche', description: '', base_price: '12.35', has_image: false, groups: [] });
  if (path === `/api/v1/public/items/${itemId}/` || path === `/api/v1/public/items/${itemId}/cancel/`) {
    const body = req.postDataJSON(); itemWrites.push(body);
    if (mutationGate) await mutationGate;
    if (body.expected_version !== orderItem.version) return failure('O pedido mudou.', 409);
    if (method === 'PATCH') Object.assign(orderItem, { quantity: body.quantity, notes: body.notes, participant_id: body.participant_id, participant_name: session.participants.find(person => person.id === body.participant_id)?.display_name ?? null, line_total: (12.35 * body.quantity).toFixed(2) });
    else Object.assign(orderItem, { status: 'CANCELLED', can_customer_change: false });
    orderItem.version++; return reply(orderItem);
  }
  if (path === '/api/v1/public/service-requests/' && method === 'GET') return reply({ results: calls, next: null, previous: null });
  if (path === '/api/v1/public/service-requests/' && method === 'POST') {
    const data = req.postDataJSON(); posts.push(data);
    if (failCall) { failCall = false; return failure('Indisponível', 503); }
    if (gate) await gate;
    if (receipts.has(data.idempotency_key)) return reply(receipts.get(data.idempotency_key), 201);
    if (calls.some(call => call.kind === data.kind)) return failure('Já existe um chamado deste tipo aguardando atendimento.', 409);
    const call = { ...data, id: crypto.randomUUID(), message: data.message ?? '', point_name: point.name, status: 'OPEN', assigned_to_id: null, assignee_name: null, can_customer_cancel: data.kind !== 'CHECK' };
    calls.push(call); receipts.set(data.idempotency_key, call);
    if (data.kind === 'CHECK') session.status = 'CHECK_REQUESTED';
    return reply(call, 201);
  }
  if (path.startsWith('/api/v1/public/service-request-receipts/')) {
    const call = receipts.get(path.split('/').at(-2));
    return call ? reply(call) : failure('Não localizado', 404);
  }
  if (path.startsWith('/api/v1/public/service-requests/') && path.endsWith('/cancel/')) {
    const call = calls.find(call => path.includes(call.id)); calls = calls.filter(value => value !== call);
    return reply({ ...call, status: 'CANCELLED', can_customer_cancel: false });
  }
  if (path === `/api/v1/public/session/participants/${person}/` && method === 'DELETE') {
    deleteCount++;
    if (failDelete) { failDelete = false; return failure('Este participante possui pedidos confirmados e precisa permanecer no histórico.', 409); }
    session.participants = []; return route.fulfill({ status: 204 });
  }
  if (path === '/api/v1/staff/me/') return reply({ staff: { id, name: 'Administrador', login_code: 'admin', role: 'ADMIN', active: true, permissions: ['MANAGE_SETTINGS'] }, auth_strength: 'password', company_name: 'Restaurante', unit_id: id, unit_name: 'Centro' });
  if (path === '/api/v1/admin/order-policy/') return reply({ customer_edit_window_minutes: 3 });
  if (path === '/api/v1/admin/unit-logo/') {
    if (method !== 'GET') { logoWrites++; logoUrl = method === 'DELETE' ? null : '/api/v1/admin/unit-logo/image/?v=0123456789abcdef'; }
    return reply({ logo_url: logoUrl, max_bytes: 2097152 });
  }
  return failure('Não encontrado', 404);
});
try {
  const page = await context.newPage(), errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', async dialog => { errors.push(`Native dialog: ${dialog.type()}`); await dialog.dismiss(); });
  await page.goto('/customer/nao-existe');
  await page.getByRole('heading', { name: 'Página não encontrada' }).waitFor();
  assert.equal(await page.getByRole('link', { name: 'Voltar ao início' }).getAttribute('href'), '/customer');
  await page.goto('/a/browser-test');
  await page.locator('.customer-entrance').waitFor();
  assert.equal(await page.locator('.customer-entrance').evaluate(el => getComputedStyle(el).animationDuration), '1.8s');
  assert.equal(await page.locator('.content-skeleton:visible').count(), 0);
  await page.locator('.customer-entrance').waitFor({ state: 'detached' });
  await page.getByRole('heading', { name: 'Boas-vindas à mesa.' }).waitFor();
  assert.equal(new URL(page.url()).pathname, '/customer');
  assert.equal(await page.locator('.table-indicator').innerText(), 'Mesa 07');
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 850 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${width}px overflow`);
    await page.screenshot({ path: new URL(`home-${width}.png`, output).pathname.replace(/^\/(?=[A-Z]:)/i, ''), fullPage: true });
  }
  assert.equal(await page.locator('.establishment-logo').evaluate(img => img.naturalWidth > 0 && getComputedStyle(img).objectFit === 'contain'), true);
  const call = page.getByRole('button', { name: 'Chamar garçom', exact: true });
  await call.click();
  const modal = page.getByRole('dialog', { name: 'Chamar atendimento' });
  await modal.waitFor();
  assert.equal(await modal.locator('select option').count(), 5);
  assert.equal(await modal.getByRole('option', { name: 'Limpeza da mesa', exact: true }).count(), 1);
  assert.equal(await page.evaluate(() => Boolean(document.activeElement.closest('dialog'))), true);
  await page.keyboard.press('Escape');
  assert.equal(await call.evaluate(el => el === document.activeElement), true);
  assert.equal(posts.length, 0);
  await call.click(); failCall = true;
  await modal.getByRole('button', { name: 'Chamar atendente', exact: true }).click();
  await modal.getByText('A confirmação está pendente.', { exact: false }).waitFor();
  const retryKey = posts[0].idempotency_key;
  await modal.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.getByRole('navigation', { name: 'Atendimento' }).getByRole('button', { name: 'Mesa', exact: true }).click();
  assert.equal(await page.getByRole('button', { name: 'Voltar', exact: true }).count(), 0);
  await page.getByRole('button', { name: 'Chamar atendimento', exact: true }).click();
  await modal.getByRole('button', { name: 'Repetir o mesmo chamado' }).waitFor();
  let release; gate = new Promise(resolve => { release = resolve; });
  await modal.getByRole('button', { name: 'Repetir o mesmo chamado' }).click();
  await modal.getByText('Estamos processando sua solicitação.').waitFor();
  assert.equal(await modal.getByRole('button', { name: 'Enviando…' }).isDisabled(), true);
  release(); gate = null;
  await modal.waitFor({ state: 'hidden' });
  assert.equal(posts[1].idempotency_key, retryKey);
  await page.getByRole('dialog', { name: 'Atendimento solicitado', exact: true }).getByRole('button', { name: 'Entendido' }).click();
  await page.getByRole('navigation', { name: 'Atendimento' }).getByRole('button', { name: 'Início' }).click();
  assert.equal(await page.getByText('Atendimento solicitado. Um membro da equipe foi notificado.').count(), 0);
  assert.equal(await page.locator('.customer-entrance').count(), 0);
  await call.click();
  assert.equal(await modal.getByRole('button', { name: 'Chamar atendente', exact: true }).isDisabled(), true);
  await modal.getByLabel('Solicitação', { exact: true }).selectOption('CUTLERY');
  assert.equal(await modal.getByRole('button', { name: 'Chamar atendente', exact: true }).isEnabled(), true);
  await modal.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.getByRole('button', { name: 'Pedir a conta', exact: true }).click();
  await page.getByRole('dialog', { name: 'Conta solicitada', exact: true }).getByRole('button', { name: 'Entendido' }).click();
  assert.equal(await page.getByText('Conta solicitada. Nossa equipe foi notificada e está preparando seu atendimento.').count(), 0);
  await page.reload();
  await page.getByRole('heading', { name: 'Boas-vindas à mesa.' }).waitFor();
  assert.equal(await page.locator('dialog:visible').count(), 0);
  await page.getByRole('button', { name: 'Pedir a conta', exact: true }).click();
  await page.getByRole('dialog', { name: 'Conta já solicitada', exact: true }).getByRole('button', { name: 'Entendido' }).click();
  assert.equal(posts.filter(data => data.kind === 'CHECK').length, 1);
  await page.locator('.customer-entrance').waitFor({ state: 'detached' });
  await page.getByRole('navigation', { name: 'Atendimento' }).getByRole('button', { name: 'Mesa', exact: true }).click();
  await page.getByRole('button', { name: 'Remover Ana', exact: true }).click();
  const removal = page.getByRole('dialog', { name: 'Remover participante?' });
  await removal.getByRole('button', { name: 'Cancelar', exact: true }).click();
  assert.equal(deleteCount, 0);
  await page.getByRole('button', { name: 'Remover Ana', exact: true }).click(); failDelete = true;
  await removal.getByRole('button', { name: 'Remover participante', exact: true }).click();
  await removal.getByRole('alert').waitFor();
  assert.equal(await removal.isVisible(), true);
  await removal.getByRole('button', { name: 'Remover participante', exact: true }).click();
  await removal.waitFor({ state: 'hidden' });
  assert.equal(await page.getByRole('button', { name: 'Remover Ana', exact: true }).count(), 0);
  assert.equal(deleteCount, 2);
  await page.reload(); await page.getByRole('heading', { name: 'Mesa', exact: true }).waitFor();
  const maria = crypto.randomUUID();
  session.participants = [{ id: maria, display_name: 'Maria', active: true }];
  await page.goto('/customer/orders');
  await page.getByText('Detalhes do item', { exact: true }).click();
  await page.getByRole('button', { name: 'Alterar item', exact: true }).click();
  const editor = page.getByRole('dialog', { name: 'Alterar item', exact: true });
  await editor.getByRole('button', { name: 'Salvar alterações' }).waitFor();
  assert.equal(await editor.getByLabel('Observações (opcional)').inputValue(), 'Sem sal');
  assert.equal(await editor.getByLabel('Participante', { exact: true }).inputValue(), person);
  await editor.getByRole('button', { name: 'Diminuir Lanche' }).click();
  assert.equal(await editor.getByRole('button', { name: 'Diminuir Lanche' }).isDisabled(), true);
  await editor.getByRole('button', { name: 'Aumentar Lanche' }).click();
  await editor.getByRole('button', { name: 'Aumentar Lanche' }).click();
  assert.equal(itemWrites.length, 0);
  await editor.getByLabel('Observações (opcional)').fill('');
  await editor.getByLabel('Participante', { exact: true }).selectOption(maria);
  let releaseMutation; mutationGate = new Promise(resolve => { releaseMutation = resolve; });
  await editor.getByRole('button', { name: 'Salvar alterações' }).evaluate(button => { button.click(); button.click(); });
  await editor.getByRole('button', { name: 'Salvando…' }).waitFor();
  await page.keyboard.press('Escape'); assert.equal(await editor.isVisible(), true);
  releaseMutation(); mutationGate = null;
  await editor.waitFor({ state: 'hidden' });
  assert.equal(itemWrites.length, 1);
  assert.equal(itemWrites[0].quantity, 3); assert.equal(itemWrites[0].notes, ''); assert.equal(itemWrites[0].participant_id, maria);
  await page.getByText('3 × Lanche', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Cancelar pedido', exact: true }).click();
  const cancellation = page.getByRole('dialog', { name: 'Cancelar pedido?', exact: true });
  await cancellation.getByRole('button', { name: 'Voltar' }).click(); assert.equal(itemWrites.length, 1);
  await page.getByRole('button', { name: 'Cancelar pedido', exact: true }).click();
  await cancellation.getByLabel('Motivo (opcional)').fill('Cliente desistiu');
  await cancellation.getByRole('button', { name: 'Confirmar cancelamento' }).click();
  await cancellation.waitFor({ state: 'hidden' }); assert.equal(itemWrites[1].reason, 'Cliente desistiu');
  Object.assign(orderItem, { status: 'NEW', can_customer_change: true, version: orderItem.version + 1 });
  await page.reload(); await page.getByText('Detalhes do item', { exact: true }).click();
  await page.getByRole('button', { name: 'Cancelar pedido', exact: true }).click();
  await cancellation.getByRole('button', { name: 'Confirmar cancelamento' }).click();
  await cancellation.waitFor({ state: 'hidden' }); assert.equal(itemWrites[2].reason, '');
  assert.equal(await page.getByRole('button', { name: /(?:Ver|Consultar) estado atual/i }).count(), 0);
  await page.goto('/staff/settings');
  const branding = page.locator('.unit-branding');
  await branding.getByRole('button', { name: 'Editar logo', exact: true }).click();
  await branding.getByLabel('Logo do estabelecimento').setInputFiles({ name: 'logo.png', mimeType: 'image/png', buffer: logo });
  await branding.getByRole('img', { name: 'Prévia da nova logo' }).waitFor();
  await branding.getByRole('button', { name: 'Salvar alterações', exact: true }).click();
  await page.locator('.ui-toast').getByText('Alterações salvas.', { exact: true }).waitFor();
  await page.locator('.ui-toast').waitFor({ state: 'hidden', timeout: 6000 });
  await page.reload(); await branding.getByRole('button', { name: 'Editar logo', exact: true }).click(); await branding.getByRole('img', { name: 'Logo atual da unidade' }).waitFor();
  await branding.getByRole('button', { name: 'Remover logo', exact: true }).click();
  await branding.getByRole('button', { name: 'Confirmar remoção', exact: true }).click();
  await page.locator('.ui-toast').getByText('Alterações salvas.', { exact: true }).waitFor();
  assert.equal(logoWrites, 2);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/customer');
  await page.getByRole('heading', { name: 'Boas-vindas à mesa.' }).waitFor();
  assert.equal(await page.locator('.customer-entrance').count(), 0);
  for (const status of [401, 403, 503]) {
    contextStatus = status; await page.goto('/customer');
    await page.getByRole('heading', { name: 'Não foi possível abrir o atendimento' }).waitFor();
    assert.equal(await page.getByRole('heading', { name: 'Página não encontrada' }).count(), 0);
  }
  assert.deepEqual(errors, []);
  console.log('PASS: customer routing, shared modal, focus/Escape, uncertain retries, no duplicate calls/checks, persistent session, participant cancel/error/success, branding preview/save/remove, four widths and reduced motion (controlled API).');
} finally { await context.close(); await browser.close(); }
