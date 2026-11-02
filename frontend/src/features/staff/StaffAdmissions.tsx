import { useEffect, useRef, useState } from 'react';
import { record, request, text } from '../../lib/api';
import type { StaffContext } from '../../lib/api';
import { randomUUID } from '../../lib/uuid';
import { useRealtime } from '../../lib/useRealtime';
import { useAutoRefresh } from '../../lib/useAutoRefresh';
import { Pagination } from './StaffUI';

type Pending = { id: string; point_name: string; verification_code: string };
export default function StaffAdmissions({ pointId, context, changed }: { pointId: string; context: StaffContext; changed: () => void }) {
  const [rows, setRows] = useState<Pending[]>([]), [error, setError] = useState('');
  const [reload, setReload] = useState(0), [page, setPage] = useState(1), [next, setNext] = useState(false);
  const [busy, setBusy] = useState(false);
  const commands = useRef(new Map<string, { idempotency_key: string; status: string }>());
  const saving = useRef(false);
  const realtime = useRealtime('staff');
  const allowed = context.staff.permissions.includes('APPROVE_DEVICE_ACCESS');
  useAutoRefresh(() => setReload(value => value + 1), allowed);
  useEffect(() => {
    if (!allowed) return;
    const controller = new AbortController();
    void request(`/api/v1/staff/admissions/?point=${pointId}&page=${page}`, 'GET', undefined, controller.signal).then(record).then(value => {
      if (!Array.isArray(value.results)) throw new Error('Fila de autorizações inválida.');
      setRows(value.results.map(item => { const row = record(item); return { id: text(row.id), point_name: text(row.point_name), verification_code: text(row.verification_code) }; })); setNext(value.next !== null); setError('');
    }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível consultar os acessos.'); });
    return () => controller.abort();
  }, [pointId, page, allowed, reload, realtime.revision]);
  async function decide(row: Pending, status: string) {
    if (saving.current) return;
    const previous = commands.current.get(row.id);
    if (previous && previous.status !== status) { setError('Há uma decisão com resultado incerto. Repita a mesma ação antes de decidir novamente.'); return; }
    const command = previous ?? { idempotency_key: randomUUID(), status };
    commands.current.set(row.id, command); saving.current = true; setBusy(true); setError('');
    try { await request(`/api/v1/staff/admissions/${row.id}/decision/`, 'POST', command); commands.current.delete(row.id); setReload(value => value + 1); changed(); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível registrar a decisão.'); }
    finally { saving.current = false; setBusy(false); }
  }
  if (!allowed) return null;
  return <section aria-label="Autorizar dispositivos"><h4>Acessos aguardando autorização</h4><p>Confira o código no aparelho da pessoa atendida antes de aprovar. Conhecer o link não comprova presença.</p>{error && <p role="alert" className="error">{error}</p>}{rows.length ? <ul className="staff-list">{rows.map(row => <li key={row.id}><strong>{row.verification_code}</strong><span>{row.point_name}</span><div className="actions"><button disabled={busy} onClick={() => { void decide(row, 'APPROVED'); }}>Autorizar dispositivo</button><button className="secondary" disabled={busy} onClick={() => { void decide(row, 'REJECTED'); }}>Recusar acesso</button></div></li>)}</ul> : <p>Nenhuma solicitação pendente.</p>}<Pagination page={page} next={next} change={setPage} /></section>;
}
