import { lazy, Suspense, useEffect, useState } from 'react';
import { ApiError, decodeContext, request } from '../../lib/api';
import type { StaffContext } from '../../lib/api';
import { ErrorState, Icon, LoadingSkeleton } from '../../components/Interface';
import AdminLayout from './AdminLayout';
import AttendantLayout from './AttendantLayout';
import StaffLogin from './StaffLogin';
import { isManagement, staffPages, staffPath } from './navigation';
import '../../design-system/staff.css';

const StaffManagement = lazy(() => import('./StaffManagement'));
const PointManagement = lazy(() => import('./PointManagement'));
const CatalogManagement = lazy(() => import('./CatalogManagement'));
const Operation = lazy(() => import('./Operation'));
const StaffOrders = lazy(() => import('./StaffOrders'));
const StaffCalls = lazy(() => import('./StaffCalls'));
const Production = lazy(() => import('./Production'));
const OrderPolicy = lazy(() => import('./OrderPolicy'));

export default function StaffScreen() {
  const [context, setContext] = useState<StaffContext | null>(null);
  const [loading, setLoading] = useState(window.location.pathname !== '/staff/login');
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const path = window.location.pathname.replace(/\/$/, '');
  const loadingVariant = path === '/staff/production' ? 'production' : path === '/staff/operation' ? 'operation' : path === '/staff/menu' ? 'catalog' : path === '/staff/points' ? 'points' : path === '/staff/settings' ? 'settings' : 'staff';
  useEffect(() => {
    if (path === '/staff/login') return;
    const controller = new AbortController(); let inFlight = false;
    function verify() {
      if (inFlight || document.visibilityState === 'hidden') return;
      inFlight = true;
      void request('/api/v1/staff/me/', 'GET', undefined, controller.signal).then(decodeContext).then(value => { if (!controller.signal.aborted) { setContext(value); setError(''); } }).catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && [401, 403].includes(cause.status)) { setContext(null); window.location.replace('/staff/login'); }
        else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar seu acesso.');
      }).finally(() => { inFlight = false; if (!controller.signal.aborted) setLoading(false); });
    }
    void verify(); window.addEventListener('pageshow', verify); document.addEventListener('visibilitychange', verify);
    return () => { controller.abort(); window.removeEventListener('pageshow', verify); document.removeEventListener('visibilitychange', verify); };

  }, [attempt, path]);
  async function leave() {
    if (busy) return;
    setBusy(true); setError('');
    try { await request('/api/v1/staff/logout/', 'POST', {}); setContext(null); window.location.replace('/staff/login'); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : 'Não foi possível sair.'); }
    finally { setBusy(false); }
  }
  if (path === '/staff/login') return <StaffLogin />;
  if (!context) return <main><img className="wordmark" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" />{loading ? <LoadingSkeleton variant={loadingVariant} /> : <ErrorState message={error || 'Não foi possível abrir seu acesso.'} retry={() => { setError(''); setLoading(true); setAttempt(value => value + 1); }} />}</main>;
  const pages = staffPages(context);
  const resolved = staffPath(context, path);
  const current = resolved === '/staff/more' ? { href: resolved, label: 'Mais', icon: 'more' as const, group: 'Expediente', permissions: [], strong: false } : pages.find(page => page.href === resolved);
  const area = current?.href.replace(/^\/(admin|staff)\//, '');
  const Layout = isManagement(context) ? AdminLayout : AttendantLayout;
  return <Layout context={context} pages={pages} current={current} busy={busy} leave={() => { void leave(); }}>
    {error && <ErrorState message={error} />}
    <Suspense fallback={<LoadingSkeleton variant={loadingVariant} />}>
      {area === 'orders' ? <StaffOrders context={context} /> : area === 'calls' ? <StaffCalls context={context} /> : area === 'more' ? <section><h1>Mais</h1><nav className="staff-more-links" aria-label="Outras áreas autorizadas">{pages.filter(page => !['/staff/operation', '/staff/orders', '/staff/calls'].includes(page.href)).map(page => <a href={page.href} key={page.href}><Icon name={page.icon} />{page.label}<Icon name="chevron" /></a>)}</nav>{pages.every(page => ['/staff/operation', '/staff/orders', '/staff/calls'].includes(page.href)) && <p>Nenhuma função secundária disponível para seu acesso.</p>}</section> : area === 'operation' ? <Operation context={context} /> : area === 'production' ? <Production /> : area === 'menu' ? <CatalogManagement context={context} /> : area === 'points' ? <PointManagement /> : area === 'settings' ? <OrderPolicy /> : area === 'staff' ? <StaffManagement context={context} /> : <section><h1>Área indisponível</h1><p>Esta página não está disponível para seu acesso. Selecione uma Área no menu da unidade.</p></section>}
    </Suspense>
  </Layout>;
}
