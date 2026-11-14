import assert from 'node:assert/strict';
import { test } from 'node:test';
import { restoreFocus } from '../src/lib/focus.ts';
import { reportRecoverableError } from '../src/lib/recoverableError.ts';

test('focus restoration skips hidden, disabled, inert, removed and unfocusable targets (SQA-BUG-001)', () => {
  const doc = { activeElement: null, defaultView: { getComputedStyle: node => node.style } };
  function element(options = {}) {
    return { ownerDocument: doc, isConnected: true, style: { visibility: 'visible', opacity: '1' }, matches: () => false, closest: () => null, getClientRects: () => [{}], focus() { doc.activeElement = this; }, ...options };
  }
  for (const invalid of [{ isConnected: false }, { getClientRects: () => [] }, { matches: () => true }, { closest: () => ({}) }, { checkVisibility: () => false }, { style: { visibility: 'hidden' } }, { style: { opacity: '0' } }, { focus() {} }]) {
    const fallback = element(); doc.activeElement = null;
    restoreFocus([null, element(invalid), fallback]);
    assert.equal(doc.activeElement, fallback);
  }
  const trigger = element(), fallback = element();
  restoreFocus([trigger, fallback]); assert.equal(doc.activeElement, trigger);
  doc.body = element(); doc.documentElement = element();
  restoreFocus([doc.body, doc.documentElement, fallback]); assert.equal(doc.activeElement, fallback);
});

test('viewport cancellation is handled specifically; genuine transition and application errors stay observable (SQA-BUG-002)', () => {
  const messages = [];
  const previous = globalThis.reportError;
  globalThis.reportError = error => messages.push(error);
  try {
    reportRecoverableError(new DOMException('Transition was aborted because of invalid state. Viewport size changed', 'InvalidStateError'));
    assert.deepEqual(messages, []);
    const errors = [new Error('Transition was aborted because of invalid state. Viewport size changed'), new DOMException('Duplicate view-transition-name', 'InvalidStateError'), new DOMException('Snapshot capture failed', 'InvalidStateError'), new DOMException('Viewport size changed', 'AbortError'), new Error('A ViewTransition timed out because a Navigation stalled.', { cause: new DOMException('DOM update timed out', 'TimeoutError') }), new Error('Failed to render'), null];
    errors.forEach(reportRecoverableError);
    assert.deepEqual(messages, errors);
  } finally { if (previous === undefined) delete globalThis.reportError; else globalThis.reportError = previous; }
});
