import assert from 'node:assert/strict';
import { test } from 'node:test';
import { existsSync, readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const hooks = registerHooks({ resolve(specifier, context, next) {
  if (specifier.startsWith('.') && context.parentURL?.includes('/src/')) {
    for (const extension of ['.tsx', '.ts']) { const url = new URL(specifier + extension, context.parentURL); if (existsSync(url)) return next(url.href, context); }
  }
  return next(specifier, context);
}, load(url, context, next) {
  if (url.endsWith('.css')) return { format: 'module', source: '', shortCircuit: true };
  if (/\.tsx?$/.test(url)) return { format: 'module', source: ts.transpileModule(readFileSync(fileURLToPath(url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX } }).outputText, shortCircuit: true };
  return next(url, context);
} });
const { default: MfaChallenge, decodeChallenge } = await import('../src/features/staff/MfaChallenge.tsx');
hooks.deregister();

test('MFA decoder never treats a partial challenge as staff identity', () => {
  const expires_at = new Date(Date.now() + 300_000).toISOString();
  assert.equal(decodeChallenge({ staff: {} }), null);
  assert.deepEqual(decodeChallenge({ mfa_required: true, enrollment_required: false, expires_at }), { mfa_required: true, enrollment_required: false, expires_at });
  assert.throws(() => decodeChallenge({ mfa_required: true, expires_at }));
  assert.throws(() => decodeChallenge({ mfa_required: true, enrollment_required: false, expires_at: 'invalid' }));
  assert.throws(() => decodeChallenge({ mfa_required: true, enrollment_required: true, expires_at, provisioning_uri: {} }));
});

test('MFA enrollment and recovery use labeled controls and never navigate to secret URLs', () => {
  const challenge = { mfa_required: true, enrollment_required: true, expires_at: new Date(Date.now() + 300_000).toISOString(), provisioning_uri: 'otpauth://totp/test?secret=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567&issuer=TapServe' };
  const html = renderToStaticMarkup(React.createElement(MfaChallenge, { challenge, realm: 'staff', authenticated() {}, cancel() {} }));
  assert.ok(html.includes('Configure seu autenticador'));
  assert.ok(html.includes('Código do autenticador'));
  assert.ok(html.includes('autoComplete="one-time-code"'));
  assert.ok(html.includes('Voltar ao login'));
  assert.equal(html.includes('href="otpauth:'), false);
  assert.equal(html.includes('localStorage'), false);
});
