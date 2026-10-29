import { useEffect, useRef, useState } from 'react';
import { randomUUID } from '../../lib/uuid';
import Toast from '../../components/Toast';
import ConfirmDialog from '../../components/ConfirmDialog';
import type { FormEvent } from 'react';
import { ApiError, decodeRoles, decodeStaff, decodeStaffPage, request } from '../../lib/api';
import type { Role, Staff, StaffContext, StaffPage } from '../../lib/api';
import SectorAssignments from './SectorAssignments';
import { Editor, PageHeader, Pagination, StatusTag } from './StaffUI';
import { EmptyState, ErrorState, SecretInput, LoadingSkeleton } from '../../components/Interface';
const errorText = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.';

const labels: Record<string, string> = {
  OWNER: 'Proprietário', ADMIN: 'Administrador', MANAGER: 'Gerente', WAITER: 'Atendente', KITCHEN: 'Cozinha', BAR: 'Bar', CASHIER: 'Caixa',
  VIEW_OPERATION: 'Ver operação', VIEW_ALL_TABLES: 'Ver todas as mesas', CREATE_MANUAL_ORDER: 'Criar pedido manual', EDIT_ORDER: 'Alterar pedido', CANCEL_ORDER: 'Cancelar pedido',
  ASSIGN_SERVICE_REQUEST: 'Assumir e resolver chamados', TRANSFER_SESSION: 'Transferir atendimento', MERGE_TABLES: 'Juntar mesas', SPLIT_TABLES: 'Separar mesas', REGISTER_PAYMENT: 'Registrar recebimento', CLOSE_SESSION: 'Fechar atendimento', REOPEN_SESSION: 'Reabrir atendimento',
  CREATE_DISCOUNT: 'Criar cupom', APPLY_MANUAL_DISCOUNT: 'Aplicar desconto manual', MANAGE_MENU: 'Gerenciar cardápio', MANAGE_STAFF: 'Gerenciar funcionários', MANAGE_SETTINGS: 'Gerenciar configurações', VIEW_REPORTS: 'Ver relatórios', VIEW_AUDIT: 'Ver auditoria',
  MANAGE_SERVICE_POINTS: 'Gerenciar pontos de atendimento', PROVISION_NFC: 'Provisionar NFC', ROTATE_SERVICE_POINT_TOKEN: 'Rotacionar link do ponto', LOCK_NFC_TAG: 'Proteger tag NFC', UPDATE_PRODUCTION_STATUS: 'Atualizar produção', CLAIM_DELIVERY: 'Assumir entrega', COMPLETE_DELIVERY: 'Concluir entrega',
};

export default function StaffManagement({ context }: { context: StaffContext }) {
  const saving = useRef(false);
  const createKey = useRef(randomUUID());
  const [action, setAction] = useState<{ staff: Staff; remove: boolean } | null>(null);
  const [page, setPage] = useState<StaffPage | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [rolesError, setRolesError] = useState('');
  const [rolesRetry, setRolesRetry] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [roleId, setRoleId] = useState('');
  const [grants, setGrants] = useState<string[]>([]);
  const [selected, setSelected] = useState<Staff | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [active, setActive] = useState('');
  const [sectorStaff, setSectorStaff] = useState<Staff | null>(null);
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(query); setPageNumber(1); }, 250); return () => window.clearTimeout(timer); }, [query]);
  useEffect(() => {
    const controller = new AbortController();
    void request('/api/v1/admin/roles/', 'GET', undefined, controller.signal).then(decodeRoles).then(values => { if (!controller.signal.aborted) { setRoles(values.filter(role => !['OWNER', 'ADMIN'].includes(role.name))); setRolesError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) setRolesError(errorText(cause)); });
    return () => controller.abort();
  }, [rolesRetry]);
  useEffect(() => {
    const controller = new AbortController();
    void request(`/api/v1/admin/staff/?page=${pageNumber}&search=${encodeURIComponent(search)}${active ? `&active=${active}` : ''}`, 'GET', undefined, controller.signal).then(decodeStaffPage).then(data => { if (!controller.signal.aborted) { setPage(data); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && pageNumber > 1) setPageNumber(1); else setError(errorText(cause)); } });
    return () => controller.abort();
  }, [pageNumber, reload, search, active]);
  function closeEditor() { setSelected(null); setRoleId(''); setGrants([]); setEditorOpen(false); }
  function chooseRole(value: string) {
    setRoleId(value); setGrants(roles.find(role => role.id === value)?.permissions.filter(code => context.staff.permissions.includes(code)) ?? []);
  }
  async function save(event: FormEvent<HTMLFormElement>, update: boolean) {
    event.preventDefault(); if (saving.current) return;
    saving.current = true;
    const form = event.currentTarget; const data = new FormData(form);
    setBusy(true); setError(''); setMessage('');
    const body = update ? { name: data.get('name'), permissions: grants, reason: data.get('reason'), ...(data.get('pin') ? { pin: data.get('pin') } : {}) } : { idempotency_key: createKey.current, name: data.get('name'), login_code: data.get('login_code'), pin: data.get('pin'), role_id: roleId, permissions: grants };
    try { decodeStaff(await request(update && selected ? `/api/v1/admin/staff/${selected.id}/` : '/api/v1/admin/staff/', update ? 'PATCH' : 'POST', body)); form.reset(); setEditorOpen(false); setSelected(null); setRoleId(''); setGrants([]); setMessage(update ? 'Alterações salvas.' : 'Funcionário cadastrado.'); setReload(value => value + 1); }
    catch (cause: unknown) { setError(errorText(cause)); }
    finally { saving.current = false; setBusy(false); }
  }
  return <section><PageHeader title="Funcionários da unidade" description="Acessos individuais, permissões e setores de trabalho." action={<button disabled={busy} onClick={() => { closeEditor(); setSectorStaff(null); setEditorOpen(true); }}>Cadastrar funcionário</button>} />
    {rolesError && <ErrorState message={rolesError} retry={() => setRolesRetry(value => value + 1)} />}{error && !editorOpen && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} />
    <div className="staff-toolbar"><label className="staff-search">Buscar funcionário<input type="search" value={query} maxLength={100} placeholder="Nome do funcionário" onChange={event => setQuery(event.target.value)} /></label><label>Situação<select value={active} onChange={event => { setActive(event.target.value); setPageNumber(1); setPage(null); }}><option value="">Todas</option><option value="true">Ativos</option><option value="false">Desativados</option></select></label><button className="secondary" disabled={busy} onClick={() => { setError(''); setReload(value => value + 1); }}>Atualizar lista</button></div>
    {page ? <><p className="muted">{page.count} funcionários encontrados · {context.unit_name}</p><div className="staff-data">{page.results.length === 0 ? <EmptyState title="Nenhum funcionário encontrado">Revise a busca e os filtros.</EmptyState> : <ul className="staff-list">{page.results.map(staff => <li key={staff.id}><div><div className="staff-row-title"><strong>{staff.name}</strong><StatusTag>{staff.active ? 'Ativo' : 'Desativado'}</StatusTag></div><p>{labels[staff.role] ?? staff.role } · Código: {staff.login_code}{staff.id === context.staff.id ? ' · Seu acesso' : ''}</p></div><button className="secondary" disabled={busy} onClick={() => { closeEditor(); setSectorStaff(staff); }}>Setores de produção</button>{staff.id !== context.staff.id && !['OWNER', 'ADMIN'].includes(staff.role) && <button className="secondary" disabled={busy} onClick={() => { setSectorStaff(null); setSelected(staff); setGrants(staff.permissions); setEditorOpen(true); setError(''); setMessage(''); }}>Editar</button>}{staff.id !== context.staff.id && !['OWNER', 'ADMIN'].includes(staff.role) && <><button className={staff.active ? 'ui-danger' : 'secondary'} disabled={busy} onClick={() => setAction({ staff, remove: false })}>{staff.active ? 'Desativar funcionário' : 'Reativar funcionário'}</button><button className="ui-danger" disabled={busy} onClick={() => setAction({ staff, remove: true })}>Excluir funcionário</button></>}</li>)}</ul>}</div>
      <Pagination page={pageNumber} next={page.next !== null} previous={page.previous !== null} busy={busy} label="Funcionários" change={value => { setPageNumber(value); setPage(null); }} /></> : <LoadingSkeleton variant="staff" />}
    {sectorStaff && <Editor title={`Setores de ${sectorStaff.name}`} close={() => setSectorStaff(null)} busy={busy}><SectorAssignments key={sectorStaff.id} staff={sectorStaff} busyChanged={setBusy} /><button type="button" className="secondary" disabled={busy} onClick={() => setSectorStaff(null)}>Voltar</button></Editor>}
    {editorOpen && <Editor title={selected ? `Editar ${selected.name}` : 'Cadastrar funcionário'} close={closeEditor} busy={busy}>{error && <p className="error" role="alert">{error}</p>}<p>O perfil sugere permissões. Revise o acesso individual antes de salvar.</p>
    <form className="staff-form-grid" key={selected?.id ?? 'new'} onChange={() => { if (!saving.current) createKey.current = randomUUID(); }} onSubmit={event => { void save(event, selected !== null); }} aria-busy={busy}>
      <label>Nome<input disabled={busy} name="name" required maxLength={100} defaultValue={selected?.name ?? ''} /></label>
      {!selected && <><label>Código individual<input disabled={busy} name="login_code" required pattern="[A-Za-z0-9_\-]{1,32}" maxLength={32} autoComplete="off" /></label><label>Perfil<select disabled={busy || roles.length === 0} required value={roleId} onChange={event => chooseRole(event.target.value)}><option value="">Selecione</option>{roles.map(role => <option key={role.id} value={role.id}>{labels[role.name] ?? role.name}</option>)}</select></label></>}
      <div><label htmlFor="staff-new-pin">{selected ? 'Novo PIN (deixe vazio para manter)' : 'PIN individual'}</label><SecretInput id="staff-new-pin" label="PIN" disabled={busy} name="pin" required={!selected} pattern="[0-9]{6,12}" minLength={6} maxLength={12} inputMode="numeric" autoComplete="new-password" /></div>
      <fieldset disabled={busy}><legend>Permissões efetivas · {grants.length} selecionadas</legend><div className="staff-permissions">{context.staff.permissions.map(code => <label className="check" key={code}><input type="checkbox" checked={grants.includes(code)} onChange={event => setGrants(values => event.target.checked ? [...values, code] : values.filter(value => value !== code))} />{labels[code] ?? code}</label>)}</div></fieldset>
      {selected && <><label>Motivo da alteração<input disabled={busy} name="reason" maxLength={300} /></label></>}
      <div className="actions"><button disabled={busy || (!selected && !roleId)} type="submit">{busy ? 'Salvando…' : selected ? 'Salvar alterações' : 'Cadastrar funcionário'}</button><button className="secondary" type="button" disabled={busy} onClick={closeEditor}>Cancelar</button></div>
    </form></Editor>}
    {action && <ConfirmDialog destructive={action.remove || action.staff.active} title={action.remove ? 'Excluir funcionário?' : action.staff.active ? 'Desativar funcionário?' : 'Reativar funcionário?'} description={`${action.staff.name}. O histórico será preservado. Sessões anteriores serão invalidadas.`} label={action.remove ? 'Excluir funcionário' : action.staff.active ? 'Desativar funcionário' : 'Reativar funcionário'} close={() => setAction(null)} confirm={async reason => {
      await request(`/api/v1/admin/staff/${action.staff.id}/`, action.remove ? 'DELETE' : 'PATCH', action.remove ? { reason } : { active: !action.staff.active, reason });
      setMessage(action.remove ? 'Funcionário excluído.' : 'Alterações salvas.'); setReload(value => value + 1);
    }} />}
  </section>;
}
