import assert from 'node:assert/strict';
import { test } from 'node:test';
import { existsSync, readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
// Structural checks use the installed compiler; browser geometry is not tested.
const hooks = registerHooks({
 resolve(specifier, context, next) {
  if (specifier.startsWith('.') && context.parentURL?.includes('/src/')) {
   for (const extension of ['.tsx', '.ts']) { const url = new URL(specifier + extension, context.parentURL); if (existsSync(url)) return next(url.href, context); }
  }
  return next(specifier, context);
 },
 load(url, context, next) {
  if (url.endsWith('.css')) return { format: 'module', source: '', shortCircuit: true };
  if (/\.tsx?$/.test(url)) return { format: 'module', source: ts.transpileModule(readFileSync(fileURLToPath(url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX } }).outputText, shortCircuit: true };
  return next(url, context);
 },
});
const { staffPages, staffHome, staffPath } = await import('../src/features/staff/navigation.ts');
const { default: AdminLayout } = await import('../src/features/staff/AdminLayout.tsx');
const { default: AttendantLayout } = await import('../src/features/staff/AttendantLayout.tsx');
const { statusNames } = await import('../src/features/customer/orderStatus.ts');
const { FulfillmentBadge, FulfillmentSelector } = await import('../src/components/Fulfillment.tsx');
const { decodeWorkItems, elapsedMinutes } = await import('../src/features/staff/workItems.ts');
const { decodeOperation } = await import('../src/features/staff/Operation.tsx');
const { ProductionCard } = await import('../src/features/staff/Production.tsx');
const { Pagination, Editor } = await import('../src/features/staff/StaffUI.tsx');
const { SecretInput, LoadingSkeleton, tableLabel, CustomerHeader } = await import('../src/components/Interface.tsx');
const { decodeItem, latestItem } = await import('../src/features/customer/orderData.ts');
const { default: ActionPopup } = await import('../src/components/ActionPopup.tsx');
const { default: StaffLogin } = await import('../src/features/staff/StaffLogin.tsx');
const { default: ItemActions } = await import('../src/features/customer/ItemActions.tsx');
const { ResourceSelect } = await import('../src/features/staff/CatalogManagement.tsx');
const { default: CustomerWorkspace } = await import('../src/features/customer/CustomerWorkspace.tsx');
const { default: ProductVideo } = await import('../src/components/ProductVideo.tsx');
const { default: PointIdentifiers } = await import('../src/features/staff/PointIdentifiers.tsx');
const { default: Modal } = await import('../src/components/Modal.tsx');
const { default: Feedback } = await import('../src/components/Feedback.tsx');
const { default: MobileNavigation } = await import('../src/features/staff/MobileNavigation.tsx');
const { default: MenuBrowser } = await import('../src/features/customer/MenuBrowser.tsx');
const { default: ManualOrder } = await import('../src/features/staff/ManualOrder.tsx');
const { default: ProductGallery } = await import('../src/features/customer/ProductGallery.tsx');
const { ProductCard } = await import('../src/features/customer/MenuBrowser.tsx');
const { decodePolicy } = await import('../src/features/staff/OrderPolicy.tsx');
const { decodeTables } = await import('../src/features/staff/Operation.tsx');
const { decodeDetail, selectionError, selectionTotal } = await import('../src/features/customer/menuData.ts');
const { decodeStaffPage } = await import('../src/lib/api.ts');
const { default: NotFound } = await import('../src/app/NotFound.tsx');
hooks.deregister();

test('fulfillment controls expose text and keyboard buttons and preserve legacy presentation', () => {
 assert.equal(renderToStaticMarkup(React.createElement(FulfillmentBadge, { mode: 'DINE_IN' })), '');
 const badge = renderToStaticMarkup(React.createElement(FulfillmentBadge, { mode: 'TAKEAWAY' }));
 assert.ok(badge.includes('Para levar')); assert.ok(badge.includes('<svg'));
 const selector = renderToStaticMarkup(React.createElement(FulfillmentSelector, { value: 'TAKEAWAY', disabled: true, change() {} }));
 assert.ok(selector.includes('Consumir aqui')); assert.ok(selector.includes('aria-pressed="true"')); assert.ok(selector.includes('<fieldset class="fulfillment-selector" disabled=""'));
});

test('gallery handles missing media, ordered photos and on-demand video without loading video in cards', () => {
 const base = { id: crypto.randomUUID(), name: 'Prato', description: '', base_price: '10.00', has_image: false, has_video: false, groups: [] };
 const empty = decodeDetail(base);
 assert.equal(empty.allergen_info, ''); assert.deepEqual(empty.photos, []);
 let html = renderToStaticMarkup(React.createElement(ProductGallery, { product: empty }));
 assert.ok(html.includes('imagem indisponível')); assert.equal(html.includes('<video'), false);
 const detailed = decodeDetail({ ...base, has_image: true, image_version: '0123456789abcdef', has_video: true, photos: [{ id: crypto.randomUUID(), alt_text: 'Vista lateral', position: 2 }] });
 html = renderToStaticMarkup(React.createElement(ProductGallery, { product: detailed }));
 assert.ok(html.includes('Foto 1 de 2')); assert.ok(html.includes('Foto 2 de 2'));
 assert.ok(html.includes('/image/?v=0123456789abcdef'));
 assert.ok(html.includes('Ver vídeo de Prato')); assert.equal(html.includes('<video'), false);
 const card = renderToStaticMarkup(React.createElement(ProductCard, { product: detailed, open() {} }));
 assert.equal(card.includes('Ver vídeo'), false); assert.equal(card.includes('/photos/'), false);
 for (const photos of ['invalid', [{ id: '../file', alt_text: '', position: 0 }], [{ id: crypto.randomUUID(), alt_text: '', position: -1 }]]) assert.throws(() => decodeDetail({ ...base, photos }));
 assert.equal(decodePolicy({ customer_edit_window_minutes: 3, table_takeaway_enabled: false, leftover_packaging_enabled: false, menu_layout: 'EDITORIAL' }).menu_layout, 'EDITORIAL');
 assert.throws(() => decodePolicy({ customer_edit_window_minutes: 3, table_takeaway_enabled: false, leftover_packaging_enabled: false, menu_layout: 'ARBITRARY_CSS' }));
});

test('staff lists normalize repeated identities without merging people with the same name', () => {
 const person = { id: 'first', name: 'Ana', login_code: 'ana', role: 'WAITER', active: true, permissions: [] };
 const page = decodeStaffPage({ count: 2, next: null, previous: null, results: [person, { ...person }, { ...person, id: 'second', login_code: 'ana2' }] });
 assert.deepEqual(page.results.map(person => person.id), ['first', 'second']);
 assert.equal(page.results.length, 2);
 assert.equal(page.count, 2);
});

test('attendant navigation has exactly tables, orders, calls and the ellipsis destination', () => {
 const permissions = ['VIEW_OPERATION', 'VIEW_ALL_TABLES', 'ASSIGN_SERVICE_REQUEST', 'CREATE_MANUAL_ORDER'];
 const ctx = { ...context(permissions), staff: { role: 'WAITER', permissions } };
 const html = renderToStaticMarkup(React.createElement(MobileNavigation, { pages: staffPages(ctx), current: '/staff/orders' }));
 assert.deepEqual([...html.matchAll(/<span>(.*?)<\/span>/g)].map(match => match[1]), ['Mesas', 'Pedidos', 'Chamados', 'Mais']);
 assert.equal((html.match(/<a /g) ?? []).length, 4);
 assert.match(html, /href="\/staff\/orders" aria-current="page"/);
 assert.match(html, /cx="19" cy="12"/);
 assert.equal(staffHome({ ...ctx, auth_strength: 'password', staff: { role: 'OWNER', permissions: [...permissions, 'UPDATE_PRODUCTION_STATUS'] } }), '/admin/operation');
});

test('menu starts with the complete explicit filter and optional direct selectors stay direct', () => {
 const html = renderToStaticMarkup(React.createElement(MenuBrowser, { open() {} }));
 assert.match(html, /aria-pressed="true"[^>]*>Tudo/);
 assert.match(html, /aria-pressed="false"[^>]*>Mais pedidos/);
 const selector = renderToStaticMarkup(React.createElement(ResourceSelect, { name: 'menu', label: 'Selecionar cardápio', kind: 'menus', initial: '' }));
 assert.equal((selector.match(/Selecionar cardápio/g) ?? []).length, 1);
 assert.equal(selector.includes('Buscar cardápio'), false);
});

test('reusable groups and independent extras share cart validation and are never charged twice', () => {
 const option = { id: 'bacon', name: 'Bacon', additional_price: '4.00' };
 const base = { id: 'product', name: 'Lanche', description: '', base_price: '10.00', has_image: false, groups: [], individual_options: [option] };
 const direct = decodeDetail(base);
 assert.equal(selectionError(direct, ['bacon']), '');
 assert.equal(selectionTotal(direct, ['bacon'], 2), 2800);
 assert.notEqual(selectionError(direct, ['bacon', 'bacon']), '');
 const both = decodeDetail({ ...base, groups: [{ id: 'group', name: 'Grupo', selection_type: 'MULTIPLE', required: false, min_choices: 0, max_choices: 1, options: [option] }] });
 assert.equal(selectionTotal(both, ['bacon']), 1400);
 assert.equal(both.groups.flatMap(group => group.options).length, 1);
});

test('table summaries reject incorrect counts and manual drafts use a real confirmation modal', () => {
 const point = { id: crypto.randomUUID(), number: 8, name: '', type: 'TABLE', active: true, nfc_enabled: true, qr_enabled: true, block_new_devices: false };
 const summary = { ...point, session: null, connected_devices: 2, order_count: 3, active_order_count: 2, subtotal: '12.35', pending_calls: [{ id: 'call', kind: 'CLEANING' }] };
 assert.equal(decodeTables({ results: [summary], next: null }).results[0].pending_calls[0].kind, 'CLEANING');
 for (const invalid of [{ order_count: -1 }, { connected_devices: 1.5 }, { subtotal: 'bad' }, { pending_calls: null }]) assert.throws(() => decodeTables({ results: [{ ...summary, ...invalid }] }));
 const previous = globalThis.sessionStorage;
 try {
  globalThis.sessionStorage = { getItem: () => null };
  const html = renderToStaticMarkup(React.createElement(ManualOrder, { point, session: null, close() {}, changed() {} }));
  assert.ok(html.includes('<dialog'));
  assert.ok(html.includes('Novo pedido'));
  assert.ok(html.includes('Confirmar pedido'));
  assert.match(html, /<button disabled="">Confirmar pedido/);
 } finally { if (previous === undefined) delete globalThis.sessionStorage; else globalThis.sessionStorage = previous; }
});

test('customer table labels expose only the registered number and preserve accessible popups', () => {
 for (const [name, expected] of [['Mesa 1', 'Mesa 01'], ['Mesa 24 QA', 'Mesa 24'], ['12', 'Mesa 12'], ['Mesa de demonstração', 'Mesa'], ['QA-2026', 'Mesa'], ['Mesa 000', 'Mesa']]) assert.equal(tableLabel(name), expected);
 const html = renderToStaticMarkup(React.createElement(CustomerHeader, { context: { point: { type: 'TABLE' }, company_name: 'QA company' }, pointName: 'Mesa 12 demonstração' }));
 assert.ok(html.includes('Mesa 12')); assert.equal(/QA company|demonstração/.test(html), false);
 const branded = renderToStaticMarkup(React.createElement(CustomerHeader, { context: { point: { type: 'TABLE', number: 12 }, unit_name: 'Restaurante', unit_logo_url: '/api/v1/public/unit-logo/image/?v=0123456789abcdef' }, pointName: 'Mesa 12' }));
 assert.ok(branded.includes('src="/brand/TapServe-logo-wordmark.png" alt="TapServe"'));
 assert.equal(branded.includes('/unit-logo/'), false);
 const popup = renderToStaticMarkup(React.createElement(ActionPopup, { notice: { title: 'Conta solicitada', message: 'A equipe foi avisada.' }, close() {} }));
 for (const text of ['<dialog', 'aria-labelledby', 'Entendido', 'Conta solicitada']) assert.ok(popup.includes(text));
});

test('item decoding retains participant identity and actual observations', () => {
 const data = { id: 'item', product_id: 'product', version: 2, snapshot: { name: 'Lanche', options: [] }, quantity: 3, notes: '', status: 'NEW', line_total: '37.05', can_customer_change: true, editable_until: 'later', participant_id: 'person', participant_name: 'Maria', delivered_by_id: null };
 assert.equal(decodeItem(data).participant_id, 'person');
 assert.equal(decodeItem(data).notes, '');
 assert.equal(decodeItem({ ...data, participant_id: null }).participant_id, null);
 const current = decodeItem({ ...data, version: 3, quantity: 4, line_total: '49.40' });
 const oldReceipt = decodeItem(data);
 assert.equal(latestItem(current, oldReceipt), current);
 assert.equal(latestItem(oldReceipt, current), current);
 assert.equal(latestItem(undefined, oldReceipt), oldReceipt);
 for (const fields of [{ participant_id: 42 }, { version: 0 }, { quantity: 100 }]) assert.throws(() => decodeItem({ ...data, ...fields }));
});
test('customer home, table cleanup, lazy video and NFC fallback expose the requested controls', () => {
 const previousWindow = globalThis.window; const previousStorage = globalThis.sessionStorage;
 const point = { id: crypto.randomUUID(), name: 'Mesa 07', type: 'TABLE', active: true, access_enabled: true, token_version: 1, qr_enabled: true, nfc_enabled: true, block_new_devices: false };
 const context = { device_id: crypto.randomUUID(), point, company_name: 'Restaurante', unit_name: 'Centro', expires_at: '2099-01-01T00:00:00Z' };
 try {
  globalThis.window = { location: { pathname: '/customer', search: '' }, isSecureContext: false };
  globalThis.sessionStorage = { getItem: () => null };
  const home = renderToStaticMarkup(React.createElement(CustomerWorkspace, { context }));
  for (const label of ['Ver cardápio', 'Chamar garçom', 'Pedir a conta', 'Mesa 07']) assert.ok(home.includes(label));
  assert.ok(home.includes('após o primeiro pedido'));
  globalThis.window.location.pathname = '/customer/table';
  const table = renderToStaticMarkup(React.createElement(CustomerWorkspace, { context }));
  assert.equal(table.includes('Consumo'), false);
  for (const tab of ['menu', 'cart', 'orders', 'table']) {
   globalThis.window.location.pathname = `/customer/${tab}`;
   const html = renderToStaticMarkup(React.createElement(CustomerWorkspace, { context }));
   assert.equal(html.includes('class="customer-back"'), false, tab);
   assert.ok(html.includes('class="customer-navigation"'), tab);
  }
  globalThis.window.location.pathname = `/customer/products/${crypto.randomUUID()}`;
  const detail = renderToStaticMarkup(React.createElement(CustomerWorkspace, { context }));
  assert.ok(detail.includes('class="customer-back"'));
  assert.equal(detail.includes('class="customer-navigation"'), false);
  const video = renderToStaticMarkup(React.createElement(ProductVideo, { id: 'product', name: 'Prato' }));
  assert.ok(video.includes('Ver vídeo de Prato')); assert.equal(video.includes('<video'), false); assert.equal(video.includes('/video/'), false);
  const admin = renderToStaticMarkup(React.createElement(PointIdentifiers, { point, url: 'https://example.com/a/capability', changed: () => {} }));
  for (const label of ['Baixar QR Code', 'Copiar link', 'Gravar tag NFC', 'somente leitura', 'aplicativo NFC', 'Estado físico não verificado']) assert.ok(admin.includes(label));
 } finally {
  if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow;
  if (previousStorage === undefined) delete globalThis.sessionStorage; else globalThis.sessionStorage = previousStorage;
 }
});
test('404 returns to its application area and custom dialogs/feedback retain accessible structure', () => {
 const previousWindow = globalThis.window;
 try {
  for (const [pathname, href] of [['/customer/missing', '/customer'], ['/staff/missing', '/staff'], ['/missing', '/']]) {
   globalThis.window = { location: { pathname } };
   const html = renderToStaticMarkup(React.createElement(NotFound));
   assert.ok(html.includes('Página não encontrada')); assert.ok(html.includes(`href="${href}"`));
  }
  const html = renderToStaticMarkup(React.createElement(Modal, { open: true, title: 'Remover participante?', description: 'Remover Ana da mesa?', close() {} }, React.createElement('button', {}, 'Cancelar')));
  for (const text of ['<dialog', 'aria-labelledby', 'aria-describedby', 'Remover Ana', 'Cancelar']) assert.ok(html.includes(text));
  for (const tone of ['info', 'success', 'warning', 'processing', 'error']) {
   const feedback = renderToStaticMarkup(React.createElement(Feedback, { tone }, 'Mensagem'));
   assert.ok(feedback.includes(`role="${tone === 'error' ? 'alert' : 'status'}"`));
  }
 } finally { if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow; }
});
const context = permissions => ({ auth_strength: 'pin', staff: { role: 'WAITER', permissions } });
test('staff navigation denies absent grants and requires strong authentication for management', () => {
 assert.deepEqual(staffPages(context([])), []);
 assert.deepEqual(staffPages(context(['MANAGE_MENU'])), []);
 assert.deepEqual(staffPages({ ...context(['MANAGE_MENU']), auth_strength: 'password' }), []);
 assert.equal(staffPages({ auth_strength: 'password', staff: { role: 'ADMIN', permissions: ['MANAGE_MENU'] } })[0].href, '/admin/menu');
 assert.deepEqual(staffPages(context(['UPDATE_PRODUCTION_STATUS'])), []);
 assert.equal(staffHome(context(['VIEW_OPERATION', 'UPDATE_PRODUCTION_STATUS'])), '/staff/production');
 assert.equal(staffHome(context(['VIEW_OPERATION', 'VIEW_ALL_TABLES'])), '/staff/operation');
});

test('management has its complete independent shell; attendant has exactly its four destinations', () => {
 const permissions = ['VIEW_OPERATION', 'VIEW_ALL_TABLES', 'UPDATE_PRODUCTION_STATUS', 'ASSIGN_SERVICE_REQUEST', 'MANAGE_MENU', 'MANAGE_STAFF', 'MANAGE_SETTINGS', 'MANAGE_SERVICE_POINTS'];
 for (const role of ['OWNER', 'ADMIN', 'MANAGER']) {
  const admin = { auth_strength: 'password', unit_name: 'Centro', company_name: 'Restaurante', staff: { role, name: 'Ana', permissions } };
  const pages = staffPages(admin);
  assert.equal(pages.length, 8);
  assert.equal(staffHome(admin), '/admin/operation');
  assert.equal(staffPath(admin, '/staff/production'), '/admin/production');
  const html = renderToStaticMarkup(React.createElement(AdminLayout, { context: admin, pages, current: pages[0], busy: false, leave() {} }));
  for (const page of pages) assert.ok(html.includes(`href="${page.href}"`), page.href);
  assert.equal(html.includes('/staff/more'), false);
  assert.equal((html.match(/id="staff-profile-popover"/g) ?? []).length, 1);
 }
 const waiter = { auth_strength: 'password', unit_name: 'Centro', staff: { role: 'WAITER', name: 'Bia', permissions } };
 const pages = staffPages(waiter);
 assert.equal(pages.some(page => page.href.startsWith('/admin')), false);
 const html = renderToStaticMarkup(React.createElement(AttendantLayout, { context: waiter, pages, current: pages[0], busy: false, leave() {} }));
 assert.match(html, /attendant-header[\s\S]*staff-avatar[\s\S]*<main/);
 assert.equal((html.match(/id="staff-profile-popover"/g) ?? []).length, 1);
 const labels = Object.values(statusNames);
 assert.equal(new Set(labels).size, labels.length);
 assert.equal(statusNames.ACCEPTED, 'Aceito'); assert.equal(statusNames.DELIVERING, 'Em entrega');
});
const created = '2026-10-08T12:00:00Z';
const row = { id: 'item', product_id: 'product', sector_id: 'sector', session_id: 'session', point_names: ['Mesa 07'], snapshot: { name: 'X-Burger', sector_name: 'Cozinha', options: [{ id: 'option', name: 'Cheddar extra' }] }, status: 'NEW', quantity: 2, version: 1, notes: 'Sem cebola\nAlergia: amendoim', created_at: created, line_total: '69.80', participant_name: 'Maria', delivered_by_id: null, editable_until: created, can_customer_change: false };
test('work item contract preserves snapshots and rejects invalid dates, money, quantities and states', () => {
 const data = decodeWorkItems({ results: [row], next: '/next' });
 assert.equal(data.next, true);
 assert.deepEqual(data.results[0].option_names, ['Cheddar extra']);
 assert.equal(data.results[0].line_total, '69.80');
 for (const change of [{ quantity: 0 }, { quantity: 100 }, { quantity: 1.5 }, { version: 0 }, { status: 'UNKNOWN' }, { created_at: 'invalid' }, { line_total: '1.999' }, { line_total: '-1.00' }, { can_customer_change: 'true' }, { point_names: 'Mesa' }]) assert.throws(() => decodeWorkItems({ results: [{ ...row, ...change }] }));
 assert.equal(elapsedMinutes(created, Date.parse(created) + 300_000), 5);
 assert.equal(elapsedMinutes(created, Date.parse(created) - 60_000), 0);
 for (const item_counts of [{}, { NEW: -1 }, { NEW: 1.5 }]) assert.throws(() => decodeOperation({ results: [{ item_counts }] }), /Resumo da operação inválido/);
});
test('KDS exposes participant, options, observations, quantities and only the applicable transition', () => {
 for (const [status, action] of [['NEW', 'Aceitar item'], ['ACCEPTED', 'Iniciar preparo'], ['PREPARING', 'Marcar pronto'], ['READY', null]]) {
  const item = decodeWorkItems({ results: [{ ...row, status }] }).results[0];
  const html = renderToStaticMarkup(React.createElement(ProductionCard, { item, now: Date.parse(created) + 300_000, refresh() {} }));
  for (const text of ['Mesa 07', '2 × X-Burger', 'Cheddar extra', 'Sem cebola', 'Alergia: amendoim', 'Para Maria', '5 min de espera']) assert.ok(html.includes(text), text);
  assert.equal((html.match(/<button/g) ?? []).length, status === 'NEW' ? 2 : action ? 1 : 0);
  assert.equal(html.includes('Recusar'), status === 'NEW');
  if (action) assert.ok(html.includes(action));
 }
});

test('pagination follows server availability and hides absent directions', () => {
 const render = props => renderToStaticMarkup(React.createElement(Pagination, { change() {}, ...props }));
 assert.equal(render({ page: 1, previous: false, next: false }), '');
 const first = render({ page: 1, previous: false, next: true });
 assert.ok(first.includes('Próxima')); assert.equal(first.includes('Anterior'), false);
 const last = render({ page: 2, previous: true, next: false, busy: true });
 assert.ok(last.includes('Anterior')); assert.equal(last.includes('Próxima'), false); assert.ok(last.includes('disabled'));
});
test('product modal, secret controls and page skeletons expose accessible structure', () => {
 const html = renderToStaticMarkup(React.createElement(Editor, { modal: true, title: 'Cadastrar produto', close() {} }, React.createElement('form')));
 assert.ok(html.includes('<dialog')); assert.ok(html.includes('aria-labelledby')); assert.ok(html.includes('aria-label="Fechar"'));
 const secret = renderToStaticMarkup(React.createElement(SecretInput, { label: 'PIN', name: 'pin', inputMode: 'numeric', defaultValue: '123456' }));
 assert.ok(secret.includes('type="password"')); assert.ok(secret.includes('Mostrar PIN')); assert.ok(secret.includes('type="button"')); assert.ok(secret.includes('value="123456"'));
 const login = renderToStaticMarkup(React.createElement(StaffLogin));
 assert.equal(login.includes('employee-card'), false); assert.equal(login.includes('Cada funcionário possui'), false);
 assert.ok(login.includes('Mostrar PIN'));
 for (const [, pattern] of login.matchAll(/pattern="([^"]+)"/g)) assert.doesNotThrow(() => new RegExp(pattern, 'v'));
 const shapes = ['menu', 'product', 'orders', 'table', 'catalog', 'staff', 'points', 'operation', 'production', 'settings', 'calls', 'options', 'health'].map(variant => renderToStaticMarkup(React.createElement(LoadingSkeleton, { variant })));
 assert.equal(new Set(shapes).size, shapes.length);
 for (const shape of shapes) { assert.ok(shape.includes('aria-busy="true"')); assert.ok(shape.includes('aria-hidden="true"')); }
 for (const status of ['DELIVERED', 'REJECTED', 'CANCELLED']) assert.equal(renderToStaticMarkup(React.createElement(ItemActions, { item: { ...row, status }, manual: true, canEdit: true, canCancel: true, changed() {} })), '');
 const legacy = renderToStaticMarkup(React.createElement(ResourceSelect, { name: 'menu', label: 'Cardápio', kind: 'service-points/menu-options', initial: '', required: false }));
 assert.equal(/<select[^>]*\brequired/.test(legacy), false); assert.ok(legacy.includes('Nenhum'));
});
