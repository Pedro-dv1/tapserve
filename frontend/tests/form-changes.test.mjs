import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formSnapshot, formSaveResult, savePendingForms } from '../src/lib/formChanges.ts';
import { callMessages, orderMessages } from '../src/lib/actionMessages.ts';

// Minimal DOM boundary; the production comparison and async submission code is unmodified.
class Input {
  constructor(name, value, type = 'text', attributes = {}) { Object.assign(this, { name, value, type, dataset: {}, checked: false, files: [], attributes }); }
  hasAttribute(name) { return Object.hasOwn(this.attributes, name); }
  get valueAsNumber() { return Number(this.value); }
}
class Form extends EventTarget {
  isConnected = true; valid = true; submit = { disabled: false }; writes = 0; dataset = {};
  constructor(fields = []) { super(); this.fields = fields; }
  querySelectorAll() { return this.fields; }
  querySelector() { return this.submit; }
  reportValidity() { return this.valid; }
  requestSubmit() { this.writes++; queueMicrotask(() => formSaveResult(this, true)); }
}
function dom(run) {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'HTMLInputElement');
  Object.defineProperty(globalThis, 'HTMLInputElement', { configurable: true, value: Input });
  try { run(); } finally { if (original) Object.defineProperty(globalThis, 'HTMLInputElement', original); else delete globalThis.HTMLInputElement; }
}

test('dirty comparison covers restored text, numeric equivalence, disabled values and checkboxes', () => dom(() => {
  const name = new Input('name', 'Original'), price = new Input('price', '10.00', 'number'), check = new Input('active', 'on', 'checkbox'); check.checked = true;
  const form = new Form([name, price, check]), initial = formSnapshot(form);
  name.value = 'Outro'; assert.notEqual(formSnapshot(form), initial); name.value = 'Original';
  price.value = '10'; assert.equal(formSnapshot(form), initial);
  check.checked = false; assert.notEqual(formSnapshot(form), initial); check.checked = true;
  name.disabled = true; assert.equal(formSnapshot(form), initial);
}));

test('files, hidden removal flags, editable associations and ignored picker fields compare actual values', () => dom(() => {
  const file = new Input('image', '', 'file'), remove = new Input('remove_image', 'false', 'hidden');
  const first = new Input('options', 'a', 'hidden', { 'data-dirty-set': '' }), second = new Input('options', 'b', 'hidden', { 'data-dirty-set': '' });
  const picker = new Input('options-picker', '', 'select', { 'data-dirty-ignore': '' });
  const form = new Form([file, remove, first, second, picker]), initial = formSnapshot(form);
  file.files = [{ name: 'photo.png', size: 10, type: 'image/png', lastModified: 123 }]; assert.notEqual(formSnapshot(form), initial);
  file.files = []; picker.value = 'transient'; assert.equal(formSnapshot(form), initial);
  remove.value = 'true'; assert.notEqual(formSnapshot(form), initial); remove.value = 'false';
  form.fields = [file, remove, second]; assert.notEqual(formSnapshot(form), initial);
  form.fields.push(first); assert.equal(formSnapshot(form), initial);
}));

test('async relation fields use their explicit initial selection', () => dom(() => {
  const relation = new Input('category', ''); relation.dataset.initialValue = 'category-id';
  const form = new Form([relation]), initial = formSnapshot(form, true);
  relation.dataset.loading = 'true'; assert.equal(formSnapshot(form), initial);
  relation.dataset.loading = 'false'; assert.notEqual(formSnapshot(form), initial);
  relation.value = 'category-id'; assert.equal(formSnapshot(form), initial);
  relation.value = 'another'; assert.notEqual(formSnapshot(form), initial);
}));

test('save-before-leave waits for confirmation, stops on error and respects validation and disabled submissions', async () => {
  const original = globalThis.requestAnimationFrame; globalThis.requestAnimationFrame = callback => { queueMicrotask(callback); return 1; };
  try {
    const form = new Form(); let confirm; form.requestSubmit = () => { form.writes++; confirm = () => formSaveResult(form, true); };
    let done = false; const saving = savePendingForms([form]).then(value => { done = value; });
    await Promise.resolve(); assert.equal(done, false); assert.equal(form.writes, 1);
    confirm(); await saving; assert.equal(done, true);
    const invalid = new Form(); invalid.valid = false; assert.equal(await savePendingForms([invalid]), false); assert.equal(invalid.writes, 0);
    const failed = new Form(); failed.requestSubmit = () => queueMicrotask(() => formSaveResult(failed, false));
    const next = new Form(); assert.equal(await savePendingForms([failed, next]), false); assert.equal(next.writes, 0);
    const disabled = new Form(); disabled.submit.disabled = true; assert.equal(await savePendingForms([disabled]), false); assert.equal(disabled.writes, 0);
    assert.equal(await savePendingForms([new Form(), new Form()]), true);
  } finally { if (original) globalThis.requestAnimationFrame = original; else delete globalThis.requestAnimationFrame; }
});

test('call and order transitions have distinct semantic feedback', () => {
  assert.equal(callMessages.RESOLVED, 'Chamado marcado como resolvido.');
  assert.equal(callMessages.ASSIGNED, 'Chamado assumido com sucesso.');
  assert.equal(callMessages.CANCELLED, 'Chamado cancelado com sucesso.');
  assert.equal(orderMessages.READY, 'Pedido pronto para entrega.');
  assert.equal(orderMessages.DELIVERED, 'Pedido marcado como entregue.');
  assert.equal(new Set(Object.values(orderMessages)).size, Object.keys(orderMessages).length);
});
