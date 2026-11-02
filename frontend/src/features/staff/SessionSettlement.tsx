import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { ApiError, record, request, text } from '../../lib/api';
import type { StaffContext } from '../../lib/api';
import { randomUUID } from '../../lib/uuid';
import ConfirmDialog from '../../components/ConfirmDialog';
import { ErrorState, LoadingSkeleton } from '../../components/Interface';
import { Pagination } from './StaffUI';

type Receipt = { id: string; method: string; amount: string; notes: string; staff_name: string; created_at: string; reverses_id: string | null };
type Lifecycle = { id: string; action: string; reason: string; staff_name: string; created_at: string; consumption_total: string; declared_received: string };
type Settlement = { id: string; status: string; version: number; consumption_total: string; declared_received: string; remaining: string; outstanding_items: number; pending_calls: number; receipts: Receipt[]; lifecycle: Lifecycle[]; declaration_notice: string };
type Action = 'RECEIPT' | 'REVERSE' | 'CLOSE' | 'REOPEN';
type Pending = { action: Action; path: string; body: Record<string, unknown> };
const methods: Record<string, string> = { MONEY: 'Dinheiro', PIX: 'Pix externo', CARD: 'Cartão externo', OTHER: 'Outro' };

function money(value: unknown, signed = false): string {
  const result = text(value);
  if (!(signed ? /^-?\d{1,14}\.\d{2}$/ : /^\d{1,14}\.\d{2}$/).test(result)) throw new Error('Valor operacional inválido.');
  return result;
}
export function displaySettlementMoney(value: string) {
  const [whole, fraction] = money(value, true).replace('-', '').split('.');
  const formatted = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).formatToParts(BigInt(whole!)).map(part => part.type === 'fraction' ? fraction : part.value).join('');
  return value.startsWith('-') ? `−${formatted}` : formatted;
}
const displayMoney = displaySettlementMoney;

export function decodeSettlement(value: unknown): Settlement {
  const row = record(value);
  for (const field of ['version', 'outstanding_items', 'pending_calls']) {
    if (!Number.isSafeInteger(row[field]) || (row[field] as number) < (field === 'version' ? 1 : 0)) throw new Error('Resumo operacional inválido.');
  }
  if (!Array.isArray(row.receipts) || !Array.isArray(row.lifecycle)) throw new Error('Histórico operacional inválido.');
  return {
    id: text(row.id), status: text(row.status), version: row.version as number,
    consumption_total: money(row.consumption_total), declared_received: money(row.declared_received), remaining: money(row.remaining, true),
    outstanding_items: row.outstanding_items as number, pending_calls: row.pending_calls as number, declaration_notice: text(row.declaration_notice),
    receipts: row.receipts.map(value => { const r = record(value); const method = text(r.method); if (!Object.hasOwn(methods, method)) throw new Error('Forma declarada inválida.'); return { id: text(r.id), method, amount: money(r.amount), notes: text(r.notes), staff_name: text(r.staff_name), created_at: text(r.created_at), reverses_id: r.reverses_id == null ? null : text(r.reverses_id) }; }),
    lifecycle: row.lifecycle.map(value => { const r = record(value); return { id: text(r.id), action: text(r.action), reason: text(r.reason), staff_name: text(r.staff_name), created_at: text(r.created_at), consumption_total: money(r.consumption_total), declared_received: money(r.declared_received) }; }),
  };
}

export function settlementStorageKey(context: StaffContext, sessionId: string) { return `tapserve:settlement:${context.staff.id}:${context.unit_id}:${sessionId}`; }
export function decodePendingSettlement(value: unknown, sessionId: string): Pending {
  const row = record(value), body = record(row.body), action = text(row.action), path = text(row.path);
  const base = `/api/v1/staff/sessions/${sessionId}/`;
  const suffix = path.startsWith(base) ? path.slice(base.length) : '';
  const matches = action === 'RECEIPT' ? suffix === 'external-receipts/' : action === 'CLOSE' ? suffix === 'close/' : action === 'REOPEN' ? suffix === 'reopen/' : action === 'REVERSE' && /^external-receipts\/[0-9a-f-]{36}\/reverse\/$/i.test(suffix);
  if (!matches || !/^[0-9a-f-]{36}$/i.test(text(body.idempotency_key)) || !Number.isSafeInteger(body.expected_version) || (body.expected_version as number) < 1) throw new Error('Não foi possível recuperar a operação pendente.');
  return { action: action as Action, path, body };
}

export default function SessionSettlement({ sessionId, pointId, context, revision, changed }: { sessionId: string; pointId: string; context: StaffContext; revision: number; changed: () => void }) {
  const storage = settlementStorageKey(context, sessionId);
  const [data, setData] = useState<Settlement | null>(null), [error, setError] = useState(''), [message, setMessage] = useState('');
  const [restored] = useState(() => { try { const raw = sessionStorage.getItem(storage); return { pending: raw ? decodePendingSettlement(JSON.parse(raw), sessionId) : null, error: '' }; } catch { return { pending: null, error: 'Não foi possível recuperar a operação armazenada. Confira o histórico com um responsável antes de registrar outro recebimento neste navegador.' }; } });
  const [pending, setPending] = useState<Pending | null>(restored.pending);
  const [busy, setBusy] = useState(false), [reload, setReload] = useState(0);
  const [confirm, setConfirm] = useState<{ action: 'CLOSE' | 'REOPEN' | 'REVERSE'; receiptId?: string } | null>(null);
  const submitting = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    void request(`/api/v1/staff/sessions/${sessionId}/settlement/`, 'GET', undefined, controller.signal).then(decodeSettlement).then(result => { if (!controller.signal.aborted) { setData(result); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && [401, 403].includes(cause.status)) setData(null); setError(cause instanceof Error ? cause.message : 'Não foi possível conferir o consumo.'); } });
    return () => controller.abort();
  }, [sessionId, revision, reload]);

  function clearPending() { sessionStorage.removeItem(storage); setPending(null); }
  async function send(command: Pending, retry = false) {
    if (submitting.current) return;
    submitting.current = true; setBusy(true); setError(''); setMessage('');
    try {
      // Persist the exact key/payload before transport; an uncertain request must not become a new receipt.
      sessionStorage.setItem(storage, JSON.stringify(command)); setPending(command);
      const result = decodeSettlement(await request(command.path, 'POST', command.body));
      setData(result); clearPending(); setMessage(command.action === 'RECEIPT' ? 'Declaração de recebimento externo registrada.' : command.action === 'REVERSE' ? 'Reversão do registro operacional registrada. Nenhum dinheiro foi movimentado.' : command.action === 'CLOSE' ? 'Atendimento encerrado e mesa liberada.' : 'Continuidade do mesmo atendimento autorizada. Os dispositivos precisam de novo acesso.');
      changed();
    } catch (cause: unknown) {
      if (!retry && cause instanceof ApiError && cause.status >= 400 && cause.status < 500) clearPending();
      setError(cause instanceof Error ? cause.message : 'Não foi possível concluir. Confira a operação pendente antes de tentar uma nova.');
      if (cause instanceof ApiError && cause.status === 409) setReload(value => value + 1);
      throw cause;
    } finally { submitting.current = false; setBusy(false); }
  }

  async function reconcile() {
    if (!pending || submitting.current) return;
    submitting.current = true; setBusy(true); setError('');
    try {
      const result = record(await request(`/api/v1/staff/sessions/${sessionId}/settlement-results/${text(pending.body.idempotency_key)}/?action=${pending.action}`));
      if (result.applied === true) { setData(decodeSettlement(result.result)); clearPending(); setMessage('Operação anterior localizada. Nenhum lançamento foi duplicado.'); changed(); }
      else if (result.applied === false && Number.isSafeInteger(result.version) && (result.version as number) > (pending.body.expected_version as number)) { clearPending(); setReload(value => value + 1); setMessage('A operação não foi aplicada e sua versão já expirou. Confira os dados atuais antes de criar uma nova ação.'); }
      else setError('Resultado ainda não localizado. Repita a mesma operação com os mesmos dados para conferir, sem criar uma nova chave.');
    } catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível conferir a operação.'); }
    finally { submitting.current = false; setBusy(false); }
  }

  async function receive(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!data || pending || busy || restored.error) return;
    const form = event.currentTarget, fields = new FormData(form);
    const command: Pending = { action: 'RECEIPT', path: `/api/v1/staff/sessions/${sessionId}/external-receipts/`, body: { idempotency_key: randomUUID(), expected_version: data.version, point_id: pointId, amount: fields.get('amount'), method: fields.get('method'), reason: fields.get('reason') } };
    try { await send(command); form.reset(); } catch { /* Keep the actual error and uncertain command above. */ }
  }

  const grants = context.staff.permissions, active = data && ['OPEN', 'CHECK_REQUESTED', 'CLOSING', 'REOPENED'].includes(data.status);
  const canManage = context.auth_strength === 'password' && ['OWNER', 'ADMIN', 'MANAGER'].includes(context.staff.role);
  return <section aria-label="Consumo e encerramento">
    <h3>Consumo e recebimentos externos</h3>
    {restored.error && <ErrorState message={restored.error} />}{error && <ErrorState message={error} retry={() => setReload(value => value + 1)} />}{message && <p role="status">{message}</p>}
    {pending && <div role="status"><p>Há uma operação com confirmação pendente. Confira o resultado antes de registrar outra.</p><div className="actions"><button disabled={busy} onClick={() => { void reconcile(); }}>Conferir resultado</button><button className="secondary" disabled={busy} onClick={() => { void send(pending, true).catch(() => {}); }}>Repetir a mesma operação</button></div></div>}
    {data ? <>
      <p>{data.declaration_notice}</p><p>Consumo: <strong>{displayMoney(data.consumption_total)}</strong> · Recebimento declarado: <strong>{displayMoney(data.declared_received)}</strong></p><p>Saldo operacional: <strong>{displayMoney(data.remaining)}</strong></p>
      {data.outstanding_items > 0 && <p role="status">{data.outstanding_items} itens ainda precisam ser entregues ou cancelados antes do encerramento.</p>}
      {data.pending_calls > 0 && <p>{data.pending_calls} chamados pendentes serão encerrados junto com este atendimento.</p>}
      {active && grants.includes('REGISTER_PAYMENT') && <form onSubmit={event => { void receive(event); }} aria-busy={busy}><fieldset disabled={busy || pending !== null || Boolean(restored.error)}><legend>Declarar recebimento realizado fora do TapServe</legend><label>Valor informado como recebido<input name="amount" required type="number" min="0.01" step="0.01" inputMode="decimal" /></label><label>Forma externa declarada<select name="method">{Object.entries(methods).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Observação operacional (opcional)<input name="reason" maxLength={300} /></label><button type="submit">Registrar declaração</button></fieldset></form>}
      {data.receipts.length > 0 && <><h4>Histórico de declarações</h4><ul className="staff-list">{data.receipts.map(receipt => <li key={receipt.id}><div><strong>{receipt.reverses_id ? 'Reversão operacional' : 'Recebimento externo declarado'} · {displayMoney(receipt.amount)}</strong><p>{methods[receipt.method]} · {receipt.staff_name} · {new Date(receipt.created_at).toLocaleString('pt-BR')}</p>{receipt.notes && <p>{receipt.notes}</p>}{!receipt.reverses_id && data.receipts.some(value => value.reverses_id === receipt.id) && <p>Registro revertido; original preservado.</p>}{active && canManage && grants.includes('CORRECT_RECEIPT') && !receipt.reverses_id && !data.receipts.some(value => value.reverses_id === receipt.id) && <button className="secondary" disabled={busy || pending !== null} onClick={() => setConfirm({ action: 'REVERSE', receiptId: receipt.id })}>Reverter registro</button>}</div></li>)}</ul></>}
      <div className="actions">{active && grants.includes('CLOSE_SESSION') && <button disabled={busy || pending !== null || data.outstanding_items > 0 || Number(data.remaining) !== 0} onClick={() => setConfirm({ action: 'CLOSE' })}>Encerrar atendimento e liberar mesa</button>}{data.status === 'CLOSED' && canManage && grants.includes('REOPEN_SESSION') && <button className="secondary" disabled={busy || pending !== null} onClick={() => setConfirm({ action: 'REOPEN' })}>Reabrir o mesmo atendimento</button>}</div>
      {data.lifecycle.length > 0 && <details><summary>Histórico de encerramentos e reaberturas</summary><ul>{data.lifecycle.map(event => <li key={event.id}>{event.action === 'CLOSE' ? 'Encerramento' : 'Reabertura'} · {event.staff_name} · {new Date(event.created_at).toLocaleString('pt-BR')} · Consumo {displayMoney(event.consumption_total)} · Declarado {displayMoney(event.declared_received)}{event.reason && ` · ${event.reason}`}</li>)}</ul></details>}
    </> : !error && <LoadingSkeleton variant="orders" />}
    {confirm && data && <ConfirmDialog title={confirm.action === 'CLOSE' ? 'Encerrar atendimento?' : confirm.action === 'REOPEN' ? 'Continuar o mesmo atendimento?' : 'Reverter declaração?'} description={confirm.action === 'CLOSE' ? 'A mesa será liberada. Os acessos de clientes serão revogados e os chamados pendentes serão encerrados. O histórico será preservado.' : confirm.action === 'REOPEN' ? 'Use somente para continuar o atendimento da mesma clientela. Nenhuma mesa pode ter recebido outro atendimento depois deste fechamento. Os acessos antigos continuam revogados. Informe o motivo.' : 'Esta ação corrige apenas um registro operacional e não devolve nem movimenta dinheiro. O original permanece no histórico. Informe o motivo.'} label={confirm.action === 'CLOSE' ? 'Confirmar encerramento' : confirm.action === 'REOPEN' ? 'Confirmar reabertura' : 'Confirmar reversão do registro'} close={() => setConfirm(null)} confirm={async reason => {
      if (confirm.action !== 'CLOSE' && !reason.trim()) throw new Error('Informe um motivo para esta operação.');
      const suffix = confirm.action === 'REVERSE' ? `external-receipts/${confirm.receiptId}/reverse` : confirm.action.toLowerCase();
      await send({ action: confirm.action, path: `/api/v1/staff/sessions/${sessionId}/${suffix}/`, body: { idempotency_key: randomUUID(), expected_version: data.version, reason } });
    }} />}
  </section>;
}

type HistorySession = { id: string; status: string; version: number; opened_at: string; closed_at: string | null };
export function PointSessionHistory({ pointId, context, revision, changed, renderOrders }: { pointId: string; context: StaffContext; revision: number; changed: () => void; renderOrders: (session: HistorySession) => ReactNode }) {
  const [sessions, setSessions] = useState<HistorySession[] | null>(null), [page, setPage] = useState(1), [next, setNext] = useState(false), [selected, setSelected] = useState<HistorySession | null>(null), [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    void request(`/api/v1/staff/tables/${pointId}/history/?page=${page}`, 'GET', undefined, controller.signal).then(record).then(value => { if (!Array.isArray(value.results)) throw new Error('Histórico inválido.'); const result = value.results.map(value => { const s = record(value); if (!Number.isSafeInteger(s.version)) throw new Error('Histórico inválido.'); return { id: text(s.id), status: text(s.status), version: s.version as number, opened_at: text(s.opened_at), closed_at: s.closed_at == null ? null : text(s.closed_at) }; }); if (!controller.signal.aborted) { setSessions(result); setNext(typeof value.next === 'string'); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) { setSessions(null); setError(cause instanceof Error ? cause.message : 'Não foi possível consultar o histórico.'); } });
    return () => controller.abort();
  }, [pointId, page, revision]);
  return <details><summary>Histórico de atendimentos desta mesa</summary>{error && <ErrorState message={error} />}{sessions ? <>{sessions.length ? <ul className="staff-list">{sessions.map(session => <li key={session.id}><button className="secondary" onClick={() => setSelected(selected?.id === session.id ? null : session)}>{new Date(session.opened_at).toLocaleString('pt-BR')} · {session.status === 'CLOSED' ? 'Encerrado' : 'Em atendimento'}</button></li>)}</ul> : <p>Nenhum atendimento registrado.</p>}<Pagination page={page} next={next} change={setPage} />{selected && <div key={selected.id}><SessionSettlement sessionId={selected.id} pointId={pointId} context={context} revision={revision} changed={changed} />{renderOrders(selected)}</div>}</> : !error && <LoadingSkeleton variant="orders" />}</details>;
}
