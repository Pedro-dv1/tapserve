export function customerRoute(path: string) {
  const product = /^\/customer\/products\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\/?$/i.exec(path);
  if (product?.[1]) return { tab: 'product' as const, product: product[1] };
  if (/^\/customer\/?$/.test(path)) return { tab: 'home' as const, product: '' };
  const tab = /^\/customer\/(menu|cart|orders|table)\/?$/.exec(path)?.[1];
  if (tab === 'menu' || tab === 'cart' || tab === 'orders' || tab === 'table') return { tab, product: '' };
  return { tab: 'not-found' as const, product: '' };
}

export function appRoute(path: string) {
  if (/^\/a\/[^/]+\/?$/.test(path) || customerRoute(path).tab !== 'not-found') return 'customer';
  if (/^\/staff(?:\/(?:login|points|menu|operation|orders|calls|more|production|settings))?\/?$/.test(path)) return 'staff';
  if (/^\/admin(?:\/(?:staff|points|menu|operation|orders|calls|production|settings))?\/?$/.test(path)) return 'staff';
  if (/^\/platform\/?$/.test(path)) return 'platform';
  return path === '/' ? 'health' : 'not-found';
}
