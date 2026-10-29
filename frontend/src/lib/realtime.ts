import { ApiError, decodeRefresh, request } from './api';

type Kind = 'public' | 'staff';
type Snapshot = { revision: number; status: string; ordersRevision: number; callsRevision: number; catalogRevision: number };
const connections = new Map<Kind, RealtimeConnection>();
class RealtimeConnection {
  snapshot: Snapshot = { revision: 0, status: '', ordersRevision: 0, callsRevision: 0, catalogRevision: 0 };
  listeners = new Set<() => void>();
  socket: WebSocket | null = null;
  timer = 0; watchdog = 0; disposal = 0; failures = 0; recovery = 0;
  stopped = false; lastMessage = 0; openedAt = 0; outage = 0;
  seen = new Set<string>();
  controller = new AbortController();
  readonly kind: Kind;
  constructor(kind: Kind) { this.kind = kind; }
  update(status = this.snapshot.status, refresh = false, kind = 'SNAPSHOT_REQUIRED') {
    if (!refresh && status === this.snapshot.status) return;
    const callsOnly = ['CALL_ASSIGNED', 'CALL_RESOLVED'].includes(kind);
    this.snapshot = { status, revision: this.snapshot.revision + (refresh ? 1 : 0),
      ordersRevision: this.snapshot.ordersRevision + (refresh && !callsOnly && kind !== 'CATALOG_CHANGED' ? 1 : 0),
      callsRevision: this.snapshot.callsRevision + (refresh && (kind.startsWith('CALL_') || kind === 'SNAPSHOT_REQUIRED') ? 1 : 0),
      catalogRevision: this.snapshot.catalogRevision + (refresh && (['CATALOG_CHANGED', 'ORDER_CREATED', 'ITEM_EDIT', 'ITEM_CANCEL', 'ITEM_STATUS_CHANGED', 'SNAPSHOT_REQUIRED'].includes(kind)) ? 1 : 0) };
    for (const listener of this.listeners) listener();
  }
  resume = () => {
    if (!navigator.onLine || document.visibilityState === 'hidden' || this.stopped) return;
    this.failures = 0; this.connect();
  };
  offline = () => { window.clearTimeout(this.timer); this.socket?.close(); this.update('Sem conexão. Confira os dados antes de continuar.'); };
  connect() {
    if (!this.listeners.size || this.stopped || this.socket && this.socket.readyState < WebSocket.CLOSING) return;
    if (!navigator.onLine) { this.offline(); return; }
    window.clearTimeout(this.timer);
    window.clearInterval(this.watchdog);
    const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/v1/${this.kind}/`);
    this.socket = socket; this.lastMessage = Date.now(); this.openedAt = 0;
    this.watchdog = window.setInterval(() => { if (Date.now() - this.lastMessage > 20_000) socket.close(4000, 'timeout'); }, 5000);
    // The server sends SNAPSHOT_REQUIRED after authentication; opening alone needs no reload.
    socket.onopen = () => { if (this.socket === socket) { this.openedAt = Date.now(); this.outage = 0; this.update(''); } };
    socket.onmessage = event => {
      if (this.socket !== socket || !this.listeners.size) return;
      this.lastMessage = Date.now();
      try {
        if (typeof event.data !== 'string' || event.data.length > 2048) throw new Error('Invalid frame');
        const value: unknown = JSON.parse(event.data);
        if (typeof value === 'object' && value !== null && Object.keys(value).length === 1 && 'type' in value && value.type === 'heartbeat') { socket.send(JSON.stringify({ type: 'heartbeat_ack' })); return; }
        const update = decodeRefresh(value);
        if (update.event_id && this.seen.has(update.event_id)) return;
        if (update.event_id) { this.seen.add(update.event_id); if (this.seen.size > 100) { const first = this.seen.values().next().value; if (first) this.seen.delete(first); } }
        this.update('', true, update.kind);
      } catch { this.update('Falha nas atualizações. Reconectando para conferir os dados.'); socket.close(1002); }
    };
    socket.onclose = event => {
      if (this.socket !== socket) return;
      this.socket = null; window.clearInterval(this.watchdog);
      if (!this.listeners.size || this.stopped) return;
      if ([4400, 4401, 4403].includes(event.code)) { this.stopped = true; this.update('Acesso às atualizações encerrado. Atualize seu acesso.', true); return; }
      if (!navigator.onLine) { this.offline(); return; }
      if (this.openedAt && Date.now() - this.openedAt >= 30_000) this.failures = 0;
      if (!this.outage) this.outage = Date.now();
      void this.retry(event.code);
    };
  }
  async retry(code: number) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    this.controller.signal.addEventListener('abort', abort, { once: true });
    const timeout = window.setTimeout(abort, 5000);
    try { await request(`/api/v1/${this.kind === 'public' ? 'public/context' : 'staff/me'}/`, 'GET', undefined, controller.signal); }
    catch (cause: unknown) {
      if (this.controller.signal.aborted) return;
      if (cause instanceof ApiError && [401, 403].includes(cause.status)) { this.stopped = true; this.update('Seu acesso expirou. Entre novamente ou abra o NFC/QR.', true); return; }
    }
    finally { window.clearTimeout(timeout); this.controller.signal.removeEventListener('abort', abort); }
    if (!this.listeners.size || this.stopped || this.socket) return;
    this.failures++;
    if (this.failures === 1 || this.failures === 6) console.warn('realtime_unavailable', { endpoint: `/ws/v1/${this.kind}/`, close_code: code, attempts: this.failures });
    if (this.failures >= 6) this.update('Atualizações em tempo real indisponíveis. Os dados continuam sendo conferidos automaticamente.');
    if (this.failures < 6 && Date.now() - this.outage >= 10_000) this.update('Atualizações interrompidas. Confira os dados antes de agir.');
    this.timer = window.setTimeout(() => this.connect(), Math.min(30_000, 1000 * 2 ** (this.failures - 1)) * (0.75 + Math.random() * 0.5));
  }
  start() {
    window.addEventListener('online', this.resume); window.addEventListener('offline', this.offline); document.addEventListener('visibilitychange', this.resume); this.connect();
    this.recovery = window.setInterval(() => {
      if (!this.stopped && navigator.onLine && document.visibilityState !== 'hidden' && (!this.socket || Date.now() - this.lastMessage > 20_000)) this.update(this.snapshot.status, true);
    }, 30_000);
  }
  dispose() {
    this.controller.abort(); window.clearTimeout(this.timer); window.clearInterval(this.watchdog); window.clearInterval(this.recovery);
    window.removeEventListener('online', this.resume); window.removeEventListener('offline', this.offline); document.removeEventListener('visibilitychange', this.resume);
    const socket = this.socket; this.socket = null; socket?.close(); connections.delete(this.kind);
  }
}
export function subscribeRealtime(kind: Kind, listener: () => void): () => void {
  let connection = connections.get(kind); const fresh = !connection;
  if (!connection) { connection = new RealtimeConnection(kind); connections.set(kind, connection); }
  window.clearTimeout(connection.disposal); connection.listeners.add(listener);
  if (fresh) connection.start();
  const current = connection;
  return () => { current.listeners.delete(listener); if (!current.listeners.size) current.disposal = window.setTimeout(() => current.dispose(), 100); };
}
const initial: Snapshot = { revision: 0, status: '', ordersRevision: 0, callsRevision: 0, catalogRevision: 0 };
export function realtimeSnapshot(kind: Kind): Snapshot { return connections.get(kind)?.snapshot ?? initial; }
