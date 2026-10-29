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
  const [editing, setEditing] = useState(false);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [error, setError] = useState(''), [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false), [reload, setReload] = useState(0);
  const [pending, setPending] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void request('/api/v1/admin/order-policy/', 'GET', undefined, controller.signal).then(decodePolicy).then(value => { if (!controller.signal.aborted) { setPolicy(value); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível consultar a configuração.'); });
    return () => controller.abort();
  }, [reload]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving.current || policy === null) return; saving.current = true;
    const values = new FormData(event.currentTarget);
    const body = pending ?? { idempotency_key: randomUUID(), expected_window_minutes: policy.customer_edit_window_minutes, customer_edit_window_minutes: Number(values.get('minutes')), expected_settings: { table_takeaway_enabled: policy.table_takeaway_enabled, leftover_packaging_enabled: policy.leftover_packaging_enabled, menu_layout: policy.menu_layout }, table_takeaway_enabled: values.has('takeaway'), leftover_packaging_enabled: values.has('packaging'), menu_layout: values.get('layout'), reason: values.get('reason') };
    const wasPending = pending !== null; setPending(body); setBusy(true); setError(''); setMessage('');
    try { setPolicy(decodePolicy(await request('/api/v1/admin/order-policy/', 'PUT', body))); setPending(null); setMessage('Alterações salvas.'); setEditing(false); }
    catch (cause: unknown) { if (!wasPending && cause instanceof ApiError && cause.status >= 400 && cause.status < 500) { setPending(null); if (cause.status === 409) { setEditing(false); setReload(value => value + 1); } } setError(cause instanceof Error ? cause.message : 'Não foi possível salvar.'); }
    finally { saving.current = false; setBusy(false); }
  }
  return <><UnitBranding /><section><PageHeader title="Configurações de pedidos" description="Políticas da unidade para correções, consumo para levar e embalagem." />{error && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} /><button className="secondary" disabled={busy || pending !== null} onClick={() => setReload(value => value + 1)}>Consultar configuração atual</button>{policy && <><p>Janela de correções: {policy.customer_edit_window_minutes} minutos.</p><p>Para levar: {policy.table_takeaway_enabled ? 'Ativado' : 'Desativado'} · Embalagem de sobras: {policy.leftover_packaging_enabled ? 'Ativada' : 'Desativada'}</p><p>Sem taxa adicional. Retirada pública ainda indisponível.</p><button className="secondary" onClick={() => setEditing(true)}>Editar configuração</button></>}{!policy ? !error && <LoadingSkeleton variant="settings" /> : editing && <Editor title="Editar configuração de pedidos" close={() => setEditing(false)} busy={busy}><form onSubmit={event => { void submit(event); }}><fieldset disabled={busy || pending !== null}><label>Janela de correções em minutos<input name="minutes" type="number" min={0} max={60} required defaultValue={policy.customer_edit_window_minutes} /></label><label className="check"><input name="takeaway" type="checkbox" defaultChecked={policy.table_takeaway_enabled} />Permitir produtos para levar na mesa</label><label className="check"><input name="packaging" type="checkbox" defaultChecked={policy.leftover_packaging_enabled} />Permitir solicitar embalagem de sobras</label><label>Apresentação do cardápio<select name="layout" defaultValue={policy.menu_layout}><option value="EDITORIAL">Editorial</option><option value="COMPACT">Compacto</option></select></label><label>Motivo<input name="reason" maxLength={300} /></label></fieldset><div className="dialog-actions"><button className="secondary" type="button" disabled={busy} onClick={() => setEditing(false)}>Voltar</button><button disabled={busy}>{busy ? 'Salvando…' : pending ? 'Repetir os mesmos dados' : 'Salvar alterações'}</button></div></form></Editor>}</section></>;
}
