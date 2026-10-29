import { randomUUID } from '../../lib/uuid.ts';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { LoadingSkeleton } from '../../components/Interface';
import { ApiError, record, request, text } from '../../lib/api';
import type { StaffContext } from '../../lib/api';
import { Button, Icon } from '../../components/Interface';
import { useSuccessToast } from '../../components/Toast';
import ConfirmDialog from '../../components/ConfirmDialog';
import Modal from '../../components/Modal';
import Feedback from '../../components/Feedback';
import ActionPopup from '../../components/ActionPopup';
import type { ActionNotice } from '../../components/ActionPopup';
import { Pagination } from '../staff/StaffUI';

type Call = { created_at: string; id: string; kind: string; message: string; status: 'OPEN' | 'ASSIGNED' | 'RESOLVED' | 'CANCELLED'; point_name: string; assigned_to_id: string | null; assignee_name: string | null; can_customer_cancel: boolean };
const names: Record<string, string> = { ATTENDANT: 'Atendente', CLEANING: 'Limpeza da mesa', CUTLERY: 'Talheres', NAPKIN: 'Guardanapo', OTHER: 'Outro', CHECK: 'Conta', PACKAGING: 'Embalagem de sobras' };
export function decodeCall(value: unknown): Call {
  const row = record(value);
  if (!['OPEN', 'ASSIGNED', 'RESOLVED', 'CANCELLED'].includes(text(row.status)) || typeof row.can_customer_cancel !== 'boolean') throw new Error('Resposta inválida do chamado.');
  return { created_at: row.created_at === undefined ? '' : text(row.created_at), id: text(row.id), kind: text(row.kind), message: text(row.message), status: row.status as Call['status'], point_name: text(row.point_name), assigned_to_id: row.assigned_to_id === null ? null : text(row.assigned_to_id), assignee_name: row.assignee_name === null ? null : text(row.assignee_name), can_customer_cancel: row.can_customer_cancel };
}
export async function loadCalls(realm: 'staff' | 'public', page: number, signal: AbortSignal, filters = '') {
  const results: Call[] = [];
  // ponytail: cap public calls at 10 pages; use incremental loading if a point exceeds it.
  for (let current = realm === 'staff' ? page : 1; current <= (realm === 'staff' ? page : 10); current++) {
    const data = record(await request(`/api/v1/${realm}/service-requests/?page=${current}${filters}`, 'GET', undefined, signal));
    if (!Array.isArray(data.results)) throw new Error('Resposta inválida do serviço.');
    results.push(...data.results.map(decodeCall));
    const next = typeof data.next === 'string';
    if (realm === 'staff' || !next) return { results, next, previous: typeof data.previous === 'string' };
  }
  throw new Error('Não foi possível conferir todos os chamados. Tente atualizar.');
}

export default function ServiceRequests({ staff, revision, quick = false, sessionStatus = null, unavailable = false, view = 'table', packagingEnabled = false, changed }: { staff?: StaffContext; revision: number; quick?: boolean; sessionStatus?: string | null; unavailable?: boolean; view?: string; packagingEnabled?: boolean; changed?: () => void }) {
  const [statusFilter, setStatusFilter] = useState('PENDING');
  const [kindFilter, setKindFilter] = useState('');
  const pointFilter = staff ? new URLSearchParams(window.location.search).get('point') : null;
  const [calls, setCalls] = useState<Call[] | null>(null);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [previous, setPrevious] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState('');
  const realm = staff ? 'staff' : 'public';
  useEffect(() => {
    const controller = new AbortController(); let inFlight = false;
    async function load() {
      if (inFlight) return;
      inFlight = true; setLoading(true);
      try {
        const data = await loadCalls(realm, page, controller.signal, staff ? `&status=${statusFilter}${kindFilter ? `&kind=${kindFilter}` : ''}${pointFilter ? `&point=${encodeURIComponent(pointFilter)}` : ''}` : '');
        if (!controller.signal.aborted) { setCalls(data.results); setNext(data.next); setPrevious(data.previous); setError(''); }
      }
      catch (cause: unknown) { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) { setPage(1); return; } setError(cause instanceof Error ? cause.message : 'Não foi possível carregar chamados.'); if (cause instanceof ApiError && [401, 403].includes(cause.status)) setCalls(null); } }
      finally { inFlight = false; if (!controller.signal.aborted) setLoading(false); }
    }
    void load(); const timer = window.setInterval(() => { void load(); }, 10_000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [realm, page, reload, revision, statusFilter, kindFilter, pointFilter, staff]);
  const refresh = (call?: Call) => { if (call && ['OPEN', 'ASSIGNED'].includes(call.status)) setCalls(values => [...(values ?? []).filter(value => value.id !== call.id), call]); setReload(value => value + 1); changed?.(); };
  const newRequest = <NewRequest packagingEnabled={packagingEnabled && Boolean(sessionStatus)} view={view} quick={quick} changed={refresh} sessionStatus={sessionStatus} disabled={unavailable || calls === null || Boolean(error)} activeKinds={calls?.map(call => call.kind) ?? []} />;
  return <section className={staff ? 'staff-calls' : quick ? 'home-service-actions' : 'table-card service-requests'} aria-label={quick ? 'Atendimento' : undefined}>
    {staff ? <div className="staff-toolbar"><label>Estado<select value={statusFilter} onChange={event => { setStatusFilter(event.target.value); setPage(1); }}><option value="PENDING">Pendentes</option><option value="OPEN">Aguardando</option><option value="ASSIGNED">Assumidos</option><option value="RESOLVED">Resolvidos</option><option value="CANCELLED">Cancelados</option><option value="ALL">Histórico completo</option></select></label><label>Tipo<select value={kindFilter} onChange={event => { setKindFilter(event.target.value); setPage(1); }}><option value="">Todos</option>{Object.entries(names).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>{pointFilter && <a href="/staff/calls">Todas as mesas</a>}</div> : quick ? null : <div className="section-heading"><h2><Icon name="message" />Chamar atendimento</h2><button className="plain-action" onClick={() => refresh()}>Atualizar</button></div>}
    {error && (staff ? <p className="error" role="alert">{error}</p> : <Feedback tone="error">{error}<button className="plain-action" onClick={() => refresh()}>Atualizar</button></Feedback>)}{staff && <button className="secondary" onClick={() => refresh()}>Atualizar chamados</button>}{!staff && newRequest}
    {quick ? null : calls === null ? error ? null : <LoadingSkeleton variant="calls" /> : calls.length === 0 ? <p className={staff ? undefined : 'request-empty'}>Nenhum chamado aguardando atendimento.</p> : <ul className={staff ? 'staff-list' : 'request-list'}>{calls.map(call => <li key={call.id}><div><strong>{staff ? `${call.point_name} · ` : ''}{names[call.kind] ?? 'Solicitação'}</strong>{call.message && <p>{call.message}</p>}<p>{call.status === 'OPEN' ? 'Aguardando atendente' : `Atendimento assumido por ${call.assignee_name ?? 'funcionário'}`}</p>{staff && call.status === 'OPEN' ? <CallAction key={call.status} call={call} target="ASSIGNED" manual changed={refresh} /> : staff && call.status === 'ASSIGNED' && call.assigned_to_id === staff.staff.id ? <CallAction key={call.status} call={call} target="RESOLVED" manual changed={refresh} /> : null}{!staff && call.can_customer_cancel && <CallAction key={call.status} call={call} target="CANCELLED" changed={refresh} />}{staff && ['OPEN', 'ASSIGNED'].includes(call.status) && <CallAction key={`${call.status}:cancel`} call={call} target="CANCELLED" manual changed={refresh} />}</div></li>)}</ul>}
    {staff && <Pagination page={page} next={next} previous={previous} busy={loading} label="Chamados" change={setPage} />}
  </section>;
}

function NewRequest({ changed, quick = false, sessionStatus = null, disabled = false, activeKinds = [], view, packagingEnabled }: { changed: (call: Call) => void; quick?: boolean; sessionStatus?: string | null; disabled?: boolean; activeKinds?: string[]; view: string; packagingEnabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('ATTENDANT');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<(ActionNotice & { view: string }) | null>(null);
  const mutation = useRef(false);
  useEffect(() => { setOpen(false); setNotice(null); }, [view]);
  const checkRequested = activeKinds.includes('CHECK') || ['CHECK_REQUESTED', 'CLOSING'].includes(sessionStatus ?? '');
  const canCheck = !checkRequested && ['OPEN', 'REOPENED'].includes(sessionStatus ?? '');
  function confirmed(call: Call) {
    setPending(null); setOpen(false);
    setNotice({ view, title: call.status === 'RESOLVED' ? 'Solicitação já atendida' : call.status === 'CANCELLED' ? 'Solicitação cancelada' : call.kind === 'CHECK' ? 'Conta solicitada' : 'Atendimento solicitado', message: call.status === 'RESOLVED' ? 'A equipe já concluiu esta solicitação.' : call.status === 'CANCELLED' ? 'Esta solicitação foi cancelada.' : call.kind === 'CHECK' ? 'A equipe foi avisada e atenderá sua solicitação.' : 'Seu pedido de atendimento foi enviado à equipe.', tone: ['RESOLVED', 'CANCELLED'].includes(call.status) ? 'info' : 'success' });
    changed(call);
  }
  async function submit(event: FormEvent<HTMLFormElement> | null) {
    event?.preventDefault(); if (mutation.current || disabled) return;
    const data = event ? new FormData(event.currentTarget) : null;
    const body = pending ?? { idempotency_key: randomUUID(), kind: data ? kind : 'CHECK', message: data?.get('message') ?? '' };
    if (!pending && (activeKinds.includes(String(body.kind)) || body.kind === 'CHECK' && checkRequested)) { setOpen(false); setNotice({ view, title: body.kind === 'CHECK' ? 'Conta já solicitada' : 'Atendimento já solicitado', message: 'A equipe já foi avisada. Aguarde o atendimento.', tone: 'info' }); return; }
    if (!pending && body.kind === 'CHECK' && !canCheck) return;
    mutation.current = true;
    const wasPending = pending !== null; setPending(body); setBusy(true); setError('');
    try {
      const call = decodeCall(await request('/api/v1/public/service-requests/', 'POST', body));
      confirmed(call);
    } catch (cause: unknown) {
      if (!wasPending && cause instanceof ApiError && cause.status >= 400 && cause.status < 500) setPending(null);
      setError(cause instanceof ApiError && cause.status === 409 ? cause.message : cause instanceof ApiError && cause.status === 400 ? Object.values(cause.fields).join(' ') || 'Confira a solicitação e a mensagem.' : cause instanceof ApiError && [401, 403].includes(cause.status) ? 'Esta ação não está disponível no momento. Atualize seu acesso à mesa.' : cause instanceof Error ? cause.message : 'Não foi possível confirmar. Confira os chamados antes de repetir.');
    } finally { mutation.current = false; setBusy(false); }
  }
  async function verify() {
    if (!pending || mutation.current) return; mutation.current = true; setBusy(true); setError('');
    try { const call = decodeCall(await request(`/api/v1/public/service-request-receipts/${text(pending.idempotency_key)}/`)); confirmed(call); }
    catch (cause: unknown) { setError(cause instanceof ApiError && cause.status === 404 ? 'A confirmação ainda não foi localizada. Aguarde ou repita com os mesmos dados.' : cause instanceof Error ? cause.message : 'Não foi possível verificar.'); }
    finally { mutation.current = false; setBusy(false); }
  }
  const feedback = <>{busy && <Feedback tone="processing">Estamos processando sua solicitação.</Feedback>}{error && <Feedback tone="error">{error}</Feedback>}{pending && !busy && <Feedback tone="warning">A confirmação está pendente. Consulte antes de repetir.</Feedback>}</>;
  const receipt = pending && <Button type="button" secondary disabled={busy} onClick={() => { void verify(); }}>Consultar confirmação</Button>;
  return <><div className={quick ? 'home-secondary-actions' : 'request-actions'}><Button secondary type="button" disabled={disabled || busy || pending?.kind === 'CHECK'} onClick={() => { setError(''); setOpen(true); }}><Icon name="message" />{quick ? 'Chamar garçom' : 'Chamar atendimento'}</Button>{quick && <Button secondary type="button" disabled={disabled || busy || !canCheck && !checkRequested && !pending || pending !== null && pending.kind !== 'CHECK'} onClick={() => { void submit(null); }}><Icon name="receipt" />Pedir a conta</Button>}</div>
    {!open && feedback}{!open && receipt}<ActionPopup notice={notice?.view === view ? notice : null} close={() => setNotice(null)} />
    {quick && !sessionStatus ? <Feedback>A conta fica disponível após o primeiro pedido.</Feedback> : quick && !canCheck && !checkRequested ? <Feedback tone="warning">Esta ação não está disponível no momento.</Feedback> : null}
    <Modal open={open} title="Chamar atendimento" description="Escolha como podemos ajudar sua mesa." busy={busy} close={() => setOpen(false)}><form className="request-form" onSubmit={event => { void submit(event); }} aria-busy={busy}><fieldset disabled={busy || pending !== null}><legend className="sr-only">Solicitação de atendimento</legend><label>Solicitação<select name="kind" value={kind} onChange={event => { setKind(event.target.value); setError(''); }}>{Object.entries(names).filter(([value]) => value !== 'CHECK' && (value !== 'PACKAGING' || packagingEnabled)).map(([value, name]) => <option value={value} key={value} disabled={activeKinds.includes(value)}>{name}{activeKinds.includes(value) ? ' — em andamento' : ''}</option>)}</select></label><label>Mensagem{kind === 'OTHER' ? ' (obrigatória)' : ' (opcional)'}<textarea name="message" required={kind === 'OTHER'} maxLength={300} placeholder="Como podemos ajudar?" rows={3} /></label></fieldset>{activeKinds.includes(kind) && !pending && <Feedback>Já existe uma solicitação deste tipo em andamento. A equipe foi notificada.</Feedback>}{feedback}<div className="dialog-actions"><Button secondary type="button" disabled={busy} onClick={() => setOpen(false)}>Cancelar</Button><Button type="submit" disabled={disabled || busy || !pending && activeKinds.includes(kind)}>{busy ? 'Enviando…' : pending ? 'Repetir o mesmo chamado' : 'Chamar atendente'}</Button></div>{receipt}</form></Modal>
  </>;
}

function CallAction({ call, target, manual = false, changed }: { call: Call; target: string; manual?: boolean; changed: () => void }) {
  const notify = useSuccessToast();
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const cancellation = useRef<Record<string, unknown> | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const values = new FormData(event.currentTarget);
    const body = pending ?? { idempotency_key: randomUUID(), expected_status: call.status, ...(manual ? { status: target, reason: String(values.get('reason') ?? '') } : {}) };
    setPending(body); setBusy(true); setError('');
    try { decodeCall(await request(`/api/v1/${manual ? 'staff' : 'public'}/service-requests/${call.id}/${manual ? 'status' : 'cancel'}/`, 'POST', body)); setConfirmed(true); notify?.('Alterações salvas.'); changed(); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível atualizar.'); }
    finally { setBusy(false); }
  }
  if (target === 'CANCELLED') return <><button className="ui-danger" disabled={busy || confirmed} type="button" onClick={() => setCancelling(true)}>Cancelar chamado</button>{cancelling && <ConfirmDialog title="Cancelar chamado?" description="A solicitação será encerrada e permanecerá no histórico." label="Cancelar chamado" close={() => setCancelling(false)} confirm={async reason => {
    const body = cancellation.current ?? { idempotency_key: randomUUID(), expected_status: call.status, ...(manual ? { status: target, reason } : {}) };
    cancellation.current = body;
    decodeCall(await request(`/api/v1/${manual ? 'staff' : 'public'}/service-requests/${call.id}/${manual ? 'status' : 'cancel'}/`, 'POST', body)); setConfirmed(true); notify?.('Alterações salvas.'); changed();
  }} />}</>;
  return confirmed ? null : <form onSubmit={event => { void submit(event); }}>{error && <p className="error" role="alert">{error} Atualize o chamado ou repita com os mesmos dados.</p>}{manual && target === 'CANCELLED' && <label>Motivo do cancelamento<input name="reason" maxLength={300} disabled={pending !== null} /></label>}<button className="secondary" disabled={busy}>{busy ? 'Atualizando…' : target === 'ASSIGNED' ? 'Assumir chamado' : target === 'RESOLVED' ? 'Resolver chamado' : 'Cancelar chamado'}</button></form>;
}
