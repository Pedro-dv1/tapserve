import { record, request } from '../../lib/api.ts';

// Each authorized workspace owns its cache; nothing survives an access/session change.
export class MenuCache {
  private entries = new Map<string, { at: number; data: Record<string, unknown> }>();

  async get(path: string, revision: string, signal: AbortSignal): Promise<Record<string, unknown>> {
    if (!/^\/api\/v1\/public\/(menu|categories)\/\?/.test(path)) throw new Error('Endereço de cardápio inválido.');
    const key = `${revision}:${path}`;
    const hit = this.entries.get(key);
    if (hit && Date.now() - hit.at < 30_000) return hit.data;
    const data = record(await request(path, 'GET', undefined, signal));
    if (!Array.isArray(data.results)) throw new Error('Resposta inválida do serviço.');
    if (!signal.aborted) {
      this.entries.set(key, { at: Date.now(), data });
      if (this.entries.size > 20) { const first = this.entries.keys().next().value; if (first) this.entries.delete(first); }
    }
    return data;
  }
}
