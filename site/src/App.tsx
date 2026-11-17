import { useEffect } from 'react';
import { routeFor } from './data/routes';
import { Icon, LinkButton, MobileMenu, navLinks } from './components/ui';
import { Page } from './pages';

export function App({ path }: { path: string }) {
  useEffect(() => {
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add('revealed'); observer.unobserve(entry.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll('.reveal').forEach(element => observer.observe(element));
    return () => observer.disconnect();
  }, []);
  const route = routeFor(path);
  return <div data-site="tapserve" className="site">
    <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
    <header className="site-header"><div className="header-inner"><a className="brand" href="/" aria-label="TapServe — início"><img src="/assets/brand/B01-logo-wordmark-black.svg" width="180" height="60" alt="TapServe" /></a><nav className="desktop-nav" aria-label="Navegação principal">{navLinks.map(([label, href]) => <a key={href} href={href} aria-current={route?.path === href ? 'page' : undefined}>{label}</a>)}</nav><div className="header-cta"><LinkButton><span className="desktop-cta-label">Solicitar demonstração</span><span className="mobile-cta-label">Solicitar demo</span></LinkButton></div><MobileMenu /></div></header>
    <main id="conteudo" tabIndex={-1}><Page path={route?.path ?? '404'} /></main>
    <footer className="site-footer"><div className="wrap"><div className="footer-top"><a className="brand" href="/"><img src="/assets/brand/B02-logo-wordmark-light.svg" width="210" height="70" alt="TapServe" /></a><p>Da primeira escolha<br />ao próximo atendimento.</p></div><div className="footer-columns"><div><h2>Produto</h2>{navLinks.map(([label, href]) => <a key={href} href={href}>{label}</a>)}</div><div><h2>Empresa</h2><a href="/para-quem">Para quem</a><a href="/sobre">Sobre o TapServe</a><a href="/contato">Contato</a></div><div><h2>Ajuda</h2><a href="/suporte">Suporte</a><a href="/duvidas">Dúvidas frequentes</a><a href="/cancelamento">Cancelamento</a></div><div><h2>Legal</h2><a href="/privacidade">Política de Privacidade</a><a href="/termos">Termos de Uso</a></div></div><div className="footer-bottom"><small>© {new Date().getFullYear()} TapServe. Prévia local para revisão.</small><a href="#conteudo" aria-label="Voltar ao conteúdo principal">Voltar ao topo <Icon name="arrow" size={16} /></a></div></div></footer>
  </div>;
}
