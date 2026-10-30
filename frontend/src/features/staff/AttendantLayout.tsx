import { OrderAttention } from './OrderAttention';
import type { ReactNode } from 'react';
import type { StaffContext } from '../../lib/api';
import { Icon } from '../../components/Interface';
import AccountMenu from './AccountMenu';
import MobileNavigation from './MobileNavigation';
import type { StaffPage } from './navigation';

export default function AttendantLayout({ context, pages, current, busy, leave, children }: { context: StaffContext; pages: StaffPage[]; current: StaffPage | undefined; busy: boolean; leave: () => void; children: ReactNode }) {
  const primary = ['/staff/operation', '/staff/orders', '/staff/calls'].flatMap(href => pages.filter(page => page.href === href));
  return <div className="staff-shell attendant-shell"><a className="sr-only staff-skip" href="#staff-content">Ir para o conteúdo</a><aside className="staff-sidebar"><a className="staff-brand" href="/staff/operation"><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /></a><div className="staff-unit"><strong>{context.unit_name}</strong><span>{context.company_name}</span></div><nav className="staff-navigation" aria-label="Atendimento da unidade">{primary.map(page => <a key={page.href} href={page.href} aria-current={current?.href === page.href ? 'page' : undefined}><span className="navigation-icon"><Icon name={page.icon} /><OrderAttention href={page.href} /></span>{page.label}</a>)}<a href="/staff/more" aria-current={current?.href === '/staff/more' ? 'page' : undefined}><Icon name="more" />Mais</a></nav></aside><div className="attendant-workspace"><header className="attendant-header"><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /><AccountMenu context={context} busy={busy} leave={leave} /></header><main className="staff-main" id="staff-content">{children}</main></div><MobileNavigation pages={pages} current={current?.href} /></div>;
}
