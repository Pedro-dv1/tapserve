import { useState } from 'react';
import type { FormEvent } from 'react';
import { record, request } from '../../lib/api';
import { ErrorState, SecretInput } from '../../components/Interface';

export type Challenge = { mfa_required: true; enrollment_required: boolean; expires_at: string; provisioning_uri?: string };

export function decodeChallenge(value: unknown): Challenge | null {
  const data = record(value);
  if (data.mfa_required !== true) return null;
  if (typeof data.enrollment_required !== 'boolean' || typeof data.expires_at !== 'string' || !Number.isFinite(Date.parse(data.expires_at)) || data.provisioning_uri !== undefined && typeof data.provisioning_uri !== 'string') throw new Error('Desafio de segurança inválido. Reinicie o login.');
  return { mfa_required: true, enrollment_required: data.enrollment_required, expires_at: data.expires_at, ...(typeof data.provisioning_uri === 'string' ? { provisioning_uri: data.provisioning_uri } : {}) };
}

export default function MfaChallenge({ challenge, realm, authenticated, cancel }: { challenge: Challenge; realm: 'staff' | 'platform'; authenticated: (value: unknown) => void; cancel: () => void }) {
  const [code, setCode] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [completed, setCompleted] = useState<{ result: unknown; codes: string[] } | null>(null);
  let secret = '';
  if (challenge.provisioning_uri) {
    try { const uri = new URL(challenge.provisioning_uri); if (uri.protocol === 'otpauth:' && uri.hostname === 'totp') secret = uri.searchParams.get('secret') ?? ''; } catch { /* Malformed enrollment material is never treated as verified. */ }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    if (Date.now() >= Date.parse(challenge.expires_at)) { setError('O desafio expirou. Volte e entre novamente com a senha.'); return; }
    setBusy(true); setError('');
    try {
      const result = await request(`/api/v1/${realm}/mfa/challenge/`, 'POST', { code });
      const row = record(result); setCode('');
      if (Array.isArray(row.recovery_codes) && row.recovery_codes.every(value => typeof value === 'string')) setCompleted({ result, codes: row.recovery_codes as string[] });
      else authenticated(result);
    } catch (cause: unknown) { setCode(''); setError(cause instanceof Error ? cause.message : 'Não foi possível verificar o código.'); }
    finally { setBusy(false); }
  }
  if (completed) return <section aria-label="Códigos de recuperação"><h2>Guarde os códigos de recuperação</h2><p>Cada código funciona uma única vez. Guarde-os em local seguro, separado do autenticador. Eles não serão exibidos novamente.</p><ul>{completed.codes.map(value => <li key={value}><code>{value}</code></li>)}</ul><button type="button" onClick={() => authenticated(completed.result)}>Guardei os códigos. Continuar</button></section>;
  return <section aria-label="Verificação em duas etapas"><h2>{challenge.enrollment_required ? 'Configure seu autenticador' : 'Verificação em duas etapas'}</h2>
    {challenge.enrollment_required && <><p>Adicione uma conta TOTP no aplicativo autenticador: TapServe, código de 6 dígitos, intervalo de 30 segundos. Cadastre a chave abaixo e informe o código exibido no aplicativo.</p><label>Chave do autenticador<input readOnly value={secret} autoComplete="off" onFocus={event => event.currentTarget.select()} /></label><p>Não compartilhe essa chave. O relógio do aparelho precisa estar sincronizado.</p></>}
    <form onSubmit={event => { void submit(event); }} aria-busy={busy}><label htmlFor="mfa-code">{challenge.enrollment_required ? 'Código do autenticador' : 'Código do autenticador ou código de recuperação'}</label><SecretInput id="mfa-code" label="código de verificação" value={code} onChange={event => setCode(event.target.value.trim())} required maxLength={32} autoComplete="one-time-code" pattern={challenge.enrollment_required ? '[0-9]{6}' : '([0-9]{6}|[a-f0-9]{32})'} disabled={busy} />{error && <ErrorState message={error} />}<div className="actions"><button type="submit" disabled={busy || challenge.enrollment_required && !secret}>{busy ? 'Verificando…' : 'Verificar código'}</button><button type="button" className="secondary" disabled={busy} onClick={cancel}>Voltar ao login</button></div></form>
  </section>;
}
