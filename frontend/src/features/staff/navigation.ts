import type { StaffContext } from '../../lib/api';
import type { ComponentProps } from 'react';
import type { Icon } from '../../components/Interface';

export const roleNames: Record<string, string> = { OWNER: 'Proprietário', ADMIN: 'Administrador', MANAGER: 'Gerente', WAITER: 'Atendente', KITCHEN: 'Cozinha', BAR: 'Bar', CASHIER: 'Caixa' };
export const isManagement = (context: StaffContext) => ['OWNER', 'ADMIN', 'MANAGER'].includes(context.staff.role);
export type StaffPage = { href: string; label: string; icon: ComponentProps<typeof Icon>['name']; group: string; permissions: string[]; strong: boolean };
const adminNavigation: StaffPage[] = [
  { href: '/admin/operation', label: 'Mesas', icon: 'table', group: 'Expediente', permissions: ['VIEW_OPERATION', 'VIEW_ALL_TABLES'], strong: false },
  { href: '/admin/orders', label: 'Pedidos', icon: 'receipt', group: 'Expediente', permissions: ['VIEW_OPERATION', 'VIEW_ALL_TABLES'], strong: false },
  { href: '/admin/production', label: 'Produção', icon: 'ready', group: 'Expediente', permissions: ['VIEW_OPERATION', 'UPDATE_PRODUCTION_STATUS'], strong: false },
  { href: '/admin/calls', label: 'Chamados', icon: 'bell', group: 'Expediente', permissions: ['VIEW_OPERATION', 'ASSIGN_SERVICE_REQUEST'], strong: false },
  { href: '/admin/menu', label: 'Cardápio', icon: 'book', group: 'Gestão', permissions: ['MANAGE_MENU'], strong: true },
  { href: '/admin/points', label: 'Pontos de atendimento', icon: 'table', group: 'Gestão', permissions: ['MANAGE_SERVICE_POINTS'], strong: true },
  { href: '/admin/staff', label: 'Funcionários', icon: 'users', group: 'Gestão', permissions: ['MANAGE_STAFF'], strong: true },
  { href: '/admin/settings', label: 'Configurações', icon: 'edit', group: 'Gestão', permissions: ['MANAGE_SETTINGS'], strong: true },
];
// The attendant experience owns a separate menu and never inherits management links.
const attendantNavigation: StaffPage[] = [
  { href: '/staff/orders', label: 'Pedidos', icon: 'receipt', group: 'Expediente', permissions: ['VIEW_OPERATION', 'VIEW_ALL_TABLES'], strong: false },
  { href: '/staff/calls', label: 'Chamados', icon: 'bell', group: 'Expediente', permissions: ['VIEW_OPERATION', 'ASSIGN_SERVICE_REQUEST'], strong: false },
  { href: '/staff/operation', label: 'Mesas', icon: 'table', group: 'Expediente', permissions: ['VIEW_OPERATION', 'VIEW_ALL_TABLES'], strong: false },
  { href: '/staff/production', label: 'Produção', icon: 'ready', group: 'Expediente', permissions: ['VIEW_OPERATION', 'UPDATE_PRODUCTION_STATUS'], strong: false },
];

export function staffPages(context: StaffContext) {
  const pages = isManagement(context) ? adminNavigation : attendantNavigation;
  return pages.filter(page => (!page.strong || context.auth_strength === 'password') && page.permissions.every(permission => context.staff.permissions.includes(permission)));
}

export function staffHome(context: StaffContext) {
  const allowed = staffPages(context);
  if (['KITCHEN', 'BAR'].includes(context.staff.role)) return allowed.find(page => page.href === '/staff/production')?.href ?? '/staff/more';
  return allowed.find(page => page.href.endsWith('/operation'))?.href ?? allowed[0]?.href ?? (isManagement(context) ? '/admin' : '/staff/more');
}

export function staffPath(context: StaffContext, path: string) {
  if (!isManagement(context)) return path === '/staff' ? staffHome(context) : path;
  if (path === '/staff') return '/admin/staff';
  if (path === '/admin' || path === '/staff/more') return staffHome(context);
  return path.replace(/^\/staff\//, '/admin/');
}
