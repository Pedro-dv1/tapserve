import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const css = readFileSync(new URL('../src/design-system/base.css', import.meta.url), 'utf8');
function luminance(hex) {
  const rgb = hex.match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16) / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
}
function contrast(a, b) { const values = [luminance(a), luminance(b)].sort((x, y) => y - x); return (values[0] + .05) / (values[1] + .05); }
test('shared auxiliary text meets 4.5:1 on white, surface and control backgrounds (SQA-BUG-005)', () => {
  assert.equal(contrast('#000000', '#ffffff'), 21);
  const muted = css.match(/--muted:\s*(#[a-f\d]{6})/i)[1];
  for (const background of ['#ffffff', ...['surface', 'control', 'warm-surface'].map(name => css.match(new RegExp(`--${name}:\\s*(#[a-f\\d]{6})`, 'i'))[1])]) {
    assert(contrast(muted, background) >= 4.5, `${muted} on ${background}: ${contrast(muted, background)}`);
  }
});
