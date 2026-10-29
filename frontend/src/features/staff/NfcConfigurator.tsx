import { useEffect, useRef, useState } from 'react';
import { lockTag, nfcCapabilities, nfcError, verifyTag, writeTag } from './nfc';

export default function NfcConfigurator({ url, enabled }: { url: string; enabled: boolean }) {
  const [confirmLock, setConfirmLock] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('Estado físico não verificado.');
  const [error, setError] = useState('');
  const operation = useRef<AbortController | null>(null);
  const { supported, canLock } = nfcCapabilities(window);
  useEffect(() => () => operation.current?.abort(), [url, enabled]);
  async function run(action: 'write' | 'verify' | 'lock') {
    if (operation.current || !supported || !enabled || !window.NDEFReader) return;

    const controller = new AbortController(); operation.current = controller;
    setBusy(true); setError(''); setStatus(action === 'write' ? 'Aproxime a tag para gravar o link.' : 'Aproxime a tag para conferir o conteúdo.');
    const timeout = window.setTimeout(() => controller.abort(), 45_000);
    try {
      const reader = new window.NDEFReader();
      if (action === 'write') { await writeTag(reader, url, controller.signal); setStatus('Tag gravada. O conteúdo ainda não foi verificado; use Verificar gravação.'); }
      else if (action === 'lock') {
        setStatus('Aproxime a mesma tag para conferir o link e bloquear a escrita. Mantenha-a próxima até terminar.');
        await lockTag(reader, url, controller.signal);
        setStatus('A API confirmou o bloqueio permanente da tag apresentada. O link pode continuar sendo desativado no TapServe.');
      } else {
        await verifyTag(reader, url, controller.signal);
        setStatus('Gravação verificada: o link lido corresponde a este ponto.');
      }
    } catch (cause: unknown) { setError(nfcError(cause)); setStatus('Operação não confirmada. Estado físico não verificado.'); }
    finally { window.clearTimeout(timeout); controller.abort(); operation.current = null; setBusy(false); }
  }
  return <details className="nfc-config"><summary>Configurar NFC</summary><p>Link que será gravado:</p><input aria-label="Link da tag NFC" readOnly value={url} />{!enabled && <p>Ative o ponto, o link e a opção NFC para configurar uma tag.</p>}{!supported ? <p>Este navegador não oferece gravação Web NFC. Copie o link acima e grave-o como URL em um aplicativo NFC compatível. A leitura de uma tag já gravada pode abrir o atendimento normalmente.</p> : <p>Use uma tag NDEF compatível, NFC ativado e mantenha a tela desbloqueada. O navegador solicitará permissão.</p>}<div className="actions"><button type="button" disabled={!supported || !enabled || busy} onClick={() => { void run('write'); }}>Gravar tag NFC</button><button className="secondary" type="button" disabled={!supported || !enabled || busy} onClick={() => { void run('verify'); }}>Verificar gravação</button>{busy && <button className="secondary" type="button" onClick={() => operation.current?.abort()}>Cancelar operação NFC</button>}</div><p role="status">{status}</p>{error && <p className="error" role="alert">{error}</p>}<details className="staff-destructive"><summary>Bloqueio permanente de escrita</summary><p>Verifique o conteúdo antes de bloquear. O bloqueio pode ser irreversível e não comprova que a tag continuará no local. Apresente a mesma tag durante toda a operação.</p><button className="ui-danger" type="button" disabled={!canLock || !enabled || busy} onClick={() => setConfirmLock(true)}>Tornar tag permanentemente somente leitura</button>{confirmLock && <div className="discard-changes" role="alert"><p>Tornar esta tag permanentemente somente leitura? A operação pode ser irreversível. Mantenha a mesma tag próxima até terminar.</p><div className="actions"><button className="secondary" type="button" disabled={busy} onClick={() => setConfirmLock(false)}>Voltar</button><button className="ui-danger" type="button" disabled={busy || !canLock} onClick={() => { setConfirmLock(false); void run('lock'); }}>Confirmar bloqueio permanente</button></div></div>}{!canLock && <p>Bloqueio físico indisponível neste navegador ou dispositivo.</p>}</details></details>;
}
