import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

const script = readFileSync(new URL('../public/assets/brand/loader.js', import.meta.url), 'utf8');
function entrance({ reduced = false, complete = false } = {}) {
  let now = 0;
  let nextId = 0;
  const timers = new Map();
  const listeners = new Map();
  const classes = new Set();
  const panel = { hidden: true, classList: { add: value => classes.add(value) } };
  const root = { inert: false };
  const window = {
    matchMedia: () => ({ matches: reduced }),
    setTimeout(callback, delay) { const id = ++nextId; timers.set(id, { at: now + delay, callback }); return id; },
    clearTimeout: id => timers.delete(id),
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: name => listeners.delete(name),
  };
  runInNewContext(script, { window, document: { readyState: complete ? 'complete' : 'loading', getElementById: id => id === 'site-preloader' ? panel : root }, performance: { now: () => now } });
  return {
    panel, root, classes,
    loaded() { listeners.get('load')?.(); },
    advance(until) {
      while (true) {
        const next = [...timers].filter(([, timer]) => timer.at <= until).sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        now = next[1].at; timers.delete(next[0]); next[1].callback();
      }
      now = until;
    },
  };
}
test('site entrance shows the original mark briefly, then restores interaction and retires', () => {
  const loader = entrance();
  assert.equal(loader.panel.hidden, false); assert.equal(loader.root.inert, true);
  loader.advance(100); loader.loaded(); loader.advance(599);
  assert.equal(loader.classes.has('is-finished'), false);
  loader.advance(600);
  assert.equal(loader.root.inert, false); assert.equal(loader.classes.has('is-finished'), true);
  loader.advance(780); assert.equal(loader.panel.hidden, true);
});
test('slow or failed bootstrap releases the prerendered site by the bounded deadline', () => {
  const loader = entrance();
  loader.advance(1600); assert.equal(loader.root.inert, false);
  loader.advance(1780); assert.equal(loader.panel.hidden, true);
  loader.loaded(); loader.advance(5000); assert.equal(loader.panel.hidden, true);
});
test('reduced motion and an already loaded document have no minimum entrance delay', () => {
  const loader = entrance({ reduced: true, complete: true });
  loader.advance(0);
  assert.equal(loader.panel.hidden, true); assert.equal(loader.root.inert, false);
});
