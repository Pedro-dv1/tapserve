import assert from 'node:assert/strict';
import { test } from 'node:test';
function luminance(hex) {
  const [r, g, b] = hex.match(/[\da-f]{2}/gi).map(value => { const srgb = parseInt(value, 16) / 255; return srgb <= .04045 ? srgb / 12.92 : ((srgb + .055) / 1.055) ** 2.4; });
  return .2126 * r + .7152 * g + .0722 * b;
}
test('reading/action colors satisfy 4.5:1 against their flat backgrounds', () => {
  for (const [text, background] of [['111111', 'e5a62b'], ['62625f', 'ffffff'], ['62625f', 'f5f5f3'], ['ffffff', '151715'], ['b8bcb6', '151715'], ['634514', 'f9efda'], ['4b370d', 'fff0cb'], ['181818', 'ffffff'], ['55564f', 'ffffff'], ['181818', 'faf7ed'], ['805400', 'ffffff']]) {
    const values = [luminance(text), luminance(background)].sort((a, b) => b - a);
    assert.ok((values[0] + .05) / (values[1] + .05) >= 4.5, `${text} on ${background}`);
  }
});
