import Toast from '../../components/Toast';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, record, request, text } from '../../lib/api';
import { Button, LoadingSkeleton } from '../../components/Interface';
import { Editor } from './StaffUI';
import Feedback from '../../components/Feedback';

function decodeLogo(value: unknown) {
  const data = record(value);
  if (data.logo_url !== null && !/^\/api\/v1\/admin\/unit-logo\/image\/\?v=[0-9a-f]{16}$/.test(text(data.logo_url)) || typeof data.max_bytes !== 'number' || !Number.isSafeInteger(data.max_bytes) || data.max_bytes < 1) throw new Error('Não foi possível conferir a logo.');
  return { url: data.logo_url === null ? null : text(data.logo_url), maxBytes: data.max_bytes };
}

export default function UnitBranding() {
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [logo, setLogo] = useState<ReturnType<typeof decodeLogo> | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reload, setReload] = useState(0);
  const mutation = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { const controller = new AbortController(); void request('/api/v1/admin/unit-logo/', 'GET', undefined, controller.signal).then(decodeLogo).then(setLogo).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível consultar a logo.'); }); return () => controller.abort(); }, [reload]);
  useEffect(() => {
    if (!file) { setPreview(''); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  function select(selected: File | undefined) {
    setFile(null); setError(''); setMessage(''); setFailed(false);
    if (!selected || !logo) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) || selected.size > logo.maxBytes) { setError('Use uma imagem PNG, JPEG ou WebP dentro do limite informado.'); if (input.current) input.current.value = ''; return; }
    setFile(selected);
  }
  async function save(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault(); if (mutation.current || !logo || event && !file) return;
    mutation.current = true; setBusy(true); setError(''); setMessage('');
    const data = new FormData(); if (event && file) data.set('image', file);
    try {
      setLogo(decodeLogo(await request('/api/v1/admin/unit-logo/', event ? 'PUT' : 'DELETE', event ? data : undefined)));
      setFile(null); setFailed(false); if (input.current) input.current.value = '';
      setMessage('Alterações salvas.'); setEditing(false); setRemoving(false);
    } catch (cause: unknown) { setError(cause instanceof ApiError && cause.fields.image ? cause.fields.image : cause instanceof Error ? cause.message : 'Não foi possível salvar a logo.'); }
    finally { mutation.current = false; setBusy(false); }
  }
  function close() { setEditing(false); setFile(null); setFailed(false); setRemoving(false); }
  const source = preview || logo?.url;
  return <section className="unit-branding"><h1>Identidade visual</h1><p>A logo desta unidade aparece nas boas-vindas dos clientes.</p>{error && <Feedback tone="error">{error}</Feedback>}<Toast message={message} clear={setMessage} />{logo && <><p>{logo.url ? 'Logo configurada.' : 'Nenhuma logo configurada.'}</p><Button secondary onClick={() => setEditing(true)}>Editar logo</Button></>}{!logo ? <>{!error && <LoadingSkeleton variant="settings" />}<Button secondary onClick={() => setReload(value => value + 1)}>Consultar logo</Button></> : editing && <Editor title="Editar logo do estabelecimento" close={close} busy={busy}><form className="staff-editor" onSubmit={event => { void save(event); }} aria-busy={busy}>{source && !failed ? <img className="establishment-logo logo-preview" src={source} alt={preview ? 'Prévia da nova logo' : 'Logo atual da unidade'} onError={() => setFailed(true)} /> : <p>{failed ? 'Não foi possível exibir esta imagem. Escolha outra para substituir.' : 'Nenhuma logo configurada.'}</p>}<label>Logo do estabelecimento<input ref={input} type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={event => select(event.target.files?.[0])} /></label><p>PNG, JPEG ou WebP, até {(logo.maxBytes / 1024 / 1024).toLocaleString('pt-BR')} MiB e 4 megapixels. A proporção e a transparência serão preservadas.</p><div className="actions"><Button type="submit" disabled={busy || !file || failed}>{busy ? 'Salvando…' : 'Salvar alterações'}</Button>{file && <Button secondary type="button" disabled={busy} onClick={() => { setFile(null); setFailed(false); if (input.current) input.current.value = ''; }}>Descartar prévia</Button>}{logo.url && <Button secondary type="button" disabled={busy} className="ui-danger" onClick={() => setRemoving(true)}>Remover logo</Button>}<Button secondary type="button" disabled={busy} onClick={close}>Cancelar</Button></div>{removing && <div className="discard-changes" role="alert"><p>Remover a logo atual?</p><div className="actions"><Button secondary type="button" disabled={busy} onClick={() => setRemoving(false)}>Voltar</Button><Button className="ui-danger" type="button" disabled={busy} onClick={() => { void save(); }}>Confirmar remoção</Button></div></div>}</form></Editor>}</section>;
}
