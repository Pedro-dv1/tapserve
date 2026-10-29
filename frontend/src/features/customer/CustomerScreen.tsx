import { useEffect, useState } from 'react';
import { ApiError, decodePublicContext, exchangePoint, request } from '../../lib/api';
import type { PublicContext } from '../../lib/api';
import { LoadingSkeleton } from '../../components/Interface';
import CustomerWorkspace from './CustomerWorkspace';

export default function CustomerScreen() {
  const [context, setContext] = useState<PublicContext | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let current = true;
    const token = window.location.pathname.startsWith('/a/') ? window.location.pathname.slice(3).replace(/\/$/, '') : null;
    const promise = token ? exchangePoint(token) : request('/api/v1/public/context/').then(decodePublicContext);
    void promise.then(data => {
      if (!current) return;
      setContext(data);
      if (token) window.history.replaceState(null, '', '/customer');
    }).catch((cause: unknown) => { if (current) setError(token && cause instanceof ApiError && cause.status === 404 ? 'Este link de mesa não está disponível. Leia o QR Code atual ou peça à equipe para conferir o identificador.' : cause instanceof Error ? cause.message : 'Não foi possível abrir o atendimento.'); }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [attempt]);
  return <main className="customer-root">{!context && <img className="wordmark" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" />}
    {loading && <LoadingSkeleton variant={window.location.pathname.includes('/products/') ? 'product' : window.location.pathname.endsWith('/orders') ? 'orders' : window.location.pathname.endsWith('/table') ? 'table' : 'menu'} />}
    {error && <><h1>Não foi possível abrir o atendimento</h1><p className="error" role="alert">{error}</p><p>Se o acesso expirou, abra novamente o NFC ou QR do ponto. Para o limite de dispositivos, solicite ajuda à equipe.</p><button disabled={loading} onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1); }}>Tentar novamente</button></>}
    {context && <CustomerWorkspace key={context.device_id} context={context} />}
  </main>;
}
