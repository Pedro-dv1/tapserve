import fixture from '../data/product-catalog.json' with { type: 'json' };
import { ApiError, record } from '../../../frontend/src/lib/api.ts';
import { decodeDetail, selectionError, selectionTotal } from '../../../frontend/src/features/customer/menuData.ts';
export * from '../../../frontend/src/lib/api.ts';

// Present only QA products with original media; retain the complete source fixture for provenance.
const catalogue = fixture.products.filter(product => product.has_image);
export const products = catalogue.map(decodeDetail);
const categories = fixture.categories.filter(category => catalogue.some(product => product.category === category.id));
type Call = { id: string; created_at: string; kind: string; message: string; status: string; point_name: string; assigned_to_id: null; assignee_name: null; can_customer_cancel: boolean };
let calls: Call[] = [];
export function resetDemo() { calls = []; }

// Requests from reused product components terminate here; unsupported actions fail closed.
export async function request(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<unknown> {
  signal?.throwIfAborted();
  const url = new URL(path, 'https://demo.invalid');
  const page = (results: unknown[]) => ({ results, next: null, previous: null, count: results.length });
  if (method === 'GET' && url.pathname === '/api/v1/public/categories/') return page(categories);
  if (method === 'GET' && url.pathname === '/api/v1/public/menu/') {
    const query = (url.searchParams.get('search') ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const category = url.searchParams.get('category');
    const results = products.filter((product, index) => (!query || `${product.name} ${product.description}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes(query)) && (!category || catalogue[index]?.category === category) && (url.searchParams.get('popular') !== 'true' || product.most_ordered));
    return { ...page(results), presentation: { layout: 'COMPACT', hero: null, popular: products.filter(product => product.most_ordered).slice(0, 2) } };
  }
  const identifier = url.pathname.match(/^\/api\/v1\/public\/products\/([^/]+)\/$/)?.[1];
  if (method === 'GET' && identifier) {
    const product = products.find(product => product.id === identifier);
    if (!product) throw new ApiError(404, 'Produto indisponível nesta demonstração.');
    return structuredClone(product);
  }
  if (method === 'POST' && url.pathname === '/api/v1/public/quote/') {
    const input = record(body), product = products.find(product => product.id === input.product_id);
    if (!product || !Array.isArray(input.option_ids) || !input.option_ids.every(value => typeof value === 'string') || !Number.isInteger(input.quantity) || Number(input.quantity) < 1 || Number(input.quantity) > 99) throw new ApiError(400, 'Revise sua seleção.');
    const selected: string[] = input.option_ids;
    const invalid = selectionError(product, selected);
    if (invalid) throw new ApiError(400, invalid);
    return { name: product.name, unit_price: (selectionTotal(product, selected) / 100).toFixed(2), options: product.groups.flatMap(group => group.options).filter(option => selected.includes(option.id)) };
  }
  if (url.pathname === '/api/v1/public/service-requests/') {
    if (method === 'GET') return page(structuredClone(calls.filter(call => ['OPEN', 'ASSIGNED'].includes(call.status))));
    const input = record(body);
    if (method !== 'POST' || !['ATTENDANT', 'CLEANING', 'CUTLERY', 'NAPKIN', 'OTHER', 'CHECK'].includes(String(input.kind)) || typeof input.message !== 'string' || input.message.length > 500) throw new ApiError(400, 'Revise a solicitação demonstrativa.');
    const call: Call = { id: crypto.randomUUID(), created_at: new Date().toISOString(), kind: String(input.kind), message: input.message, status: 'OPEN', point_name: 'Mesa 08', assigned_to_id: null, assignee_name: null, can_customer_cancel: true };
    calls.push(call); return structuredClone(call);
  }
  const callId = url.pathname.match(/^\/api\/v1\/public\/service-requests\/([^/]+)\/cancel\/$/)?.[1];
  if (callId && method === 'POST') {
    const call = calls.find(call => call.id === callId);
    if (!call) throw new ApiError(400, 'Ação indisponível nesta demonstração.');
    call.status = 'CANCELLED'; call.can_customer_cancel = false; return structuredClone(call);
  }
  throw new ApiError(400, 'Esta ação não faz parte da demonstração local.');
}
