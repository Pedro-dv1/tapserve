import type { ReactNode } from 'react';
import Modal from '../../components/Modal';
import { Icon } from '../../components/Interface';

export function PageHeader({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <header className="staff-page-header"><div><h1>{title}</h1><p>{description}</p></div>{action}</header>;
}

export function Pagination({ page, next, previous = page > 1, busy = false, change, label = 'Resultados' }: { page: number; next: boolean; previous?: boolean; busy?: boolean; change: (page: number) => void; label?: string }) {
  if (!previous && !next) return null;
  return <nav className="staff-pagination" aria-label={`Páginas: ${label}`}>{previous && <button className="secondary" disabled={busy} onClick={() => change(page - 1)} type="button"><Icon name="back" size={16} />Anterior</button>}<span>Página {page}</span>{next && <button className="secondary" disabled={busy} onClick={() => change(page + 1)} type="button">Próxima<Icon name="chevron" size={16} /></button>}</nav>;
}

export function StatusTag({ children, attention = false }: { children: ReactNode; attention?: boolean }) {
  return <span className={`staff-status${attention ? ' attention' : ''}`}>{children}</span>;
}

export function Editor({ title, close, children, busy = false, guardChanges = true }: { title: string; close: () => void; children: ReactNode; busy?: boolean; modal?: boolean; guardChanges?: boolean }) {
  return <Modal open title={title} close={close} busy={busy} guardChanges={guardChanges} className="staff-editor staff-modal">{children}</Modal>;
}

export function ConnectionStatus({ status }: { status: string }) {
  if (!status) return null;
  return <p className="staff-connection attention" role="status"><Icon name="info" size={16} />{status}</p>;
}
