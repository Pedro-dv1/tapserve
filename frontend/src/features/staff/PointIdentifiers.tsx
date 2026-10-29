import Toast from '../../components/Toast';
import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, decodePoint, request } from '../../lib/api';
import type { Point } from '../../lib/api';
import NfcConfigurator from './NfcConfigurator';

export default function PointIdentifiers({ point, url, changed }: { point: Point; url: string; changed: (point: Point) => void }) {
  const [rotation, setRotation] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const mutation = useRef(false);
  async function configure(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (mutation.current) return;
    const form = new FormData(event.currentTarget);
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    const action = submitter instanceof HTMLButtonElement ? submitter.value : 'ASSOCIATE';
    const body = { action, reason: form.get('reason') ?? '', expected_version: point.token_version, confirmed: action === 'ROTATE', ...(action === 'ASSOCIATE' ? { url: form.get('url') } : {}) };
    if (action === 'ROTATE') { setRotation(body); return; }
    await apply(body);
  }
  async function apply(body: Record<string, unknown>) {
    if (mutation.current) return;
    const action = body.action;

    mutation.current = true; setBusy(true); setError(''); setMessage('');
    try { const result = decodePoint(await request(`/api/v1/admin/service-points/${point.id}/identifier/`, 'POST', body)); changed(result); setRotation(null); setMessage(action === 'ROTATE' ? 'Novo identificador gerado. Substitua os QR e regrave ou substitua as tags antigas.' : 'QR existente conferido e associado a este ponto.'); }
    catch (cause: unknown) { setError(cause instanceof ApiError ? cause.fields.url ?? cause.message : cause instanceof Error ? cause.message : 'Não foi possível configurar o identificador.'); }
    finally { mutation.current = false; setBusy(false); }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(url); setMessage('Link copiado.'); setError(''); }
    catch { setError('Não foi possível copiar automaticamente. Selecione e copie o link acima.'); }
  }
  const local = ['127.0.0.1', 'localhost', '[::1]'].includes(new URL(url).hostname);
  return <section className="point-identifiers" aria-label={`QR Code e NFC de ${point.name}`}><h3>QR Code e NFC · {point.name}</h3><p>{point.access_enabled && point.active ? 'Identificador ativo' : 'Identificador indisponível para novos acessos'}</p><label>Link público de acesso<input readOnly value={url} onFocus={event => event.currentTarget.select()} /></label>{local && <p role="status">Link de desenvolvimento. Configure PUBLIC_APP_ORIGIN com o domínio público HTTPS antes de imprimir ou distribuir.</p>}<div className="actions"><button className="secondary" type="button" onClick={() => { void copy(); }}>Copiar link</button><a href={url} target="_blank" rel="noreferrer">Abrir acesso</a></div>{point.qr_enabled && <><img className="point-qr-preview" src={`/api/v1/admin/service-points/${point.id}/qr/?v=${point.token_version}`} alt={`QR Code para ${point.name}`} /><p><a href={`/api/v1/admin/service-points/${point.id}/qr/`} download>Baixar QR Code para impressão (SVG)</a></p></>}<NfcConfigurator key={url} url={url} enabled={point.active && point.access_enabled && point.nfc_enabled} /><details><summary>Associar QR existente ou substituir identificador</summary><form onSubmit={event => { void configure(event); }}><p>Para associar um QR existente, cole o conteúdo lido. Ele deve conter o link atual deste ponto no domínio configurado. Links de outra mesa não são transferidos.</p><label>Link do QR existente<input name="url" type="url" maxLength={500} disabled={busy} /></label><label>Motivo<input name="reason" maxLength={300} disabled={busy} /></label><div className="actions"><button className="secondary" type="submit" value="ASSOCIATE" disabled={busy}>Associar QR existente</button><button className="ui-danger" type="submit" value="ROTATE" disabled={busy}>Gerar novo identificador</button></div></form></details>{rotation && <div className="discard-changes" role="alert"><p>Invalidar o link já distribuído? Os QR e tags antigos precisarão ser substituídos. Os dispositivos autorizados continuarão no atendimento.</p><div className="actions"><button type="button" className="secondary" disabled={busy} onClick={() => setRotation(null)}>Voltar</button><button type="button" className="ui-danger" disabled={busy} onClick={() => { void apply(rotation); }}>Confirmar regeneração</button></div></div>}{error && <p className="error" role="alert">{error}</p>}<Toast message={message} clear={setMessage} /></section>;
}
