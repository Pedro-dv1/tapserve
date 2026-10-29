import type { StaffContext } from '../../lib/api';
import { useRealtime } from '../../lib/useRealtime';
import ServiceRequests from '../customer/ServiceRequests';
import { ConnectionStatus, PageHeader } from './StaffUI';

export default function StaffCalls({ context }: { context: StaffContext }) {
  const realtime = useRealtime('staff');
  return <section><PageHeader title="Chamados" description="Solicitações de atendimento e histórico da unidade." /><ConnectionStatus status={realtime.status} /><ServiceRequests staff={context} revision={realtime.callsRevision} /></section>;
}
