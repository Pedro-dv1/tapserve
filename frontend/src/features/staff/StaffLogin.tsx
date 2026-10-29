import { startTransition, useRef, useState, ViewTransition } from 'react';
import type { FormEvent } from 'react';
import { decodeContext, request } from '../../lib/api';
import { Button, ErrorState, Icon, SecretInput } from '../../components/Interface';
import '../../design-system/customer.css';
import '../../design-system/login.css';
import { staffHome } from './navigation';

export default function StaffLogin() {
  const [strong, setStrong] = useState(false);
  const [company, setCompany] = useState('');
  const [unit, setUnit] = useState('');
  const [identity, setIdentity] = useState('');
  const [pin, setPin] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState('');
  const [recover, setRecover] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (submitting.current || (!strong && !/^\d{6,12}$/.test(pin))) return;
    submitting.current = true; setBusy(true); setError('');
    try {
      const context = decodeContext(await request(strong ? '/api/v1/staff/password-login/' : '/api/v1/staff/login/', 'POST', { company, unit, ...(strong ? { username: identity, password } : { login_code: identity, pin }) }));
      setPin(''); setPassword('');
      window.location.replace(staffHome(context));
    } catch (cause: unknown) { setPin(''); setPassword(''); setError(cause instanceof Error ? cause.message : 'Não foi possível entrar. Tente novamente.'); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <main className="staff-login"><img className="login-logo" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" />
    <h1>Login da equipe</h1><p className="login-subtitle">{strong ? 'Use sua senha para acessar a gestão da unidade' : 'Digite seu PIN para acessar sua área de trabalho'}</p>
    <form onSubmit={event => { void submit(event); }} aria-busy={busy}>
      <details className="unit-details" open><summary><Icon name="table" size={25} /><span><strong>{unit || 'Identifique a unidade'}</strong><span>{company || 'Empresa e unidade do seu acesso'}</span></span><Icon name="chevron" size={18} /></summary><div className="unit-fields">
        <label htmlFor="login-company">Código da empresa<input id="login-company" name="company" required maxLength={80} pattern="[A-Za-z0-9_\-]+" value={company} disabled={busy} onChange={event => setCompany(event.target.value)} autoCapitalize="none" autoComplete="off" /></label>
        <label htmlFor="login-unit">Código da unidade<input id="login-unit" name="unit" required maxLength={80} pattern="[A-Za-z0-9_\-]+" value={unit} disabled={busy} onChange={event => setUnit(event.target.value)} autoCapitalize="none" autoComplete="off" /></label>
      </div></details>
      <label className="identity-field" htmlFor="login-identity">{strong ? 'Usuário' : 'Código individual'}<input id="login-identity" name="identity" required maxLength={strong ? 150 : 32} pattern={strong ? undefined : '[A-Za-z0-9_\\-]{1,32}'} value={identity} disabled={busy} onChange={event => setIdentity(event.target.value)} autoCapitalize="none" autoComplete="username" /></label>
      {!strong && <><label className="sr-only" htmlFor="staff-pin">PIN individual, de 6 a 12 dígitos</label><SecretInput label="PIN" id="staff-pin" name="pin" inputMode="numeric" autoComplete="current-password" required minLength={6} maxLength={12} pattern="[0-9]{6,12}" value={pin} disabled={busy} onChange={event => setPin(event.target.value.replace(/\D/g, '').slice(0, 12))} aria-describedby="pin-policy" />
        <p className="pin-policy" id="pin-policy">PIN de 6 a 12 dígitos</p>
        <div className="pin-keypad" aria-label="Teclado numérico">{[1, 2, 3, 4, 5, 6, 7, 8, 9].map(digit => <button type="button" key={digit} disabled={busy || pin.length >= 12} onClick={() => setPin(value => (value + digit).slice(0, 12))}>{digit}</button>)}<span aria-hidden="true" /><button type="button" disabled={busy || pin.length >= 12} onClick={() => setPin(value => (value + '0').slice(0, 12))}>0</button><button className="erase-key" type="button" aria-label="Apagar último dígito" disabled={busy || pin.length === 0} onClick={() => setPin(value => value.slice(0, -1))}><Icon name="erase" size={25} /></button></div>
        <button className="pin-recovery" type="button" aria-expanded={recover} onClick={() => startTransition(() => setRecover(value => !value))}>Esqueci meu PIN</button>{recover && <ViewTransition default="none" enter="motion-panel" exit="motion-panel"><p className="recovery-help" role="status">Solicite a redefinição ao responsável pela unidade. Somente a gestão autorizada pode atualizar seu PIN individual.</p></ViewTransition>}
      </>}
      {strong && <div><label htmlFor="staff-password">Senha</label><SecretInput label="senha" id="staff-password" name="password" required maxLength={256} autoComplete="current-password" disabled={busy} value={password} onChange={event => setPassword(event.target.value)} /></div>}
      {error && <ErrorState message={error} />}
      <Button className="login-submit" type="submit" disabled={busy || (!strong && pin.length < 6)}>{busy ? 'Entrando…' : 'Entrar'}<Icon name="arrow" /></Button>
    </form>
    <p className="login-security"><Icon name="lock" size={16} />Tentativas excessivas podem bloquear temporariamente o acesso.</p>
    <button className="login-switch" disabled={busy} aria-pressed={strong} onClick={() => { setStrong(value => !value); setPin(''); setPassword(''); setIdentity(''); setError(''); }}>{strong ? 'Entrar com PIN individual' : 'Responsável: entrar com senha'}</button>
  </main>;
}
