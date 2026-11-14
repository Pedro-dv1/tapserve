import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { contact } from '../config/contact';

export function Icon({ name, size = 22 }: { name: 'arrow' | 'mail' | 'message' | 'nfc' | 'check' | 'plus' | 'close' | 'menu'; size?: number }) {
  const paths = {
    arrow: 'M5 12h14m-6-6 6 6-6 6', mail: 'M3 5h18v14H3zM3 5l9 8 9-8', message: 'M21 11a9 9 0 0 1-13 8l-5 2 1-6A9 9 0 1 1 21 11Z',
    nfc: 'M9 7a7 7 0 0 1 0 10M13 4a11 11 0 0 1 0 16M5 10a3 3 0 0 1 0 4',
    check: 'm5 12 4 4L19 6', plus: 'M12 5v14M5 12h14', close: 'm6 6 12 12M6 18 18 6', menu: 'M4 6h16M4 12h16M4 18h16',
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
export function LinkButton({ href = '/contato', children = 'Solicitar demonstração', secondary = false }: { href?: string; children?: ReactNode; secondary?: boolean }) {
  return <a className={`button magnetic${secondary ? ' secondary' : ''}`} href={href}>{children}<Icon name="arrow" size={18} /></a>;
}
export function ContactButtons({ support = false }: { support?: boolean }) {
  return <div className="contact-buttons"><a className="button" href={support ? contact.support : contact.commercial} target="_blank" rel="noopener noreferrer" aria-label="Enviar mensagem pelo WhatsApp, em aplicativo externo"><Icon name="message" />Enviar mensagem</a><a className="button secondary" href={contact.email} aria-label="Enviar e-mail pelo aplicativo de e-mail"><Icon name="mail" />Enviar e-mail</a></div>;
}
export function Photo({ id, alt, priority = false, className = '' }: { id: string; alt: string; priority?: boolean; className?: string }) {
  return <img className={`photo ${className}`} src={`/assets/photography/${id}.webp`} srcSet={`/assets/photography/${id}-640.webp 640w, /assets/photography/${id}-1280.webp 1280w`} sizes="(max-width: 767px) 100vw, 60vw" width="1280" height="960" loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} decoding="async" alt={alt} />;
}
export function Heading({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="section-heading reveal"><h2>{title}</h2>{children && <p>{children}</p>}</div>;
}
export function PageIntro({ title, children }: { title: string; children?: ReactNode }) {
  return <header className="page-intro wrap"><h1>{title}</h1>{children && <p>{children}</p>}</header>;
}
export function Tabs({ labels, children, active, change, name }: { labels: string[]; children: ReactNode; active: number; change: (index: number) => void; name: string }) {
  const id = useId();
  return <><div className="tabs" role="tablist" aria-label={name}>{labels.map((label, index) => <button key={label} id={`${id}-tab-${index}`} role="tab" aria-selected={active === index} aria-controls={`${id}-panel`} tabIndex={active === index ? 0 : -1} onClick={() => change(index)} onKeyDown={event => {
    const next = event.key === 'ArrowRight' ? (index + 1) % labels.length : event.key === 'ArrowLeft' ? (index + labels.length - 1) % labels.length : event.key === 'Home' ? 0 : event.key === 'End' ? labels.length - 1 : null;
    if (next !== null) { event.preventDefault(); change(next); document.getElementById(`${id}-tab-${next}`)?.focus(); }
  }}>{label}</button>)}</div><div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-tab-${active}`} tabIndex={0} className="tab-panel" key={active}>{children}</div></>;
}
export function Accordion({ items }: { items: { id: string; question: string; answer: string }[] }) {
  return <div className="accordion">{items.map(item => <details id={item.id} key={item.id}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div>;
}
export function FinalCTA() { return <section className="final-cta"><div className="wrap"><h2>Seu próximo atendimento<br />pode começar aqui.</h2><p>Conheça o TapServe no contexto do seu estabelecimento.</p><ContactButtons /></div></section>; }
export function MobileMenu() {
  const [open, setOpen] = useState(false);
  return <div className="mobile-menu" onKeyDown={event => { if (event.key === 'Escape') { setOpen(false); event.currentTarget.querySelector('button')?.focus(); } }}><button className="icon-button" aria-label={open ? 'Fechar menu' : 'Abrir menu'} aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen(value => !value)}><Icon name={open ? 'close' : 'menu'} /></button><nav id="mobile-nav" hidden={!open} aria-label="Navegação mobile">
    {navLinks.map(([label, href]) => <a key={href} href={href}>{label}</a>)}<a href="/para-quem">Para quem</a><a href="/contato">Contato</a><a href="/suporte">Suporte</a><LinkButton /></nav></div>;
}
export const navLinks = [['Como funciona', '/como-funciona'], ['Funcionalidades', '/funcionalidades'], ['Acesso NFC', '/nfc'], ['Demonstração', '/demonstracao']] as const;
