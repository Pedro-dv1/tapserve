import { useEffect, useState } from 'react';
import { ApiError, decodeAdmission, decodePublicContext, exchangePoint, request } from '../../lib/api';
import type { Admission, PublicContext } from '../../lib/api';
import { LoadingSkeleton } from '../../components/Interface';
import CustomerWorkspace from './CustomerWorkspace';

export default function CustomerScreen() {
  const [context, setContext] = useState<PublicContext | null>(null);
  const [pending, setPending] = useState<Admission | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let current = true;
    const controller = new AbortController();
    let timer = 0;
    const ready = (value: PublicContext) => {
      if (!current) return;
      try { sessionStorage.removeItem('tapserve:admission'); } catch { /* Access remains authorized without storage. */ }
      setPending(null); setError(''); setContext(value); setLoading(false);
      window.history.replaceState(null, '', '/customer');
    };
    const fail = (cause: unknown) => { if (current) { setError(cause instanceof Error ? cause.message : 'Não foi possível abrir o atendimento.'); setLoading(false); } };
    async function poll(identifier: string) {
      try {
        const value = decodeAdmission(await request(`/api/v1/public/admissions/${identifier}/`, 'GET', undefined, controller.signal));
        if (!current) return;
        setPending(value); setLoading(false); setError('');
        if (value.status === 'APPROVED') ready(decodePublicContext(await request(`/api/v1/public/admissions/${identifier}/claim/`, 'POST', {}, controller.signal)));
        else if (value.status === 'PENDING') timer = window.setTimeout(() => { void poll(identifier); }, 5000);
      } catch (cause: unknown) { if (!controller.signal.aborted) fail(cause); }
    }
    const token = window.location.pathname.startsWith('/a/') ? window.location.pathname.slice(3).replace(/\/$/, '') : null;
    if (token) {
      void exchangePoint(token).then(value => {
        if (!current) return;
        if ('admission_id' in value) {
          setPending(value); setLoading(false);
          try { sessionStorage.setItem('tapserve:admission', value.admission_id); } catch { /* Polling still works in this page. */ }
          window.history.replaceState(null, '', '/customer');
          void poll(value.admission_id);
        } else ready(value);
      }).catch((cause: unknown) => fail(cause instanceof ApiError && cause.status === 404 ? new Error('Este link não está disponível. Leia o QR Code atual ou peça ajuda à equipe.') : cause));
    } else {
      let identifier: string | null = null;
      try { identifier = sessionStorage.getItem('tapserve:admission'); } catch { /* No stored pending request. */ }
      if (identifier && /^[0-9a-f-]{36}$/.test(identifier)) void poll(identifier);
      else void request('/api/v1/public/context/', 'GET', undefined, controller.signal).then(decodePublicContext).then(ready).catch(fail);
    }
    return () => { current = false; controller.abort(); window.clearTimeout(timer); };
  }, [attempt]);
  return <main className="customer-root">{!context && <img className="wordmark" src="/brand/TapServe_logo_wordmark.svg" alt="TapServe" />}
    {loading && <LoadingSkeleton variant="menu" />}
    {pending && !context && <section aria-live="polite"><h1>{pending.status === 'PENDING' || pending.status === 'APPROVED' ? 'Aguardando autorização da equipe' : 'Solicitação de acesso encerrada'}</h1><p>{pending.status === 'PENDING' ? 'Mostre este código a um funcionário para autorizar este dispositivo na mesa.' : pending.status === 'APPROVED' ? 'Autorização recebida. Abrindo seu atendimento…' : 'Esta solicitação foi recusada, revogada ou expirou. Peça ajuda à equipe e leia novamente o QR Code ou NFC.'}</p><p>Código da solicitação: <strong>{pending.verification_code}</strong></p><p>O acesso só será liberado após aprovação. Nenhum pedido foi enviado.</p></section>}
    {error && <section><h1>Não foi possível abrir o atendimento</h1><p className="error" role="alert">{error}</p><button disabled={loading} onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1); }}>Tentar novamente</button></section>}
    {context && <CustomerWorkspace key={context.device_id} context={context} />}
  </main>;
}
