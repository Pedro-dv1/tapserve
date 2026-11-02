import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { record, request } from '../../lib/api';
import { ErrorState, SecretInput } from '../../components/Interface';
import Modal from '../../components/Modal';
import MfaChallenge, { decodeChallenge } from './MfaChallenge';
import type { Challenge } from './MfaChallenge';

export default function MfaSettings({ realm, close }: { realm: 'staff' | 'platform'; close: () => void }) {
  const [remaining, setRemaining] = useState<number | null>(null), [enabled, setEnabled] = useState(false);
  const [password, setPassword] = useState(''), [code, setCode] = useState('');
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [challenge, setChallenge] = useState<Challenge | null>(null), [confirmReset, setConfirmReset] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void request(`/api/v1/${realm}/mfa/`, 'GET', undefined, controller.signal).then(record).then(data => { if (!controller.signal.aborted) { setEnabled(data.enabled === true); setRemaining(typeof data.recovery_codes_remaining === 'number' ? data.recovery_codes_remaining : 0); } }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível consultar sua segurança.'); });
    return () => controller.abort();
  }, [realm]);
  async function replace(event: FormEvent<HTMLFormElement>) { event.preventDefault(); await change(false); }
  async function change(remove: boolean) {
    if (busy) return; setBusy(true); setError('');
    try {
      const value = await request(`/api/v1/${realm}/mfa/`, remove ? 'DELETE' : 'POST', { password, code }); setPassword(''); setCode('');
      if (remove) { window.location.replace(realm === 'staff' ? '/staff/login' : '/platform'); return; }
      const next = decodeChallenge(value); if (!next) throw new Error('Não foi possível iniciar a substituição.'); setChallenge(next);
    } catch (cause: unknown) { setPassword(''); setCode(''); setError(cause instanceof Error ? cause.message : 'Não foi possível alterar o autenticador.'); }
    finally { setBusy(false); setConfirmReset(false); }
  }
  return <Modal open title="Segurança da conta" close={close} busy={busy}>
    {challenge ? <MfaChallenge challenge={challenge} realm={realm} authenticated={() => window.location.reload()} cancel={() => window.location.replace(realm === 'staff' ? '/staff/login' : '/platform')} /> : <><p>{remaining === null ? 'Consultando configuração…' : enabled ? `Verificação em duas etapas ativa. ${remaining} códigos de recuperação disponíveis.` : 'Sua conta ainda não tem um autenticador ativo. Entre novamente com a senha para configurar quando exigido.'}</p><p>Para substituir ou redefinir, confirme a senha e um código do autenticador ou de recuperação. A substituição invalida as sessões anteriores quando concluída.</p><form onSubmit={event => { void replace(event); }} aria-busy={busy}><label htmlFor="mfa-current-password">Senha atual</label><SecretInput id="mfa-current-password" label="senha atual" required maxLength={256} autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy || !enabled} /><label htmlFor="mfa-current-code">Código do autenticador ou de recuperação</label><SecretInput id="mfa-current-code" label="código atual" required maxLength={32} autoComplete="one-time-code" pattern="([0-9]{6}|[a-f0-9]{32})" value={code} onChange={event => setCode(event.target.value.trim())} disabled={busy || !enabled} />{error && <ErrorState message={error} />}<div className="actions"><button disabled={busy || !enabled} type="submit">Substituir autenticador</button><button disabled={busy || !enabled || !password || !code} className="ui-danger" type="button" onClick={() => setConfirmReset(true)}>Redefinir e sair</button></div></form>{confirmReset && <div role="alert"><p>Redefinir o autenticador encerra seus acessos. Contas privilegiadas precisarão cadastrar um novo autenticador após entrar novamente com a senha. Confirme somente se você controla a senha e os meios de recuperação.</p><div className="actions"><button type="button" disabled={busy} onClick={() => { void change(true); }}>Confirmar redefinição</button><button type="button" className="secondary" disabled={busy} onClick={() => setConfirmReset(false)}>Voltar</button></div></div>}</>}
  </Modal>;
}
