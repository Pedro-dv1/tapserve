import { randomUUID } from '../../lib/uuid.ts';
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, record, request, text } from '../../lib/api';

import { Editor, PageHeader, Pagination, StatusTag } from './StaffUI';
import { EmptyState, LoadingSkeleton } from '../../components/Interface';
import type { StaffContext } from '../../lib/api';
import Toast from '../../components/Toast';
import ConfirmDialog from '../../components/ConfirmDialog';
import { brl } from '../customer/menuData';
import ProductPhotos from './ProductPhotos';

type Entity = Record<string, unknown> & { id: string; name: string };
type Field = { name: string; label: string; type: 'text' | 'textarea' | 'checkbox' | 'money' | 'integer' | 'relation' | 'selection'; relation?: string; initial?: string | number | boolean; min?: number; max?: number; optional?: boolean };
const name: Field = { name: 'name', label: 'Nome', type: 'text' };
const active: Field = { name: 'active', label: 'Ativo', type: 'checkbox', initial: true };
const available: Field = { name: 'available', label: 'Disponível', type: 'checkbox', initial: true };
const sections: Record<string, { label: string; fields: Field[] }> = {
  menus: { label: 'Cardápios', fields: [name, active] },
  categories: { label: 'Categorias', fields: [name, { name: 'menu', label: 'Cardápio', type: 'relation', relation: 'menus' }, { name: 'position', label: 'Ordem de exibição', type: 'integer', initial: 0, min: 0, max: 32767 }, active] },
  sectors: { label: 'Setores de produção', fields: [name, active] },
  products: { label: 'Produtos', fields: [name, { name: 'description', label: 'Descrição curta', type: 'textarea' }, { name: 'long_description', label: 'Descrição completa', type: 'textarea', max: 4000 }, { name: 'ingredients', label: 'Ingredientes', type: 'textarea' }, { name: 'serving_info', label: 'Porção / para quantas pessoas', type: 'text', max: 120, optional: true }, { name: 'allergen_info', label: 'Alergênicos declarados', type: 'textarea', max: 500 }, { name: 'featured', label: 'Destacar com foto no cardápio', type: 'checkbox', initial: false }, { name: 'category', label: 'Categoria', type: 'relation', relation: 'categories' }, { name: 'production_sector', label: 'Setor de produção', type: 'relation', relation: 'sectors' }, { name: 'base_price', label: 'Preço em reais', type: 'money', initial: '0.00' }, active, available, { name: 'takeaway_allowed', label: 'Permitir para levar', type: 'checkbox', initial: true }] },
  'option-groups': { label: 'Grupos de opções', fields: [name, { name: 'product', label: 'Produto inicial', type: 'relation', relation: 'products' }, { name: 'selection_type', label: 'Seleção', type: 'selection', initial: 'SINGLE' }, { name: 'required', label: 'Seleção obrigatória', type: 'checkbox', initial: false }, { name: 'min_choices', label: 'Mínimo de escolhas', type: 'integer', initial: 0, min: 0, max: 20 }, { name: 'max_choices', label: 'Máximo de escolhas', type: 'integer', initial: 1, min: 1, max: 20 }, active] },
  options: { label: 'Opções', fields: [name, { name: 'group', label: 'Grupo de opções', type: 'relation', relation: 'option-groups' }, { name: 'additional_price', label: 'Preço adicional em reais', type: 'money', initial: '0.00' }, active, available] },
};
const singular: Record<string, string> = { menus: 'cardápio', categories: 'categoria', sectors: 'setor', products: 'produto', 'option-groups': 'grupo de opções', options: 'opção' };
function entity(data: unknown): Entity {
  const row = record(data); return { ...row, id: text(row.id), name: text(row.name) };
}
function pageEntries(data: unknown): { results: Entity[]; next: boolean } {
  const row = record(data); if (!Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
  return { results: row.results.map(entity), next: typeof row.next === 'string' };
}

export default function CatalogManagement({ context }: { context: StaffContext }) {
  const saving = useRef(false);
  const imageInput = useRef<HTMLInputElement>(null);
  const videoInput = useRef<HTMLInputElement>(null);
  const writeKey = useRef(randomUUID());
  const [deactivating, setDeactivating] = useState(false);
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [removeImage, setRemoveImage] = useState(false);
  const [video, setVideo] = useState<File | null>(null);
  const [videoPreview, setVideoPreview] = useState('');
  const [removeVideo, setRemoveVideo] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [menu, setMenu] = useState('');
  const [menuPoints, setMenuPoints] = useState<string[]>([]);
  const [kind, setKind] = useState('products');
  const [entries, setEntries] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [photoProduct, setPhotoProduct] = useState<Entity | null>(null);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [availability, setAvailability] = useState('');
  const section = sections[kind];
  useEffect(() => { if (!image) { setPreview(''); return; } const url = URL.createObjectURL(image); setPreview(url); return () => URL.revokeObjectURL(url); }, [image]);
  useEffect(() => { if (!video) { setVideoPreview(''); return; } const url = URL.createObjectURL(video); setVideoPreview(url); return () => URL.revokeObjectURL(url); }, [video]);
  useEffect(() => { const controller = new AbortController(); void request('/api/v1/admin/menus/?active=true', 'GET', undefined, controller.signal).then(pageEntries).then(data => { if (!controller.signal.aborted && data.results.length === 1 && !data.next) setMenu(data.results[0]?.id ?? ''); }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar cardápios.'); }); return () => controller.abort(); }, []);
  useEffect(() => { if (!menu) return; const controller = new AbortController(); void request(`/api/v1/admin/menus/${menu}/`, 'GET', undefined, controller.signal).then(record).then(data => { if (!controller.signal.aborted) setMenuPoints(Array.isArray(data.points) ? data.points.map(point => text(record(point).name)) : []); }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar pontos.'); }); return () => controller.abort(); }, [menu, reload]);
  useEffect(() => { const timer = window.setTimeout(() => { setSearch(query); setPage(1); }, 250); return () => window.clearTimeout(timer); }, [query]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    if (!menu && ['products', 'categories'].includes(kind)) { setEntries([]); setNext(false); setLoading(false); return; }
    void request(`/api/v1/admin/${kind}/?page=${page}&search=${encodeURIComponent(search)}${activeFilter ? `&active=${activeFilter}` : ''}${availability ? `&available=${availability}` : ''}${menu && ['products', 'categories'].includes(kind) ? `&menu=${menu}` : ''}`, 'GET', undefined, controller.signal).then(pageEntries).then(data => { if (!controller.signal.aborted) { setEntries(data.results); setNext(data.next); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar.'); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [kind, page, reload, search, activeFilter, availability, menu]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving.current || !section) return;
    const form = event.currentTarget; const data = new FormData(form); const body: Record<string, unknown> = {};
    for (const field of section.fields) body[field.name] = field.type === 'checkbox' ? data.get(field.name) === 'on' : field.type === 'integer' ? Number(data.get(field.name)) : data.get(field.name);
    saving.current = true; setBusy(true); setError(''); setFieldErrors({}); setMessage('');
    if (kind === 'products') { body.idempotency_key = writeKey.current; body.remove_image = removeImage; body.remove_video = removeVideo; body.option_group_ids = data.getAll('option_group_ids'); body.individual_option_ids = data.getAll('individual_option_ids'); }
    const upload = new FormData(); if (kind === 'products') { for (const [key, value] of Object.entries(body)) upload.set(key, Array.isArray(value) ? JSON.stringify(value) : String(value)); if (image) upload.set('image', image); if (video) upload.set('video', video); }
    try { entity(await request(selected ? `/api/v1/admin/${kind}/${selected.id}/` : `/api/v1/admin/${kind}/`, selected ? 'PATCH' : 'POST', kind === 'products' ? upload : body)); setMessage(selected ? 'Alterações salvas.' : `${singular[kind]?.replace(/^./, value => value.toUpperCase())} cadastrad${['categories', 'options'].includes(kind) ? 'a' : 'o'}.`); closeEditor(); form.reset(); setReload(value => value + 1); }
    catch (cause: unknown) { if (cause instanceof ApiError) setFieldErrors(cause.status === 413 && (video || image) ? { [video ? 'video' : 'image']: cause.message } : cause.fields); setError(cause instanceof Error ? cause.message : 'Não foi possível salvar.'); }
    finally { saving.current = false; setBusy(false); }
  }
  function closeEditor() { setSelected(null); setEditorOpen(false); setImage(null); setRemoveImage(false); setVideo(null); setRemoveVideo(false); setFieldErrors({}); writeKey.current = randomUUID(); }
  return <section><PageHeader title="Cardápio da unidade" description={`${context.company_name} · ${context.unit_name}`} />
    <UnitSelector context={context} />
    <div className="catalog-navigation-row"><nav className="staff-tabs" aria-label="Cadastros do cardápio">{Object.entries(sections).map(([key, value]) => <button key={key} disabled={busy} aria-pressed={kind === key} onClick={() => { setKind(key); closeEditor(); setPage(1); setEntries([]); setLoading(true); setAvailability(''); setQuery(''); setSearch(''); setError(''); }}>{value.label}</button>)}</nav><span className="catalog-divider" aria-hidden="true">|</span><button disabled={busy || (!menu && ['products', 'categories'].includes(kind))} onClick={() => { closeEditor(); setEditorOpen(true); setError(''); }}>+ Cadastrar {singular[kind]}</button></div>
    <div className="staff-menu-context"><ResourceSelect key={menu} name="context_menu" label="Selecionar cardápio" kind="menus" initial={menu} disabled={busy} changed={value => { setMenu(value); setPage(1); closeEditor(); }} />{menu && <p>Pontos: {menuPoints.length ? menuPoints.join(', ') : 'Nenhum ponto vinculado'}</p>}</div>
    {error && !editorOpen && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} />
    <div className="staff-toolbar"><label className="staff-search">Buscar {section?.label.toLocaleLowerCase('pt-BR')}<input type="search" value={query} maxLength={100} placeholder="Nome do cadastro" onChange={event => setQuery(event.target.value)} /></label><label>Situação<select value={activeFilter} disabled={busy} onChange={event => { setActiveFilter(event.target.value); setPage(1); }}><option value="">Todas</option><option value="true">Ativos</option><option value="false">Desativados</option></select></label>{['products', 'options'].includes(kind) && <label>Disponibilidade<select value={availability} onChange={event => { setAvailability(event.target.value); setPage(1); }}><option value="">Todas</option><option value="true">Disponíveis</option><option value="false">Indisponíveis</option></select></label>}<button className="secondary" disabled={busy || loading} onClick={() => { setError(''); setReload(value => value + 1); }}>Atualizar lista</button></div>
    <div className="staff-data">{loading && entries.length === 0 ? <LoadingSkeleton variant="catalog" /> : error && entries.length === 0 ? null : entries.length === 0 ? <EmptyState title="Nenhum cadastro encontrado">Revise os filtros ou crie um cadastro.</EmptyState> : <ul className="staff-list">{entries.map(row => <li key={row.id}>{kind === 'products' && row.has_image === true && <img className="staff-product-thumbnail" src={`/api/v1/admin/products/${row.id}/image/?v=${typeof row.image_version === 'string' ? row.image_version : ''}`} alt="" loading="lazy" />}<div><div className="staff-row-title"><strong>{row.name}</strong><StatusTag>{row.active === true ? 'Ativo' : 'Desativado'}</StatusTag>{row.available === false && <StatusTag attention>Indisponível</StatusTag>}</div>{typeof row.base_price === 'string' && <p>{brl(row.base_price)}</p>}{typeof row.additional_price === 'string' && <p>Adicional: {brl(row.additional_price)}</p>}</div><button className="secondary" disabled={busy} onClick={() => { setSelected(row); setEditorOpen(true); setError(''); setMessage(''); }}>Editar</button>{kind === 'products' && <button type="button" className="secondary" disabled={busy} onClick={() => setPhotoProduct(row)}>Fotos</button>}</li>)}</ul>}</div>
    <Pagination page={page} next={next} busy={busy || loading} label={section?.label ?? 'Cardápio'} change={setPage} />
    {photoProduct && <ProductPhotos product={photoProduct} close={() => setPhotoProduct(null)} />}
    {editorOpen && <Editor modal title={selected ? `Editar ${selected.name}` : `Cadastrar ${singular[kind]}`} close={closeEditor} busy={busy}>{error && <p className="error" role="alert">{error}</p>}
    <form className="staff-form-grid" aria-busy={busy} key={kind + (selected?.id ?? 'new')} onChange={() => { if (!saving.current) writeKey.current = randomUUID(); }} onSubmit={event => { void save(event); }}>
      {kind === 'option-groups' && selected && Array.isArray(selected.product_ids) && selected.product_ids.length > 1 && <p className="staff-full-width" role="status">Este grupo é usado por {selected.product_ids.length} produtos. As alterações afetam todos eles.</p>}
      {kind === 'products' && <><MultiResource name="option_group_ids" label="Grupos de opções reutilizáveis" kind="option-groups" initial={Array.isArray(selected?.option_group_ids) ? selected.option_group_ids as string[] : []} disabled={busy} /><MultiResource name="individual_option_ids" label="Opções individuais" kind="options" initial={Array.isArray(selected?.individual_option_ids) ? selected.individual_option_ids as string[] : []} disabled={busy} /></>}
      {section?.fields.map(field => {
        const value = selected?.[field.name] ?? (field.name === 'menu' ? menu : field.initial) ?? '';
        const invalid = fieldErrors[field.name]; const errorId = `catalog-error-${field.name}`;
        const feedback = invalid ? <span className="error field-error" id={errorId}>{invalid}</span> : null;
        if (field.type === 'relation' && field.relation) return <ResourceSelect key={field.name} name={field.name} label={field.label} kind={field.relation} disabled={busy} initial={typeof value === 'string' ? value : ''} menu={field.relation !== 'menus' && field.relation !== 'sectors' ? menu : undefined} error={invalid} />;
        if (field.type === 'checkbox') return <label className="check" key={field.name}><input aria-invalid={Boolean(invalid)} disabled={busy} name={field.name} type="checkbox" defaultChecked={value === true} />{field.label}{feedback}</label>;
        if (field.type === 'textarea') return <label key={field.name}>{field.label}<textarea disabled={busy} name={field.name} maxLength={field.max ?? 1000} aria-invalid={Boolean(invalid)} aria-describedby={invalid ? errorId : undefined} defaultValue={typeof value === 'string' ? value : ''} />{feedback}</label>;
        if (field.type === 'selection') return <label key={field.name}>{field.label}<select disabled={busy} aria-invalid={Boolean(invalid)} name={field.name} defaultValue={typeof value === 'string' ? value : 'SINGLE'}><option value="SINGLE">Uma escolha</option><option value="MULTIPLE">Várias escolhas</option></select>{feedback}</label>;
        return <label key={field.name}>{field.label}<input disabled={busy} name={field.name} type={field.type === 'text' ? 'text' : 'number'} required={!field.optional} maxLength={field.max ?? 100} min={field.type === 'money' ? 0 : field.min} max={field.type === 'money' ? 99999.99 : field.max} step={field.type === 'money' ? '0.01' : '1'} aria-invalid={Boolean(invalid)} aria-describedby={invalid ? errorId : undefined} defaultValue={typeof value === 'string' || typeof value === 'number' ? value : ''} />{feedback}</label>;
      })}{kind === 'products' && <fieldset className="staff-full-width"><legend>Imagem do produto</legend>{(preview || selected?.has_image === true && !removeImage) && <img className="product-photo" src={preview || `/api/v1/admin/products/${selected?.id}/image/`} alt="Prévia da imagem do produto" />}<label>JPEG, PNG ou WebP<input ref={imageInput} type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} aria-invalid={Boolean(fieldErrors.image)} onChange={event => { setImage(event.target.files?.[0] ?? null); setRemoveImage(false); }} /></label>{fieldErrors.image && <p className="error">{fieldErrors.image}</p>}{(image || selected?.has_image === true) && <button className="secondary" type="button" disabled={busy} onClick={() => { setImage(null); setRemoveImage(true); if (imageInput.current) imageInput.current.value = ''; }}>Remover imagem</button>}</fieldset>}{kind === 'products' && <fieldset className="staff-full-width"><legend>Vídeo do produto (opcional)</legend><p>MP4 ou MOV com H.264/AAC, ou WebM com VP8/VP9/AV1 e Opus/Vorbis. O servidor valida o conteúdo e o limite de envio.</p>{(videoPreview || selected?.has_video === true && !removeVideo) && <video className="staff-video-preview" src={videoPreview || `/api/v1/admin/products/${selected?.id}/video/`} controls playsInline preload="metadata" aria-label="Prévia do vídeo do produto" />}<label>Selecionar ou substituir vídeo<input ref={videoInput} type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" disabled={busy} aria-invalid={Boolean(fieldErrors.video)} onChange={event => { setVideo(event.target.files?.[0] ?? null); setRemoveVideo(false); }} /></label>{fieldErrors.video && <p className="error" role="alert">{fieldErrors.video}</p>}{(video || selected?.has_video === true) && <button className="secondary" type="button" disabled={busy} onClick={() => { setVideo(null); setRemoveVideo(true); if (videoInput.current) videoInput.current.value = ''; }}>Remover vídeo</button>}</fieldset>}<div className="actions"><button disabled={busy} type="submit">{busy ? 'Salvando…' : selected ? 'Salvar alterações' : `Cadastrar ${singular[kind]}`}</button><button className="secondary" type="button" disabled={busy} onClick={closeEditor}>Cancelar</button></div>
    </form>
    {selected && <button type="button" className="ui-danger" disabled={busy} onClick={() => { setEditorOpen(false); setDeactivating(true); }}>Desativar este cadastro</button>}

    </Editor>}{deactivating && selected && <ConfirmDialog title="Desativar cadastro?" description="O cadastro ficará inativo. Os pedidos e o histórico serão preservados." label="Desativar cadastro" close={() => { setDeactivating(false); closeEditor(); }} confirm={async reason => { await request(`/api/v1/admin/${kind}/${selected.id}/`, 'DELETE', { reason }); setReload(value => value + 1); setMessage('Cadastro desativado.'); }} />}</section>;
}

export function ResourceSelect({ name, label, kind, initial, disabled = false, required = true, menu, changed, error: fieldError }: { name: string; label: string; kind: string; initial: string; disabled?: boolean; required?: boolean; menu?: string | undefined; changed?: (value: string) => void; error?: string | undefined }) {
  const fieldId = useId();
  const [options, setOptions] = useState<Entity[]>([]);
  const [chosen, setChosen] = useState<Entity | null>(null);
  const [value, setValue] = useState(initial);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    const timer = window.setTimeout(() => {
      void request(`/api/v1/admin/${kind}/?page=${page}&search=${encodeURIComponent(search)}${menu ? `&menu=${menu}` : ''}`, 'GET', undefined, controller.signal).then(pageEntries).then(data => { if (!controller.signal.aborted) { setOptions(data.results); setNext(data.next); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar opções.'); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 200);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [kind, initial, page, search, menu]);
  useEffect(() => {
    if (!initial) return;
    const controller = new AbortController();
    void request(`/api/v1/admin/${kind}/${initial}/`, 'GET', undefined, controller.signal).then(entity).then(data => { if (!controller.signal.aborted) setChosen(data); }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar seleção.'); });
    return () => controller.abort();
  }, [kind, initial]);
  return <div className="staff-resource"><label htmlFor={fieldId}>{label}<select id={fieldId} disabled={disabled} name={name} required={required} aria-describedby={fieldError ? `${fieldId}-error` : undefined} aria-invalid={Boolean(fieldError)} value={value} onChange={event => { setValue(event.target.value); changed?.(event.target.value); setChosen(options.find(option => option.id === event.target.value) ?? null); }}><option value="">{required ? 'Selecione' : 'Nenhum'}</option>{chosen && !options.some(option => option.id === chosen.id) && <option value={chosen.id}>{chosen.name}</option>}{options.map(option => <option value={option.id} key={option.id}>{option.name}{option.active === false ? ' (desativado)' : ''}</option>)}</select></label>{(next || page > 1 || search) && <label>Filtrar opções<input value={search} maxLength={100} disabled={disabled} onChange={event => { setSearch(event.target.value); setPage(1); }} /></label>}{error && <p role="alert">{error}</p>}{fieldError && <p id={`${fieldId}-error`} className="error">{fieldError}</p>}<Pagination page={page} next={next} busy={loading || disabled} label={label} change={setPage} /></div>;

}

function UnitSelector({ context }: { context: StaffContext }) {
  const [units, setUnits] = useState<{ id: string; name: string; unit_id: string; unit_name: string }[]>([]);
  const [page, setPage] = useState(1); const [next, setNext] = useState(false);
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(''); const submitting = useRef(false);
  useEffect(() => { const controller = new AbortController(); setLoading(true); void request(`/api/v1/staff/units/?page=${page}`, 'GET', undefined, controller.signal).then(record).then(row => { if (!Array.isArray(row.results)) throw new Error('Resposta inválida.'); if (!controller.signal.aborted) { setUnits(row.results.map(value => { const item = record(value); return { id: text(item.id), name: text(item.name), unit_id: text(item.unit_id), unit_name: text(item.unit_name) }; })); setNext(typeof row.next === 'string'); setError(''); } }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar unidades.'); }).finally(() => { if (!controller.signal.aborted) setLoading(false); }); return () => controller.abort(); }, [page]);
  async function select(id: string) {
    if (submitting.current || !id || id === context.staff.id) return;
    submitting.current = true; setBusy(true); setError('');
    try { await request('/api/v1/staff/units/', 'POST', { membership_id: id }); window.location.assign('/admin/menu'); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível selecionar unidade.'); }
    finally { submitting.current = false; setBusy(false); }
  }
  if (units.length <= 1 && !next && page === 1) return error ? <p className="error" role="alert">{error}</p> : null;
  return <fieldset className="staff-resource"><legend>Unidade</legend><label>Selecionar unidade<select disabled={busy || loading} value={context.staff.id} onChange={event => { void select(event.target.value); }}>{!units.some(unit => unit.id === context.staff.id) && <option value={context.staff.id}>{context.unit_name}</option>}{units.map(unit => <option value={unit.id} key={unit.id}>{unit.unit_name}</option>)}</select></label>{error && <p className="error" role="alert">{error}</p>}<Pagination page={page} next={next} busy={busy || loading} label="Unidades autorizadas" change={setPage} /></fieldset>;
}

function MultiResource({ name, label, kind, initial, disabled }: { name: string; label: string; kind: string; initial: string[]; disabled: boolean }) {
  const [ids, setIds] = useState(initial);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!ids.length) return;
    const controller = new AbortController();
    async function load() {
      const entries: Entity[] = [];
      const query = new URLSearchParams(); ids.forEach(id => query.append('ids', id));
      for (let page = 1; page <= 2; page++) {
        const data = pageEntries(await request(`/api/v1/admin/${kind}/?${query}&page=${page}`, 'GET', undefined, controller.signal));
        entries.push(...data.results);
        if (!data.next) break;
      }
      if (!controller.signal.aborted) {
        setLabels(Object.fromEntries(entries.map(row => [row.id, row.name])));
        setError(entries.length === ids.length ? '' : 'Uma associação não está mais disponível. Revise antes de salvar.');
      }
    }
    void load().catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível conferir as associações.'); });
    return () => controller.abort();
  }, [ids, kind, retry]);
  return <fieldset className="staff-full-width" disabled={disabled}><legend>{label}</legend>{error && <p className="error" role="alert">{error}<button className="secondary" type="button" onClick={() => setRetry(value => value + 1)}>Tentar novamente</button></p>}<ResourceSelect key={ids.join(',')} name={`${name}-picker`} label={`Adicionar ${kind === 'options' ? 'opção' : 'grupo'}`} kind={kind} initial="" required={false} disabled={disabled} changed={id => { if (id && !ids.includes(id)) setIds(values => [...values, id]); }} /><ul className="staff-list">{ids.map(id => <li key={id}><input type="hidden" name={name} value={id} /><span>{labels[id] ?? 'Carregando seleção…'}</span><button className="secondary" type="button" disabled={disabled} onClick={() => setIds(values => values.filter(value => value !== id))}>Remover associação</button></li>)}</ul><p>A remoção da associação mantém o cadastro original. Opções já presentes em um grupo serão exibidas e cobradas uma única vez.</p></fieldset>;
}
