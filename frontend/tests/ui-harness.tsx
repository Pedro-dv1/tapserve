import { StrictMode, ViewTransition, useEffect, useState } from 'react';
import { startMotionTransition } from '../src/lib/motion';
import { createRoot } from 'react-dom/client';
import AccountMenu from '../src/features/staff/AccountMenu';
import OrderPolicy from '../src/features/staff/OrderPolicy';
import { ProductionCard } from '../src/features/staff/Production';
import { Pagination } from '../src/features/staff/StaffUI';
import SearchCombobox from '../src/components/SearchCombobox';
import ServiceRequests from '../src/features/customer/ServiceRequests';
import Modal from '../src/components/Modal';
import { reportRecoverableError } from '../src/lib/recoverableError';
import '../src/design-system/base.css';
import '../src/design-system/staff.css';
import '../src/design-system/login.css';
import '../src/design-system/motion.css';

function DetachedPopover() {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(true);
  useEffect(() => { if (open) setMounted(false); }, [open]);
  return <><button popoverTarget="test-popover">Perfil removível</button>{mounted && <div popover="auto" id="test-popover"><button onClick={() => setOpen(true)}>Abrir</button></div>}{open && <Modal open title="Popover desmontado" close={() => setOpen(false)}><button onClick={() => setOpen(false)}>Voltar</button></Modal>}</>;
}
function Navigation() {
  const [cart, setCart] = useState(false);
  return <><nav>{['Cardápio', 'Carrinho'].map((label, index) => <button key={label} onClick={() => startMotionTransition(() => setCart(Boolean(index)), 'navigation')}>{label}</button>)}</nav><ViewTransition name="qa-page"><main key={String(cart)}><h1>{cart ? 'Carrinho' : 'Cardápio'}</h1></main></ViewTransition></>;
}
function PaginationRelease() {
  const [busy, setBusy] = useState(true);
  return <><Pagination page={1} next busy={busy} change={() => {}} label="Contraste" /><button type="button" onClick={() => setBusy(false)}>Liberar controles</button></>;
}
const fixture = {
  id: 'qa-item', product_id: 'qa-product', session_id: 'qa-session', version: 1, quantity: 1,
  name: 'Produto com nome longo e informações adicionais '.repeat(5), points: ['Mesa 01'],
  sector_name: 'Cozinha', sector_id: 'qa-sector', participant_name: null, participant_id: null,
  option_ids: [], option_names: [], notes: '', status: 'NEW' as const,
  fulfillment_mode: 'DINE_IN' as const, line_total: '10.00', created_at: new Date().toISOString(),
  editable_until: new Date().toISOString(), can_customer_change: false, delivered_by_id: null,
};
const selected = new URLSearchParams(location.search).get('case');
const context = { staff: { id: 'qa-admin', name: 'QA sintético', login_code: 'qa', role: 'ADMIN', active: true, permissions: [] }, auth_strength: 'password' as const, company_name: 'QA', unit_id: 'qa-unit', unit_name: 'QA' };
createRoot(document.getElementById('root')!, { onRecoverableError: reportRecoverableError }).render(<StrictMode><ViewTransition default="none" update={{ navigation: 'motion-page', default: 'none' }}><div className="staff-shell"><div>{selected === 'account' ? <><AccountMenu context={context} busy={false} leave={() => {}} /><button type="button">Próximo controle</button></> : selected === 'detached' ? <DetachedPopover /> : selected === 'policy' ? <OrderPolicy /> : selected === 'kds' ? <ProductionCard item={fixture} now={Date.now()} refresh={() => {}} /> : selected === 'calls' ? <ServiceRequests revision={0} /> : selected === 'transition' ? <Navigation /> : selected === 'pagination' ? <PaginationRelease /> : selected === 'search-label' ? <SearchCombobox label="Filtrar opções" value="" change={() => {}} search={() => {}} suggestions={[]} select={() => {}} /> : <><p className="muted">Texto auxiliar</p><input placeholder="Controle" /></>}</div></div></ViewTransition></StrictMode>);
