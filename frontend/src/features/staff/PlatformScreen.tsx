import { formSaveResult, requestEditorClose } from '../../lib/formChanges';
import Toast from '../../components/Toast';
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, request } from '../../lib/api';

import { Editor, PageHeader, Pagination, StatusTag } from './StaffUI';
import { Icon, EmptyState, LoadingSkeleton, SecretInput } from '../../components/Interface';
import '../../design-system/staff.css';
import '../../design-system/customer.css';
import '../../design-system/login.css';

type Entry = { id: string; name: string; slug: string; active: boolean; company_id?: string };
type Page = { count: number; next: string | null; previous: string | null; results: Entry[] };

function decodePage(data: unknown): Page {
  if (typeof data !== 'object' || data === null || !('count' in data) || typeof data.count !== 'number' || !('results' in data) || !Array.isArray(data.results) || !('next' in data) || !('previous' in data)) throw new Error('Resposta inválida do serviço.');
  const results = data.results.map((value: unknown) => {
    if (typeof value !== 'object' || value === null || !('id' in value) || typeof value.id !== 'string' || !('name' in value) || typeof value.name !== 'string' || !('slug' in value) || typeof value.slug !== 'string' || !('active' in value) || typeof value.active !== 'boolean') throw new Error('Resposta inválida do serviço.');
    return { id: value.id, name: value.name, slug: value.slug, active: value.active, ...('company_id' in value && typeof value.company_id === 'string' ? { company_id: value.company_id } : {}) };
  });
  if ((data.next !== null && typeof data.next !== 'string') || (data.previous !== null && typeof data.previous !== 'string')) throw new Error('Resposta inválida do serviço.');
  return { count: data.count, next: data.next, previous: data.previous, results };
}

export default function PlatformScreen() {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [companies, setCompanies] = useState<Page | null>(null);
  const [units, setUnits] = useState<Page | null>(null);
  const [companyPage, setCompanyPage] = useState(1);
  const [unitPage, setUnitPage] = useState(1);
  const [creating, setCreating] = useState<'company' | 'unit' | null>(null);
  const [chosenCompany, setChosenCompany] = useState<Entry | null>(null);
  const [reload, setReload] = useState(0);
  const fail = (cause: unknown) => setError(cause instanceof Error ? cause.message : 'Não foi possível concluir.');
  useEffect(() => {
    const controller = new AbortController();
    void request('/api/v1/platform/me/', 'GET', undefined, controller.signal).then(() => setAuthenticated(true)).catch((cause: unknown) => { if (!controller.signal.aborted && !(cause instanceof ApiError && cause.status === 401)) fail(cause); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    const controller = new AbortController();
    void request(`/api/v1/platform/companies/?page=${companyPage}`, 'GET', undefined, controller.signal).then(decodePage).then(data => { if (!controller.signal.aborted) setCompanies(data); }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && companyPage > 1) setCompanyPage(1); else fail(cause); } });
    return () => controller.abort();
  }, [authenticated, companyPage, reload]);
  useEffect(() => {
    if (!authenticated) return;
    const controller = new AbortController();
    void request(`/api/v1/platform/units/?page=${unitPage}`, 'GET', undefined, controller.signal).then(decodePage).then(data => { if (!controller.signal.aborted) setUnits(data); }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && unitPage > 1) setUnitPage(1); else fail(cause); } });
    return () => controller.abort();
  }, [authenticated, unitPage, reload]);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const form = event.currentTarget; const data = new FormData(form); setBusy(true); setError('');
    try { await request('/api/v1/platform/login/', 'POST', { username: data.get('username'), password: data.get('password') }); form.reset(); setAuthenticated(true); }
    catch (cause: unknown) { fail(cause); }
    finally { setBusy(false); }
  }
  async function create(event: FormEvent<HTMLFormElement>, unit: boolean) {
    event.preventDefault(); if (busy) return;
    const form = event.currentTarget; const data = new FormData(form); setBusy(true); setError(''); setMessage('');
    try { await request(unit ? '/api/v1/platform/units/' : '/api/v1/platform/companies/', 'POST', { name: data.get('name'), slug: data.get('slug'), ...(unit ? { company_id: data.get('company_id') } : {}) }); formSaveResult(form, true); form.reset(); setCreating(null); setChosenCompany(null); setMessage(unit ? 'Unidade cadastrada.' : 'Empresa cadastrada.'); setReload(value => value + 1); }
    catch (cause: unknown) { formSaveResult(form, false); fail(cause); }
    finally { setBusy(false); }
  }
  async function leave() {
    if (busy) return; setBusy(true); setError('');
    try { await request('/api/v1/platform/logout/', 'POST', {}); setAuthenticated(false); setCompanies(null); setUnits(null); }
    catch (cause: unknown) { fail(cause); }
    finally { setBusy(false); }
  }
  if (loading || !authenticated) return <main className="staff-login"><img className="login-logo" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /><h1>Administração da plataforma</h1><p className="login-subtitle">Acesso individual à gestão de empresas e unidades.</p>{error && <p className="error" role="alert">{error}</p>}{loading ? <LoadingSkeleton variant="staff" /> : <form onSubmit={event => { void login(event); }} aria-busy={busy}><label>Usuário<input name="username" required maxLength={150} autoComplete="username" disabled={busy} /></label><div><label htmlFor="platform-password">Senha</label><SecretInput label="senha" id="platform-password" name="password" required maxLength={256} autoComplete="current-password" disabled={busy} /></div><button className="ui-button ui-primary login-submit" disabled={busy} type="submit">{busy ? 'Entrando…' : 'Entrar na plataforma'}</button></form>}<p><a href="/staff/login">Acesso da equipe</a></p></main>;
  const navigation = <><div className="staff-unit"><strong>Administração da plataforma</strong><span>Empresas e unidades</span></div><nav className="staff-navigation" aria-label="Administração da plataforma"><a href="#companies"><Icon name="users" />Empresas</a><a href="#units"><Icon name="table" />Unidades</a></nav><div className="staff-profile"><span>Acesso da plataforma</span><button className="secondary" disabled={busy} onClick={() => { void leave(); }}>Sair da plataforma</button><a href="/staff/login">Acesso da equipe</a></div></>;
  return <div className="staff-shell"><aside className="staff-sidebar"><a className="staff-brand" href="/platform"><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /></a>{navigation}</aside><details className="staff-mobile-menu"><summary><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /><span>Menu<Icon name="chevron" size={18} /></span></summary>{navigation}</details><main className="staff-main"><div className="staff-topbar"><span>TapServe</span><span>Administração da plataforma</span></div><PageHeader title="Empresas e unidades" description="Cadastros da plataforma. A operação de cada unidade usa uma identidade própria." />
    {error && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} />
    <div className="staff-platform-grid"><section className="staff-platform-section" id="companies"><div className="staff-page-header"><h2>Empresas</h2><button disabled={busy} onClick={() => setCreating('company')}>Cadastrar empresa</button></div>{companies ? <><p className="muted">{companies.count} empresas cadastradas</p><div className="staff-data">{companies.results.length === 0 ? <EmptyState title="Nenhuma empresa cadastrada" /> : <ul className="staff-list">{companies.results.map(row => <li key={row.id}><div><div className="staff-row-title"><strong>{row.name}</strong><StatusTag>{row.active ? 'Ativa' : 'Desativada'}</StatusTag></div><p>Código: {row.slug}</p></div></li>)}</ul>}</div><Pagination page={companyPage} next={companies.next !== null} previous={companies.previous !== null} busy={busy} label="Empresas" change={value => { setCompanyPage(value); setCompanies(null); }} /></> : <LoadingSkeleton variant="staff" />}</section>
    <section className="staff-platform-section" id="units"><div className="staff-page-header"><h2>Unidades</h2><button disabled={busy} onClick={() => setCreating('unit')}>Cadastrar unidade</button></div>{units ? <><p className="muted">{units.count} unidades cadastradas</p><div className="staff-data">{units.results.length === 0 ? <EmptyState title="Nenhuma unidade cadastrada" /> : <ul className="staff-list">{units.results.map(row => <li key={row.id}><div><div className="staff-row-title"><strong>{row.name}</strong><StatusTag>{row.active ? 'Ativa' : 'Desativada'}</StatusTag></div><p>Código: {row.slug}</p></div></li>)}</ul>}</div><Pagination page={unitPage} next={units.next !== null} previous={units.previous !== null} busy={busy} label="Unidades" change={value => { setUnitPage(value); setUnits(null); }} /></> : <LoadingSkeleton variant="staff" />}</section></div>
    {creating && <Editor title={creating === 'company' ? 'Cadastrar empresa' : 'Cadastrar unidade'} close={() => setCreating(null)} busy={busy}><form className="staff-form-grid" onSubmit={event => { void create(event, creating === 'unit'); }} aria-busy={busy}>{creating === 'unit' && <fieldset><legend>Empresa da unidade</legend><label>Empresa<select name="company_id" required value={chosenCompany?.id ?? ''} onChange={event => setChosenCompany(companies?.results.find(row => row.id === event.target.value) ?? null)}><option value="">Selecione uma empresa</option>{chosenCompany && !companies?.results.some(row => row.id === chosenCompany.id) && <option value={chosenCompany.id}>{chosenCompany.name}</option>}{companies?.results.filter(row => row.active).map(row => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label>{companies && <Pagination page={companyPage} next={companies.next !== null} previous={companies.previous !== null} busy={busy} label="Opções de empresa" change={value => { setCompanyPage(value); setCompanies(null); }} />}</fieldset>}<label>Nome {creating === 'company' ? 'da empresa' : 'da unidade'}<input name="name" required maxLength={120} /></label><label>Código {creating === 'company' ? 'da empresa' : 'da unidade'}<input name="slug" required maxLength={80} pattern="[A-Za-z0-9_\-]+" /></label><div className="actions"><button disabled={busy} type="submit">{busy ? 'Salvando…' : creating === 'company' ? 'Cadastrar empresa' : 'Cadastrar unidade'}</button><button className="secondary" type="button" disabled={busy} onClick={requestEditorClose}>Cancelar</button></div></form></Editor>}
  </main></div>;
}
