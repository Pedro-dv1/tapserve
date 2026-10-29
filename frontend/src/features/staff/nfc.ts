export type Reading = { serialNumber: string; message: { records: { recordType: string; data: DataView }[] } };
export type NfcReader = {
  write: (message: { records: { recordType: 'url'; data: string }[] }, options: { signal: AbortSignal }) => Promise<void>;
  scan: (options: { signal: AbortSignal }) => Promise<void>;
  makeReadOnly?: (options: { signal: AbortSignal }) => Promise<void>;
  onreading: ((event: Reading) => void) | null;
  onreadingerror: (() => void) | null;
};
declare global { interface Window { NDEFReader?: { new(): NfcReader; prototype: NfcReader } } }

export function nfcCapabilities(host: Pick<Window, 'isSecureContext' | 'NDEFReader'>) {
  const supported = host.isSecureContext && Boolean(host.NDEFReader);
  return { supported, canLock: supported && Boolean(host.NDEFReader?.prototype.makeReadOnly) };
}

export function nfcError(error: unknown): string {
  const name = error instanceof Error ? error.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Permissão NFC negada. Autorize o acesso em um navegador compatível usando HTTPS.';
  if (name === 'NotSupportedError') return 'Dispositivo ou tag incompatível com esta operação NFC.';
  if (name === 'NotReadableError') return 'Não foi possível acessar o NFC. Confira se ele está ativado e se a tag está próxima.';
  if (name === 'NetworkError') return 'Falha de comunicação com a tag. Mantenha-a próxima e tente novamente.';
  if (name === 'AbortError') return 'Operação cancelada ou tempo esgotado. O estado físico da tag não foi confirmado.';
  return error instanceof Error ? error.message : 'Falha na operação NFC. O estado físico não foi confirmado.';
}

export function writeTag(reader: NfcReader, url: string, signal: AbortSignal) {
  return reader.write({ records: [{ recordType: 'url', data: url }] }, { signal });
}

export function verifyTag(reader: NfcReader, url: string, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const cleanup = () => { reader.onreading = null; reader.onreadingerror = null; signal.removeEventListener('abort', aborted); };
    const aborted = () => { cleanup(); reject(new DOMException('Cancelado', 'AbortError')); };
    if (signal.aborted) { aborted(); return; }
    signal.addEventListener('abort', aborted, { once: true });
    reader.onreading = event => {
      const records = event.message.records;
      const matches = records.length === 1 && records[0]?.recordType === 'url' && new TextDecoder().decode(records[0].data) === url;
      cleanup();
      if (matches) resolve(); else reject(new Error('O conteúdo lido não corresponde ao link deste ponto. Grave e verifique novamente.'));
    };
    reader.onreadingerror = () => { cleanup(); reject(new Error('Tag ilegível ou incompatível. Tente aproximá-la novamente.')); };
    void reader.scan({ signal }).catch(error => { cleanup(); reject(error); });
  });
}

export async function lockTag(reader: NfcReader, url: string, signal: AbortSignal) {
  if (!reader.makeReadOnly) throw new Error('Bloqueio físico não suportado neste dispositivo.');
  await verifyTag(reader, url, signal);
  await reader.makeReadOnly({ signal });
}
