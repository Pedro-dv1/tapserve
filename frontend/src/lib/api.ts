export type Health = { status: 'ok' | 'unavailable'; database: 'ok' | 'unavailable' };

export class ApiError extends Error {
  readonly status: number;
  readonly fields: Record<string, string>;
  constructor(status: number, message: string, fields: Record<string, string> = {}) { super(message); this.status = status; this.fields = fields; }
}

export async function getHealth(signal: AbortSignal): Promise<Health> {
  const response = await fetch('/api/v1/health/', { signal, credentials: 'same-origin', cache: 'no-store' });
  if (!response.ok) throw new ApiError(response.status, 'O serviço está indisponível. Tente novamente.');
  const data: unknown = await response.json();
  if (typeof data !== 'object' || data === null || !('status' in data) || !('database' in data)
      || (data.status !== 'ok' && data.status !== 'unavailable')
      || (data.database !== 'ok' && data.database !== 'unavailable')) {
    throw new Error('Resposta inválida do serviço.');
  }
  return { status: data.status, database: data.database };
}

export type Staff = { id: string; name: string; login_code: string; role: string; active: boolean; permissions: string[] };
export type StaffContext = { staff: Staff; company_name: string; unit_id: string; unit_name: string; auth_strength: 'pin' | 'password' };
export type Role = { id: string; name: string; permissions: string[] };
export type StaffPage = { count: number; next: string | null; previous: string | null; results: Staff[] };

export function record(data: unknown): Record<string, unknown> {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) throw new Error('Resposta inválida do serviço.');
  return data as Record<string, unknown>;
}
function strings(data: unknown): string[] {
  if (!Array.isArray(data) || !data.every((value: unknown) => typeof value === 'string')) throw new Error('Resposta inválida do serviço.');
  return data as string[];
}
export function text(data: unknown): string {
  if (typeof data !== 'string') throw new Error('Resposta inválida do serviço.');
  return data;
}
export function decodeStaff(data: unknown): Staff {
  const row = record(data);
  if (typeof row.active !== 'boolean') throw new Error('Resposta inválida do serviço.');
  return { id: text(row.id), name: text(row.name), login_code: text(row.login_code), role: text(row.role), active: row.active, permissions: strings(row.permissions) };
}
export function decodeContext(data: unknown): StaffContext {
  const row = record(data);
  if (row.auth_strength !== 'pin' && row.auth_strength !== 'password') throw new Error('Resposta inválida do serviço.');
  return { staff: decodeStaff(row.staff), company_name: text(row.company_name), unit_id: text(row.unit_id), unit_name: text(row.unit_name), auth_strength: row.auth_strength };
}
export function decodeRoles(data: unknown): Role[] {
  if (!Array.isArray(data)) throw new Error('Resposta inválida do serviço.');
  return data.map((value: unknown) => { const row = record(value); return { id: text(row.id), name: text(row.name), permissions: strings(row.permissions) }; });
}
export function decodeStaffPage(data: unknown): StaffPage {
  const row = record(data);
  if (!Number.isSafeInteger(row.count) || (row.count as number) < 0 || !Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
  const staff = row.results.map(decodeStaff);
  return { count: row.count as number, next: row.next === null ? null : text(row.next), previous: row.previous === null ? null : text(row.previous), results: [...new Map(staff.map(person => [person.id, person])).values()] };
}

export async function request(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<unknown> {
  if (!path.startsWith('/api/v1/')) throw new Error('Endereço de API inválido.');
  const headers: Record<string, string> = {};
  if (method !== 'GET') {
    const token = record(await request('/api/v1/csrf/', 'GET', undefined, signal));
    headers['X-CSRFToken'] = text(token.csrf_token);
    if (!(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  }
  const timeout = AbortSignal.timeout(body instanceof FormData ? 120_000 : 10_000);
  const options: RequestInit = { method, credentials: 'same-origin', cache: 'no-store', headers, signal: signal ? AbortSignal.any([signal, timeout]) : timeout };
  if (body !== undefined) options.body = body instanceof FormData ? body : JSON.stringify(body);
  let response: Response;
  try { response = await fetch(path, options); }
  catch (error: unknown) {
    if (signal?.aborted) throw error;
    throw new Error('Não foi possível conectar. Confira a conexão e tente novamente.');
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: 'Confira os dados informados.', 401: 'Credenciais inválidas ou acesso expirado. Atualize seu acesso.',
      403: 'Ação não autorizada. Atualize a página ou entre com uma credencial adequada.',
      404: 'Registro não encontrado.', 409: 'O registro mudou. Atualize antes de tentar novamente.',
      422: 'Confira os dados informados.', 429: 'Muitas tentativas. Aguarde antes de tentar novamente.',
      413: 'O conteúdo excede o limite de envio. Reduza a seleção ou o arquivo e tente novamente.',
    };
    let message = messages[response.status] ?? 'O serviço está indisponível. Tente novamente.';
    const fields: Record<string, string> = {};
    try {
      const envelope = record(await response.json()); const error = record(envelope.error);
      if (response.status === 409 && typeof error.message === 'string') message = error.message;
      if ([400, 422].includes(response.status) && typeof error.fields === 'object' && error.fields !== null) {
        for (const [key, value] of Object.entries(record(error.fields))) {
          if (Array.isArray(value) && value.every(item => typeof item === 'string')) fields[key] = value.join(' ');
          else if (typeof value === 'string') fields[key] = value;
        }
      }
    } catch { /* A proxy may return HTML; keep the safe HTTP error message. */ }
    if (Object.keys(fields).length) message = Object.values(fields).join(' ');
    throw new ApiError(response.status, message, fields);
  }
  return response.status === 204 ? null : response.json() as Promise<unknown>;
}

export type Point = { id: string; number?: number | null; name: string; type: string; active: boolean; access_enabled: boolean; token_version: number; nfc_enabled: boolean; qr_enabled: boolean; block_new_devices: boolean; menu?: string | null };
export type PublicContext = { device_id: string; point: Point; company_name: string; unit_name: string; expires_at: string; unit_timezone?: string; unit_logo_url?: string | null; leftover_packaging_enabled?: boolean };
export function decodePoint(data: unknown): Point {
  const row = record(data);
  if (typeof row.active !== 'boolean' || typeof row.nfc_enabled !== 'boolean' || typeof row.qr_enabled !== 'boolean' || typeof row.block_new_devices !== 'boolean') throw new Error('Resposta inválida do serviço.');
  if (row.access_enabled !== undefined && typeof row.access_enabled !== 'boolean' || row.token_version !== undefined && (typeof row.token_version !== 'number' || !Number.isSafeInteger(row.token_version) || row.token_version < 1)) throw new Error('Resposta inválida do serviço.');
  if (row.number != null && (typeof row.number !== 'number' || !Number.isSafeInteger(row.number) || row.number < 1 || row.number > 999999)) throw new Error('Número de ponto inválido.');
  return { id: text(row.id), ...(typeof row.number === 'number' || row.number === null ? { number: row.number } : {}), name: text(row.name), type: text(row.type), active: row.active, access_enabled: row.access_enabled !== false, token_version: typeof row.token_version === 'number' ? row.token_version : 1, nfc_enabled: row.nfc_enabled, qr_enabled: row.qr_enabled, block_new_devices: row.block_new_devices, ...(typeof row.menu === 'string' || row.menu === null ? { menu: row.menu } : {}) };
}
export function decodePublicContext(data: unknown): PublicContext {
  const row = record(data);
  if (row.unit_logo_url != null && (typeof row.unit_logo_url !== 'string' || !/^\/api\/v1\/public\/unit-logo\/image\/\?v=[0-9a-f]{16}$/.test(row.unit_logo_url))) throw new Error('Resposta inválida do serviço.');
  if (row.leftover_packaging_enabled !== undefined && typeof row.leftover_packaging_enabled !== 'boolean') throw new Error('Configuração inválida.');
  return { leftover_packaging_enabled: row.leftover_packaging_enabled === true, device_id: text(row.device_id), point: decodePoint(row.point), company_name: text(row.company_name), unit_name: text(row.unit_name), expires_at: text(row.expires_at), unit_logo_url: row.unit_logo_url == null ? null : text(row.unit_logo_url), ...(typeof row.unit_timezone === 'string' ? { unit_timezone: row.unit_timezone } : {}) };
}

let pendingExchange: { token: string; promise: Promise<PublicContext> } | null = null;
export function exchangePoint(token: string): Promise<PublicContext> {
  if (pendingExchange?.token === token) return pendingExchange.promise;
  const promise = request('/api/v1/public/access/', 'POST', { public_token: token }).then(decodePublicContext);
  pendingExchange = { token, promise };
  // Consume only the derived cleanup rejection; the original promise still reports the error to its caller.
  void promise.finally(() => { if (pendingExchange?.promise === promise) pendingExchange = null; }).catch(() => {});
  return promise;
}

export function decodeRefresh(value: unknown): { event_id: string | null; kind: string } {
  const row = record(value);
  if (row.type !== 'refresh' || (row.event_id !== null && (typeof row.event_id !== 'string' || !/^\d{1,20}$/.test(row.event_id))) || typeof row.kind !== 'string' || !/^[A-Z_]{1,40}$/.test(row.kind)) throw new Error('Mensagem de atualização inválida.');
  return { event_id: row.event_id as string | null, kind: row.kind };
}
