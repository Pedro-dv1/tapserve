import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import ts from 'typescript';

const hooks = registerHooks({
  resolve(specifier, context, next) {
    try { return next(specifier, context); }
    catch (error) { if (specifier.startsWith('.') && !/\.[a-z]+$/i.test(specifier)) { for (const extension of ['.ts', '.tsx']) { try { return next(specifier + extension, context); } catch {} } } throw error; }
  },
  load(url, context, next) {
    if (/\.tsx?$/.test(url)) return { format: 'module', source: ts.transpileModule(readFileSync(fileURLToPath(url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX } }).outputText, shortCircuit: true };
    return next(url, context);
  },
});
const { decodeSettlement, decodePendingSettlement, settlementStorageKey, displaySettlementMoney } = await import('../src/features/staff/SessionSettlement.tsx');
hooks.deregister();

test('settlement decoder preserves external declaration and detects divergent balances', () => {
  const row = { id: 'session', status: 'OPEN', version: 2, consumption_total: '10.00', declared_received: '12.00', remaining: '-2.00', outstanding_items: 0, pending_calls: 1, declaration_notice: 'Declaração externa', receipts: [], lifecycle: [] };
  assert.equal(decodeSettlement(row).remaining, '-2.00');
  assert.match(displaySettlementMoney('99999999999999.99'), /99\.999\.999\.999\.999,99/);
  for (const invalid of [{ ...row, version: 0 }, { ...row, outstanding_items: -1 }, { ...row, remaining: 'NaN' }, { ...row, consumption_total: '-1.00' }, { ...row, receipts: null }]) assert.throws(() => decodeSettlement(invalid));
});

test('uncertain settlement operations are scoped by operator, unit and consumption session', () => {
  const context = { staff: { id: 'one' }, unit_id: 'unit-a' };
  const key = settlementStorageKey(context, 'session-a');
  assert.notEqual(key, settlementStorageKey({ ...context, staff: { id: 'two' } }, 'session-a'));
  assert.notEqual(key, settlementStorageKey({ ...context, unit_id: 'unit-b' }, 'session-a'));
  assert.notEqual(key, settlementStorageKey(context, 'session-b'));
  const pending = { action: 'RECEIPT', path: '/api/v1/staff/sessions/session-a/external-receipts/', body: { idempotency_key: '00000000-0000-4000-8000-000000000001', expected_version: 2, amount: '10.00' } };
  assert.deepEqual(decodePendingSettlement(pending, 'session-a'), pending);
  assert.throws(() => decodePendingSettlement(pending, 'session-b'));
  assert.throws(() => decodePendingSettlement({ ...pending, action: 'TRANSFER_MONEY' }, 'session-a'));
  assert.throws(() => decodePendingSettlement({ ...pending, path: '/api/v1/staff/sessions/session-a/../../staff/' }, 'session-a'));
});
