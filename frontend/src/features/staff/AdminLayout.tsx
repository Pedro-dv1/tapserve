import { OrderAttention } from './OrderAttention';
import type { ReactNode } from 'react';
import type { StaffContext } from '../../lib/api';
import { Icon } from '../../components/Interface';
import AccountMenu from './AccountMenu';
import type { StaffPage } from './navigation';

export default function AdminLayout({ context, pages, current, busy, leave, children }: { context: StaffContext; pages: StaffPage[]; current: StaffPage | undefined; busy: boolean; leave: () => void; children: ReactNode }) {
  const navigation = <nav className="staff-navigation" aria-label="Administração da unidade">{['Expediente', 'Gestão'].map(group => <div key={group}><h2>{group}</h2>{pages.filter(page => page.group === group).map(page => <a href={page.href} key={page.href} aria-current={current?.href === page.href ? 'page' : undefined}><span className="navigation-icon"><Icon name={page.icon} /><OrderAttention href={page.href} /></span>{page.label}</a>)}</div>)}{context.auth_strength !== 'password' && <a href="/staff/login">Entrar com senha para gestão</a>}</nav>;
  return <div className="staff-shell admin-shell"><a className="sr-only staff-skip" href="#staff-content">Ir para o conteúdo</a><aside className="staff-sidebar"><a className="staff-brand" href="/admin/operation"><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /></a><div className="staff-unit"><strong>{context.unit_name}</strong><span>{context.company_name}</span></div>{navigation}</aside><div className="admin-mobile-header"><details><summary>Menu administrativo</summary>{navigation}</details></div><main className="staff-main" id="staff-content"><header className="staff-topbar admin-topbar"><a className="admin-mobile-logo" href="/admin/operation"><img src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /></a><span>{current?.label ?? 'Administração'}</span><AccountMenu context={context} busy={busy} leave={leave} /></header>{children}</main></div>;
}
