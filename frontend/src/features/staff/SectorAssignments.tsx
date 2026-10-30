import { useAutoRefresh } from '../../lib/useAutoRefresh';
import Toast from '../../components/Toast';
import { LoadingSkeleton } from '../../components/Interface';
import { useEffect, useRef, useState } from 'react';
import { record, request, text } from '../../lib/api';
import type { Staff } from '../../lib/api';
import { ResourceSelect } from './CatalogManagement';

function decode(value: unknown) { const row = record(value); if (!Array.isArray(row.sectors)) throw new Error('Resposta inválida do serviço.'); return row.sectors.map((value: unknown) => { const sector = record(value); return { id: text(sector.id), name: text(sector.name) }; }); }
export default function SectorAssignments({ staff, busyChanged }: { staff: Staff; busyChanged: (busy: boolean) => void }) {
  const saving = useRef(false);
  const [sectors, setSectors] = useState<ReturnType<typeof decode> | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  useAutoRefresh(() => setReload(value => value + 1));
  const path = `/api/v1/admin/staff/${staff.id}/sectors/`;
  useEffect(() => { const controller = new AbortController(); void request(path, 'GET', undefined, controller.signal).then(decode).then(setSectors).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os setores.'); }); return () => controller.abort(); }, [path, reload]);
  async function save(ids: string[]) {
    if (saving.current) return; saving.current = true; setBusy(true); busyChanged(true); setError(''); setMessage('');
    try { setSectors(decode(await request(path, 'PUT', { sector_ids: ids, reason: reason.trim() }))); setMessage('Setores do funcionário atualizados com sucesso.'); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível atualizar os setores.'); }
    finally { saving.current = false; setBusy(false); busyChanged(false); }
  }
  return <section><p>O KDS exige a permissão de produção e um vínculo ao setor. Limite de 20 setores.</p>{error && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} /><label>Motivo da alteração (opcional)<input value={reason} disabled={busy} maxLength={300} onChange={event => setReason(event.target.value)} /></label>{sectors === null ? <LoadingSkeleton variant="options" /> : <><ul className="staff-list">{sectors.map(sector => <li key={sector.id}>{sector.name}<button className="secondary" disabled={busy} onClick={() => { void save(sectors.filter(value => value.id !== sector.id).map(value => value.id)); }}>Remover vínculo</button></li>)}</ul><form onSubmit={event => { event.preventDefault(); const id = new FormData(event.currentTarget).get('sector'); if (typeof id === 'string' && !sectors.some(value => value.id === id)) void save([...sectors.map(value => value.id), id]); else setError('Esse setor já está vinculado.'); }}><fieldset disabled={busy}><legend className="sr-only">Vincular setor de produção</legend><ResourceSelect name="sector" label="Adicionar setor" kind="staff/sector-options" initial="" /><button disabled={busy || sectors.length >= 20} type="submit">Adicionar vínculo</button></fieldset></form></>}</section>;
}
