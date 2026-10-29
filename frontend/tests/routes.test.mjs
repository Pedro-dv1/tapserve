import assert from 'node:assert/strict';
import { test } from 'node:test';
import { appRoute, customerRoute } from '../src/app/routes.ts';
import { decodePublicContext } from '../src/lib/api.ts';

test('only registered paths match; NFC and dynamic products retain their routes', () => {
  for (const path of ['/customer', '/customer/', '/customer/menu', '/customer/cart/', '/customer/table', '/customer/orders', `/customer/products/${crypto.randomUUID()}`]) assert.equal(appRoute(path), 'customer', path);
  for (const path of ['/a/opaque-token', '/a/opaque-token/']) assert.equal(appRoute(path), 'customer');
  for (const path of ['/staff', '/staff/login', '/staff/settings/', '/staff/production', '/platform/']) assert.notEqual(appRoute(path), 'not-found');
  for (const path of ['/admin', '/admin/staff', '/admin/settings/', '/admin/production', '/admin/menu', '/admin/operation', '/admin/orders', '/admin/calls', '/admin/points']) assert.equal(appRoute(path), 'staff');
  for (const path of ['/missing', '/customerish', '/customer/unknown', '/customer/menu/extra', '/customer/products/invalid', '/staff/unknown', '/staffish', '/admin/unknown', '/adminish', '/a/token/extra', '/api/v1/unknown/']) assert.equal(appRoute(path), 'not-found', path);
  assert.equal(customerRoute('/customer/table/').tab, 'table');
  assert.equal(customerRoute('/customer/nope').tab, 'not-found');
  assert.equal(appRoute('/'), 'health');
});

test('branding context accepts only the scoped first-party image endpoint', () => {
  const context = { device_id: 'device', company_name: 'Company', unit_name: 'Unit', expires_at: 'later', point: { id: 'point', name: 'Table', type: 'TABLE', active: true, nfc_enabled: true, qr_enabled: true, block_new_devices: false } };
  assert.equal(decodePublicContext(context).unit_logo_url, null);
  const url = '/api/v1/public/unit-logo/image/?v=0123456789abcdef';
  assert.equal(decodePublicContext({ ...context, unit_logo_url: url }).unit_logo_url, url);
  for (const value of ['https://foreign.example/logo.png', '//foreign/logo', '/api/v1/admin/unit-logo/image/', 1]) assert.throws(() => decodePublicContext({ ...context, unit_logo_url: value }));
});
