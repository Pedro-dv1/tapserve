import { useAutoRefresh } from '../../lib/useAutoRefresh';
import { formSaveResult, requestEditorClose } from '../../lib/formChanges';
import Toast from '../../components/Toast';
import { randomUUID } from '../../lib/uuid.ts';
import { LoadingSkeleton } from '../../components/Interface';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, record, request } from '../../lib/api';

import { Editor, PageHeader } from './StaffUI';
import UnitBranding from './UnitBranding';

type Policy = { customer_edit_window_minutes: number; table_takeaway_enabled: boolean; leftover_packaging_enabled: boolean; menu_layout: 'EDITORIAL' | 'COMPACT' };
export function decodePolicy(value: unknown): Policy {
  const row = record(value);
  if (typeof row.customer_edit_window_minutes !== 'number' || !Number.isInteger(row.customer_edit_window_minutes) || row.customer_edit_window_minutes < 0 || row.customer_edit_window_minutes > 60 || typeof row.table_takeaway_enabled !== 'boolean' || typeof row.leftover_packaging_enabled !== 'boolean' || (row.menu_layout !== 'EDITORIAL' && row.menu_layout !== 'COMPACT')) throw new Error('Configuração inválida.');
  return { customer_edit_window_minutes: row.customer_edit_window_minutes, table_takeaway_enabled: row.table_takeaway_enabled, leftover_packaging_enabled: row.leftover_packaging_enabled, menu_layout: row.menu_layout };
}
export default function OrderPolicy() {
  const saving = useRef(false);
  const expectedPolicy = useRef<Policy | null>(null);
  const [editing, setEditing] = useState<Policy | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [error, setError] = useState(''), [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false), [reload, setReload] = useState(0);
  useAutoRefresh(() => setReload(value => value + 1), editing === null);
  const [conflict, setConflict] = useState(false);
  const [latest, setLatest] = useState<Policy | null>(null);
  const alert = useRef<HTMLParagraphElement>(null);
  useEffect(() => { if (editing && error) alert.current?.focus(); }, [editing, error]);
  const [pending, setPending] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void request('/api/v1/admin/order-policy/', 'GET', undefined, controller.signal).then(decodePolicy).then(value => { if (!controller.signal.aborted) { setPolicy(value); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível consultar a configuração.'); });
    return () => controller.abort();
  }, [reload]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving.current || editing === null || conflict) return; saving.current = true;
    const form = event.currentTarget; const values = new FormData(form);
    const expected = expectedPolicy.current ?? editing;
    const body = pending ?? { idempotency_key: randomUUID(), expected_window_minutes: expected.customer_edit_window_minutes, customer_edit_window_minutes: Number(values.get('minutes')), expected_settings: { table_takeaway_enabled: expected.table_takeaway_enabled, leftover_packaging_enabled: expected.leftover_packaging_enabled, menu_layout: expected.menu_layout }, table_takeaway_enabled: values.has('takeaway'), leftover_packaging_enabled: values.has('packaging'), menu_layout: values.get('layout'), reason: values.get('reason') };
    const wasPending = pending !== null; setPending(body); setBusy(true); setError(''); setMessage('');
    try { setPolicy(decodePolicy(await request('/api/v1/admin/order-policy/', 'PUT', body))); setPending(null); formSaveResult(form, true); setMessage('Configurações salvas com sucesso.'); setEditing(null); }
    catch (cause: unknown) { formSaveResult(form, false); if (cause instanceof ApiError && cause.status === 409) { setConflict(true); setLatest(null); } if (!wasPending && cause instanceof ApiError && cause.status >= 400 && cause.status < 500) { setPending(null); } setError(cause instanceof Error ? cause.message : 'Não foi possível salvar.'); }
    finally { saving.current = false; setBusy(false); }
  }
  async function reviewConflict() {
    if (saving.current) return; saving.current = true; setBusy(true);
    try { setLatest(decodePolicy(await request('/api/v1/admin/order-policy/'))); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível consultar a configuração atual.'); }
    finally { saving.current = false; setBusy(false); }
  }
  return <><UnitBranding /><section><PageHeader title="Configurações de pedidos" description="Políticas da unidade para correções, consumo para levar e embalagem." />{error && !editing && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} />{policy && <><p>Janela de correções: {policy.customer_edit_window_minutes} minutos.</p><p>Para levar: {policy.table_takeaway_enabled ? 'Ativado' : 'Desativado'} · Embalagem de sobras: {policy.leftover_packaging_enabled ? 'Ativada' : 'Desativada'}</p><p>Sem taxa adicional. Retirada pública ainda indisponível.</p><button className="secondary" onClick={() => { setError(''); setConflict(false); setLatest(null); expectedPolicy.current = policy; setEditing(policy); }}>Editar configuração</button></>}{!policy ? !error && <LoadingSkeleton variant="settings" /> : editing && <Editor title="Editar configuração de pedidos" close={() => setEditing(null)} busy={busy}>{error && <p ref={alert} tabIndex={-1} className="error" role="alert">{error}</p>}{conflict && <div className="discard-changes"><p>Seu rascunho foi mantido. Confira a versão atual antes de tentar salvar novamente.</p>{latest ? <><p>Configuração atual: {latest.customer_edit_window_minutes} minutos; para levar: {latest.table_takeaway_enabled ? 'ativado' : 'desativado'}; embalagem: {latest.leftover_packaging_enabled ? 'ativada' : 'desativada'}; cardápio: {latest.menu_layout === 'EDITORIAL' ? 'Editorial' : 'Compacto'}.</p><button type="button" disabled={busy} onClick={() => { setPolicy(latest); expectedPolicy.current = latest; setPending(null); setConflict(false); setError(''); }}>Usar esta versão como referência e manter rascunho</button></> : <button type="button" disabled={busy} onClick={() => { void reviewConflict(); }}>Conferir configuração atual</button>}</div>}<form onSubmit={event => { void submit(event); }}><fieldset disabled={busy || pending !== null}><label>Janela de correções em minutos<input name="minutes" type="number" min={0} max={60} required defaultValue={editing.customer_edit_window_minutes} /></label><label className="check"><input name="takeaway" type="checkbox" defaultChecked={editing.table_takeaway_enabled} />Permitir produtos para levar na mesa</label><label className="check"><input name="packaging" type="checkbox" defaultChecked={editing.leftover_packaging_enabled} />Permitir solicitar embalagem de sobras</label><label>Apresentação do cardápio<select name="layout" defaultValue={editing.menu_layout}><option value="EDITORIAL">Editorial</option><option value="COMPACT">Compacto</option></select></label><label>Motivo<input name="reason" maxLength={300} /></label></fieldset><div className="dialog-actions"><button className="secondary" type="button" disabled={busy} onClick={requestEditorClose}>Voltar</button><button disabled={busy || conflict}>{busy ? 'Salvando…' : pending ? 'Repetir os mesmos dados' : 'Salvar alterações'}</button></div></form></Editor>}</section></>;
}
