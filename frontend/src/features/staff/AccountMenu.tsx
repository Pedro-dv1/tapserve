import type { StaffContext } from '../../lib/api';
import { Icon } from '../../components/Interface';
import { roleNames } from './navigation';
import { useState } from 'react';
import MfaSettings from './MfaSettings';

export default function AccountMenu({ context, busy, leave }: { context: StaffContext; busy: boolean; leave: () => void }) {
  const [security, setSecurity] = useState(false);
  return <div className="staff-account"><button type="button" className="staff-avatar" popoverTarget="staff-profile-popover" aria-label={`Perfil de ${context.staff.name}`}><Icon name="user" /></button><div id="staff-profile-popover" popover="auto" className="staff-profile-popover"><strong>{context.staff.name}</strong><span>{roleNames[context.staff.role] ?? 'Equipe'}</span>{context.auth_strength === 'password' && <button className="secondary" disabled={busy} onClick={() => setSecurity(true)}>Segurança da conta</button>}<button className="secondary" disabled={busy} onClick={leave}>{busy ? 'Saindo…' : 'Sair'}</button></div>{security && <MfaSettings realm="staff" close={() => setSecurity(false)} />}</div>;
}
