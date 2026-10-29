import { LoadingSkeleton } from '../components/Interface';
import { lazy, Suspense, useEffect, useState } from 'react';
import { getHealth } from '../lib/api';
import { appRoute } from './routes';
import NotFound from './NotFound';

type Status = { kind: 'loading' } | { kind: 'ready' } | { kind: 'error'; message: string };

export function App() {
  const [path, setPath] = useState(window.location.pathname);
  const [entering, setEntering] = useState(() => appRoute(window.location.pathname) === 'customer' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => { const changed = () => setPath(window.location.pathname); window.addEventListener('popstate', changed); return () => window.removeEventListener('popstate', changed); }, []);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const reduced = () => { if (media.matches) setEntering(false); };
    reduced();
    media.addEventListener('change', reduced);
    return () => media.removeEventListener('change', reduced);
  }, []);
  const route = appRoute(path);
  if (route === 'customer') return <>{entering && <div className="customer-entrance" role="status" aria-label="Abrindo TapServe" onAnimationEnd={event => { if (event.target === event.currentTarget) setEntering(false); }}><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /></div>}<div hidden={entering}><Suspense fallback={<main><LoadingSkeleton variant="menu" /></main>}><CustomerScreen /></Suspense></div></>;
  if (route === 'platform') return <Suspense fallback={<main><LoadingSkeleton variant="staff" /></main>}><PlatformScreen /></Suspense>;
  if (route === 'staff') {
    return <Suspense fallback={<main><LoadingSkeleton variant="staff" /></main>}><StaffScreen /></Suspense>;
  }
  return route === 'health' ? <HealthScreen /> : <main><NotFound /></main>;
}

const StaffScreen = lazy(() => import('../features/staff/StaffScreen'));
const PlatformScreen = lazy(() => import('../features/staff/PlatformScreen'));
const CustomerScreen = lazy(() => import('../features/customer/CustomerScreen'));

function HealthScreen() {
  const [status, setStatus] = useState<Status>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(new DOMException('Tempo de conexão esgotado.', 'TimeoutError')), 10_000);
    void getHealth(controller.signal).then((health) => {
      setStatus(health.status === 'ok' && health.database === 'ok'
        ? { kind: 'ready' }
        : { kind: 'error', message: 'O serviço está indisponível.' });
    }).catch((error: unknown) => {
      if (controller.signal.aborted && controller.signal.reason instanceof DOMException && controller.signal.reason.name === 'AbortError') return;
      setStatus({ kind: 'error', message: error instanceof Error ? error.message : 'Não foi possível conectar. Tente novamente.' });
    }).finally(() => window.clearTimeout(timeout));
    return () => { controller.abort(); window.clearTimeout(timeout); };
  }, [attempt]);

  return <main>
    <img className="wordmark" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" />
    <h1>Conexão com o TapServe</h1>
    <div aria-live="polite" aria-busy={status.kind === 'loading'}>
      {status.kind === 'loading' && <LoadingSkeleton variant="health" />}
      {status.kind === 'ready' && <p>Serviço e banco de dados conectados.</p>}
      {status.kind === 'error' && <p role="alert">{navigator.onLine ? status.message : 'Você está sem conexão. Conecte-se e tente novamente.'}</p>}
    </div>
    <button disabled={status.kind === 'loading'} onClick={() => { setStatus({ kind: 'loading' }); setAttempt((value) => value + 1); }}>Verificar novamente</button>
    <p><a href="/staff/login">Acesso da equipe</a></p>
  </main>;
}
