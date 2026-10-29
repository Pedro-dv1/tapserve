import { randomUUID } from '../../lib/uuid.ts';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, decodePoint, record, request, text } from '../../lib/api';
import type { Point } from '../../lib/api';

import { ResourceSelect } from './CatalogManagement';
import { Editor, PageHeader, Pagination, StatusTag } from './StaffUI';
import { EmptyState, LoadingSkeleton } from '../../components/Interface';
import Toast from '../../components/Toast';
import PointIdentifiers from './PointIdentifiers';

export default function PointManagement() {
  const saving = useRef(false);
  const [access, setAccess] = useState(false);
  const [type, setType] = useState('TABLE');
  const [confirmation, setConfirmation] = useState<Record<string, unknown> | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState<Point | null>(null);
  const [url, setUrl] = useState('');
  const [connected, setConnected] = useState<number | null>(null);
  const [presenceError, setPresenceError] = useState('');
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(query); setPage(1); }, 250); return () => window.clearTimeout(timer); }, [query]);
  const key = useRef(randomUUID());
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    void request(`/api/v1/admin/service-points/?page=${page}&search=${encodeURIComponent(search)}${activeFilter ? `&active=${activeFilter}` : ''}`, 'GET', undefined, controller.signal).then(record).then(row => {
      if (!Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
      setPoints(row.results.map(decodePoint)); setNext(typeof row.next === 'string');
    }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar.'); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, reload, search, activeFilter]);
  useEffect(() => {
    if (!selected || !access) return;
    const controller = new AbortController(); const id = selected.id; let inFlight = false;
    setUrl(''); setConnected(null);
    void request(`/api/v1/admin/service-points/${id}/url/`, 'GET', undefined, controller.signal).then(record).then(row => { if (!controller.signal.aborted) setUrl(text(row.url)); }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Link indisponível.'); });
    async function presence() {
      if (inFlight) return; inFlight = true;
      try { const row = record(await request(`/api/v1/admin/service-points/${id}/presence/`, 'GET', undefined, controller.signal)); if (typeof row.connected_devices !== 'number' || !Number.isSafeInteger(row.connected_devices) || row.connected_devices < 0) throw new Error('Resposta de presença inválida.'); if (!controller.signal.aborted) { setConnected(row.connected_devices); setPresenceError(''); } }
      catch { if (!controller.signal.aborted) { setConnected(null); setPresenceError('Presença indisponível. Tentaremos atualizar novamente.'); } }
      finally { inFlight = false; }
    }
    void presence(); const timer = window.setInterval(() => { void presence(); }, 10_000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [selected?.id, selected?.token_version, access]);
  async function inspect(point: Point) {
    if (busy) return;
    setCreating(false); setAccess(false); setConfirmation(null); setError(''); setMessage(''); setSelected(point);
  }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving.current) return;
    saving.current = true;
    const form = event.currentTarget; const data = new FormData(form); setBusy(true); setError(''); setMessage('');
    try { decodePoint(await request('/api/v1/admin/service-points/', 'POST', { ...(data.get('number') ? { number: Number(data.get('number')) } : {}), name: data.get('name'), menu: data.get('menu'), type: data.get('type'), nfc_enabled: data.get('nfc') === 'on', qr_enabled: data.get('qr') === 'on', idempotency_key: key.current })); key.current = randomUUID(); form.reset(); setCreating(false); setReload(value => value + 1); setMessage('Ponto cadastrado.'); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível cadastrar.'); }
    finally { saving.current = false; setBusy(false); }
  }
  async function change(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected || busy) return;
    const data = new FormData(event.currentTarget);
    const body = { ...(data.get('number') ? { number: Number(data.get('number')) } : {}), name: data.get('name'), active: data.get('active') === 'on', access_enabled: data.get('access_enabled') === 'on', nfc_enabled: data.get('nfc') === 'on', qr_enabled: data.get('qr') === 'on', ...(data.get('menu') ? { menu: data.get('menu') } : {}), block_new_devices: data.get('block') === 'on', reason: data.get('reason') };
    if (selected.active && !body.active || selected.access_enabled && !body.access_enabled) { setConfirmation(body); return; }
    await applyChange(body);
  }
  async function applyChange(body: Record<string, unknown>) {
    if (!selected || saving.current) return;
    saving.current = true; setBusy(true); setError('');
    try { decodePoint(await request(`/api/v1/admin/service-points/${selected.id}/`, 'PATCH', body)); setReload(value => value + 1); setMessage('Alterações salvas.'); setSelected(null); setConfirmation(null); }
    catch (cause: unknown) { setError(cause instanceof ApiError && Object.keys(cause.fields).length ? Object.values(cause.fields).join(' ') : cause instanceof Error ? cause.message : 'Não foi possível atualizar.'); }
    finally { saving.current = false; setBusy(false); }
  }

  return <section><PageHeader title="Pontos de atendimento" description="Mesas, balcões e retiradas. Gerencie os links e os acessos dos clientes." action={<button disabled={busy} onClick={() => { setSelected(null); setType('TABLE'); setCreating(true); setError(''); }}>Cadastrar ponto</button>} />{error && !selected && !creating && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} />
    <div className="staff-toolbar"><label className="staff-search">Buscar ponto<input type="search" value={query} maxLength={100} placeholder="Nome do ponto" onChange={event => setQuery(event.target.value)} /></label><label>Situação<select value={activeFilter} onChange={event => { setActiveFilter(event.target.value); setPage(1); }}><option value="">Todos</option><option value="true">Ativos</option><option value="false">Desativados</option></select></label><button className="secondary" disabled={busy || loading} onClick={() => { setError(''); setReload(value => value + 1); }}>Atualizar lista</button></div>
    <div className="staff-data">{loading ? <LoadingSkeleton variant="points" /> : error && points.length === 0 ? null : points.length === 0 ? <EmptyState title="Nenhum ponto encontrado">Revise a busca ou cadastre um ponto de atendimento.</EmptyState> : <ul className="staff-list">{points.map(point => <li key={point.id}><div><div className="staff-row-title"><strong>{point.type === 'TABLE' && point.number ? `Mesa ${String(point.number).padStart(2, '0')}` : point.name}{point.number && point.name ? ` · ${point.name}` : ''}</strong><StatusTag>{point.active ? 'Ativo' : 'Desativado'}</StatusTag>{point.block_new_devices && <StatusTag attention>Acesso bloqueado</StatusTag>}</div><p>{{ TABLE: 'Mesa', COUNTER: 'Balcão', PICKUP: 'Retirada', OTHER: 'Outro' }[point.type] ?? 'Ponto'} · {point.qr_enabled ? 'QR habilitado' : 'QR desabilitado'} · {point.nfc_enabled ? 'NFC habilitado' : 'NFC desabilitado'}</p></div><button className="secondary" disabled={busy} onClick={() => { void inspect(point); }}>Editar</button></li>)}</ul>}</div>
    <Pagination page={page} next={next} busy={busy || loading} label="Pontos de atendimento" change={setPage} />
    {creating && <Editor title="Cadastrar ponto" close={() => setCreating(false)} busy={busy}>{error && <p className="error" role="alert">{error}</p>}<form className="staff-form-grid" onSubmit={event => { void create(event); }} onChange={() => { key.current = randomUUID(); }}><label>Número da mesa<input name="number" type="number" min={1} max={999999} step={1} required={type === 'TABLE'} disabled={busy} /></label><label>Nome (opcional para mesas)<input name="name" required={type !== 'TABLE'} maxLength={100} disabled={busy} /></label><label>Tipo<select name="type" value={type} onChange={event => setType(event.target.value)} disabled={busy}><option value="TABLE">Mesa</option><option value="COUNTER">Balcão</option><option value="PICKUP">Retirada</option><option value="OTHER">Outro</option></select></label><ResourceSelect name="menu" label="Cardápio deste ponto" kind="service-points/menu-options" initial="" disabled={busy} /><label className="check"><input name="nfc" type="checkbox" disabled={busy} defaultChecked />Habilitar NFC</label><label className="check"><input name="qr" type="checkbox" disabled={busy} defaultChecked />Habilitar QR</label><button disabled={busy} type="submit">{busy ? 'Cadastrando…' : 'Cadastrar ponto'}</button><button className="secondary" type="button" disabled={busy} onClick={() => setCreating(false)}>Cancelar</button></form></Editor>}
    {selected && <Editor title={access ? 'QR Code e NFC' : 'Editar ponto de atendimento'} close={() => setSelected(null)} busy={busy}>{error && <p className="error" role="alert">{error}</p>}{access && url && <PointIdentifiers point={selected} url={url} changed={point => { setSelected(current => current?.id === point.id ? point : current); setReload(value => value + 1); }} />}
      <button type="button" className="secondary" disabled={busy} onClick={() => setAccess(value => !value)}>{access ? 'Voltar aos dados da mesa' : 'QR Code e NFC'}</button>
      <form key={selected.id} onSubmit={event => { void change(event); }}><div hidden={access}><label>Número<input name="number" type="number" required={selected.type === 'TABLE'} min={1} max={999999} step={1} defaultValue={selected.number ?? ''} disabled={busy} /></label><label>Nome (opcional para mesas)<input name="name" maxLength={100} defaultValue={selected.name} disabled={busy} /></label><ResourceSelect name="menu" label="Cardápio deste ponto" kind="service-points/menu-options" initial={selected.menu ?? ''} disabled={busy} required={false} /></div><label className="check"><input name="active" type="checkbox" disabled={busy} defaultChecked={selected.active} />Ponto ativo</label><div hidden={!access}><label className="check"><input name="access_enabled" type="checkbox" disabled={busy} defaultChecked={selected.access_enabled} />Link de QR Code/NFC ativo</label><label className="check"><input name="qr" type="checkbox" disabled={busy} defaultChecked={selected.qr_enabled} />Habilitar QR Code</label><label className="check"><input name="nfc" type="checkbox" disabled={busy} defaultChecked={selected.nfc_enabled} />Habilitar NFC</label><label className="check"><input name="block" type="checkbox" disabled={busy} defaultChecked={selected.block_new_devices} />Bloquear novos dispositivos</label></div><label>Motivo (opcional)<input name="reason" disabled={busy} maxLength={300} /></label><button disabled={busy} type="submit">{busy ? 'Atualizando…' : 'Salvar alterações'}</button><button className="secondary" type="button" disabled={busy} onClick={() => setSelected(null)}>Cancelar</button></form>
      {access && <><p className="point-presence" role="status">Dispositivos conectados: {connected === null ? 'indisponível' : connected}</p>{presenceError && <p role="status">{presenceError}</p>}<p>Conexões em tempo real do atendimento atual, atualizadas a cada 10 segundos. Uma conexão perdida pode levar até 30 segundos para sair da contagem. Navegadores usando apenas atualização periódica não entram neste contador.</p></>}
      {confirmation && <div className="discard-changes" role="alert"><p>Confirmar a desativação? Novos acessos serão bloqueados; ao desativar o ponto, os dispositivos autorizados também serão revogados. O histórico permanece preservado.</p><div className="actions"><button type="button" className="secondary" disabled={busy} onClick={() => setConfirmation(null)}>Voltar</button><button type="button" className="ui-danger" disabled={busy} onClick={() => { void applyChange(confirmation); }}>Confirmar desativação</button></div></div>}
    </Editor>}
  </section>;
}
