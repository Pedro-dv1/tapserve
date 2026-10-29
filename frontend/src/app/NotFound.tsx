import { Icon } from '../components/Interface';

export default function NotFound() {
  const path = window.location.pathname;
  const home = /^\/(customer|a)(\/|$)/.test(path) ? '/customer' : /^\/admin(\/|$)/.test(path) ? '/admin' : /^\/staff(\/|$)/.test(path) ? '/staff' : /^\/platform(\/|$)/.test(path) ? '/platform' : '/';
  return <section className="not-found" aria-labelledby="not-found-title"><img className="wordmark" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" /><span className="not-found-code">404</span><h1 id="not-found-title">Página não encontrada</h1><p>Este endereço não existe. Volte ao início para continuar.</p><a className="ui-button" href={home}><Icon name="home" />Voltar ao início</a></section>;
}
