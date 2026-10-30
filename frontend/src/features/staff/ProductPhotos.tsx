import { useAutoRefresh } from '../../lib/useAutoRefresh';
import { formSaveResult } from '../../lib/formChanges';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, record, request, text } from '../../lib/api';
import { randomUUID } from '../../lib/uuid';
import type { Photo } from '../customer/menuData';
import { Editor } from './StaffUI';
import ConfirmDialog from '../../components/ConfirmDialog';

function decodePhoto(value: unknown): Photo {
  const row = record(value);
  if (typeof row.position !== 'number' || !Number.isInteger(row.position) || row.position < 0) throw new Error('Galeria inválida.');
  return { id: text(row.id), alt_text: text(row.alt_text), position: row.position };
}
const sortPhotos = (photos: Photo[]) => photos.sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));

export default function ProductPhotos({ product, close }: { product: { id: string; name: string }; close: () => void }) {
  const [photos, setPhotos] = useState<Photo[]>([]), [loading, setLoading] = useState(true);
  const [error, setError] = useState(''), [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false), [reload, setReload] = useState(0);
  const [removing, setRemoving] = useState<Photo | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const pending = useRef<FormData | null>(null), saving = useRef(false);
  useAutoRefresh(() => setReload(value => value + 1));
  const uploadPosition = useRef<number | null>(null);
  const base = `/api/v1/admin/products/${product.id}/photos/`;
  useEffect(() => {
    const controller = new AbortController();
    void request(base, 'GET', undefined, controller.signal).then(value => {
      if (!Array.isArray(value)) throw new Error('Galeria inválida.');
      const rows = value.map(decodePhoto);
      if (!controller.signal.aborted) { uploadPosition.current ??= rows.length; setPhotos(rows); setError(''); }
    }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar fotos.'); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [base, reload]);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (saving.current) return;
    const form = event.currentTarget;
    const body = pending.current ?? new FormData(form);
    if (!pending.current) body.set('idempotency_key', randomUUID());
    pending.current = body; saving.current = true; setBusy(true); setError(''); setMessage('');
    try {
      const photo = decodePhoto(await request(base, 'POST', body));
      setPhotos(values => sortPhotos([...values.filter(value => value.id !== photo.id), photo]));
      pending.current = null; setUncertain(false); form.reset();
      uploadPosition.current = photos.length + (photos.some(value => value.id === photo.id) ? 0 : 1);
      const position = form.elements.namedItem('position');
      if (position instanceof HTMLInputElement) { position.defaultValue = String(uploadPosition.current); position.value = String(uploadPosition.current); }
      formSaveResult(form, true); setMessage('Foto adicionada.');
    }
    catch (cause: unknown) {
      formSaveResult(form, false); if (!uncertain && cause instanceof ApiError && cause.status >= 400 && cause.status < 500) pending.current = null;
      setUncertain(pending.current !== null); setError(cause instanceof Error ? cause.message : 'Não foi possível enviar a foto.');
    } finally { saving.current = false; setBusy(false); }
  }
  async function update(event: FormEvent<HTMLFormElement>, photo: Photo) {
    event.preventDefault(); if (saving.current) return;
    const form = event.currentTarget; const data = new FormData(form);
    saving.current = true; setBusy(true); setError(''); setMessage('');
    try {
      const updated = decodePhoto(await request(`${base}${photo.id}/`, 'PATCH', { alt_text: data.get('alt_text'), position: Number(data.get('position')) }));
      setPhotos(values => sortPhotos(values.map(value => value.id === updated.id ? updated : value)));
      for (const [name, value] of Object.entries(updated)) { const input = form.elements.namedItem(name); if (input instanceof HTMLInputElement) input.value = String(value); }
      formSaveResult(form, true); setMessage('Foto atualizada.');
    }
    catch (cause: unknown) { formSaveResult(form, false); setError(cause instanceof Error ? cause.message : 'Não foi possível atualizar.'); }
    finally { saving.current = false; setBusy(false); }
  }
  return <Editor title={`Fotos de ${product.name}`} close={close} busy={busy}>
    <p>A capa e o vídeo são editados no produto. Adicione até seis fotos à galeria; a menor ordem aparece primeiro. Imagens de até 2 MiB e 4 megapixels, sem animação.</p>
    {error && <p className="error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}

    {loading ? <p role="status">Carregando fotos…</p> : <div className="staff-photo-grid">{photos.map(photo => <form key={photo.id} onSubmit={event => { void update(event, photo); }}><img src={`${base}${photo.id}/`} width={160} height={120} alt={photo.alt_text || product.name} loading="lazy" /><fieldset disabled={busy || uncertain}><label>Descrição da foto<input name="alt_text" maxLength={200} defaultValue={photo.alt_text} /></label><label>Ordem<input name="position" type="number" min={0} max={32767} required defaultValue={photo.position} /></label><div className="actions"><button type="submit">Salvar foto</button><button className="ui-danger" type="button" onClick={() => setRemoving(photo)}>Remover foto</button></div></fieldset></form>)}</div>}
    {!loading && <form onSubmit={event => { void upload(event); }}><h3>Adicionar foto</h3><fieldset disabled={busy || uncertain || photos.length >= 6}><label>Imagem<input name="image" type="file" accept="image/jpeg,image/png,image/webp" required /></label><label>Descrição da foto<input name="alt_text" maxLength={200} /></label><label>Ordem<input name="position" type="number" min={0} max={32767} defaultValue={uploadPosition.current ?? 0} required /></label></fieldset>{uncertain && <p role="status">Envio pendente. Repita com os mesmos dados para consultar ou confirmar sem duplicar a foto.</p>}<button type="submit" disabled={busy || photos.length >= 6 && !uncertain}>{busy ? 'Enviando…' : uncertain ? 'Repetir o mesmo envio' : 'Adicionar foto'}</button></form>}
    {removing && <ConfirmDialog title="Remover foto?" description="A foto será retirada da galeria do produto." label="Remover foto" close={() => setRemoving(null)} confirm={async () => { await request(`${base}${removing.id}/`, 'DELETE'); setPhotos(values => values.filter(value => value.id !== removing.id)); setMessage('Foto removida com sucesso.'); }} />}
  </Editor>;
}
