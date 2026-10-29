import { useId, useRef, useState } from 'react';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import type { PublicContext } from '../lib/api';

const paths = {
  bag: <path d="M5 7h14l2 14H3L5 7Zm3 0V5a4 4 0 0 1 8 0v2" />,
  more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
  bell: <path d="M6 9a6 6 0 0 1 12 0v7l2 2H4l2-2V9Zm4 12h4" />,
  home: <path d="m3 10 9-7 9 7v11h-7v-7h-4v7H3V10Z" />,
  play: <path d="m9 5 11 7-11 7V5Z" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
  eyeOff: <><path d="m3 3 18 18M9 5a12 12 0 0 1 3 0c6 0 10 7 10 7a18 18 0 0 1-3 4M6 6a22 22 0 0 0-4 6s4 7 10 7a12 12 0 0 0 5-1" /></>,
  star: <path d="m12 2 3 6.5 7 1-5 5 1 7-6-3.5L6 21l1-6.5-5-5 7-1L12 2Z" />,
  back: <path d="m14 6-6 6 6 6" />,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  chevron: <path d="m9 6 6 6-6 6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  check: <path d="m5 12 4 4 10-10" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  cart: <><path d="M2 3h3l3 12h11l2-9H6" /><circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" /></>,
  table: <path d="M3 11h18l-2-6H5l-2 6Zm2 0v8m14-8v8M5 15h14" />,
  user: <><circle cx="12" cy="7" r="4" /><path d="M5 21v-3a7 7 0 0 1 14 0v3H5Z" /></>,
  users: <><circle cx="9" cy="7" r="3" /><path d="M3 20v-3a6 6 0 0 1 12 0v3H3Zm14-15a3 3 0 0 1 0 6m1 3a5 5 0 0 1 3 5v1" /></>,
  edit: <path d="m15 4 5 5M4 20l1-5L16 4a2 2 0 0 1 3 0l1 1a2 2 0 0 1 0 3L9 19l-5 1Z" />,
  trash: <path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7" />,
  message: <path d="M4 3h16a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H8l-5 3V4a1 1 0 0 1 1-1Z" />,
  book: <path d="M12 5v16M3 3l9 2 9-2v16l-9 2-9-2V3Z" />,
  receipt: <path d="M6 3h12l2 2v16H4V5l2-2Zm2 4h8M8 11h8M8 15h5" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  ready: <path d="M3 17h18M5 17a7 7 0 0 1 14 0M12 6v4M3 21h18" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 4v3" /></>,
  erase: <path d="M9 4h12v16H9L2 12l7-8Zm3 5 6 6m0-6-6 6" />,
  image: <><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="1" /><path d="m3 16 5-5 4 4 4-6 5 7" /></>,
};
export function Icon({ name, size = 20 }: { name: keyof typeof paths; size?: number }) {
  return <svg className="ui-icon" aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
export function Button({ secondary = false, className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { secondary?: boolean }) {
  return <button className={`ui-button ${secondary ? 'ui-secondary' : 'ui-primary'} ${className}`} {...props} />;
}
export function SecretInput({ label, id, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string }) {
  const [visible, setVisible] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const generatedId = useId(); const identifier = id ?? generatedId;
  function toggle() {
    const start = input.current?.selectionStart ?? null; const end = input.current?.selectionEnd ?? null;
    setVisible(value => !value);
    window.requestAnimationFrame(() => { if (start !== null && end !== null) input.current?.setSelectionRange(start, end); });
  }
  return <span className="secret-field"><input {...props} id={identifier} ref={input} type={visible ? 'text' : 'password'} /><button className="secret-toggle secondary" type="button" aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${label}`} aria-pressed={visible} aria-controls={identifier} disabled={props.disabled} onPointerDown={event => event.preventDefault()} onClick={toggle}><Icon name={visible ? 'eyeOff' : 'eye'} /></button></span>;
}
export function PriceAction({ children, price, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { price: string }) {
  return <Button {...props}><span>{children}</span><span className="action-price">{price}</span></Button>;
}
export function StickyActionBar({ children }: { children: ReactNode }) {
  return <div className="sticky-action"><div>{children}</div></div>;
}
export function tableLabel(name: string, type = 'TABLE'): string {
  if (type !== 'TABLE') return ({ COUNTER: 'Balcão', PICKUP: 'Retirada' } as Record<string, string>)[type] ?? 'Atendimento';
  const number = name.match(/\bmesa\s*[-#]?\s*(\d{1,6})\b/i)?.[1] ?? name.trim().match(/^\d{1,6}$/)?.[0];
  return number && Number(number) > 0 ? `Mesa ${number.padStart(2, '0')}` : 'Mesa';
}
export function CustomerHeader({ context, pointName, back }: { context: PublicContext; pointName: string; back?: () => void }) {
  return <><header className="customer-header">
    <img className="customer-logo" src="/brand/TapServe-logo-wordmark.png" alt="TapServe" />
    <div className="table-indicator"><Icon name="table" size={22} /><strong>{tableLabel(context.point.number ? `Mesa ${context.point.number}` : pointName, context.point.type)}</strong></div>
  </header>{back && <div className="customer-back"><button className="icon-button back-button" aria-label="Voltar" onClick={back}><Icon name="back" size={24} /></button></div>}</>;
}
export function ProductImage({ id, name, hasImage = true, className = '', version = '' }: { id: string; name: string; hasImage?: boolean; className?: string; version?: string }) {
  const [failed, setFailed] = useState(false);
  return <span className={`product-image ${className}`}>
    {hasImage && !failed ? <img src={`/api/v1/public/products/${id}/image/${version ? `?v=${encodeURIComponent(version)}` : ''}`} alt={name} loading="lazy" onError={() => setFailed(true)} /> : <span className="image-fallback" role="img" aria-label={`${name}: imagem indisponível`}><Icon name="image" size={28} /></span>}
  </span>;
}
export function ParticipantChip({ name }: { name: string }) {
  return <span className="participant-tag"><Icon name="user" size={14} />{name}</span>;
}
export function PopularityBadge() { return <span className="popularity-badge"><Icon name="star" size={12} />Mais pedido</span>; }
export function QuantitySelector({ quantity, disabled, change, name }: { quantity: number; disabled: boolean; change: (value: number) => void; name: string }) {
  return <div className="quantity-selector" aria-label={`Quantidade de ${name}`}>
    <button type="button" className="icon-button" aria-label={`Diminuir ${name}`} disabled={disabled || quantity <= 1} onClick={() => change(quantity - 1)}><Icon name="minus" size={17} /></button>
    <output aria-live="polite" style={{ animationName: quantity % 2 ? 'motion-count-odd' : 'motion-count-even' }}>{quantity}</output>
    <button type="button" className="icon-button quantity-plus" aria-label={`Aumentar ${name}`} disabled={disabled || quantity >= 99} onClick={() => change(quantity + 1)}><Icon name="plus" size={18} /></button>
  </div>;
}
export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return <div className="empty-state"><Icon name="receipt" size={32} /><h2>{title}</h2>{children && <p>{children}</p>}{action}</div>;
}
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="error-state" role="alert"><Icon name="info" /><p>{message}</p>{retry && <Button secondary onClick={retry}>Tentar novamente</Button>}</div>;
}
export function LoadingSkeleton({ product = false, variant = 'menu' }: { product?: boolean; variant?: 'menu' | 'product' | 'orders' | 'table' | 'catalog' | 'staff' | 'points' | 'operation' | 'production' | 'settings' | 'calls' | 'options' | 'health' }) {
  const shape = product ? 'product' : variant;
  const bar = (className = '') => <span className={`skeleton-block ${className}`} />;
  let content: ReactNode;
  if (shape === 'product') content = <>{bar('skeleton-photo')}<div className="skeleton-heading">{bar('skeleton-title')}{bar('skeleton-price')}</div>{bar('skeleton-line')}<div className="skeleton-options">{[0, 1, 2].map(index => <div key={index}>{bar('skeleton-line')}{bar('skeleton-control')}</div>)}</div>{bar('skeleton-action')}</>;
  else if (shape === 'production') content = <div className="skeleton-columns">{[0, 1, 2].map(column => <section key={column}>{bar('skeleton-title')}{[0, 1].map(index => <article className="skeleton-ticket" key={index}>{bar('skeleton-line')}{bar('skeleton-title')}{bar('skeleton-line')}{bar('skeleton-action')}</article>)}</section>)}</div>;
  else if (shape === 'settings' || shape === 'health' || shape === 'options') content = <>{bar('skeleton-title')}{bar('skeleton-line')}{shape !== 'health' && bar('skeleton-control')}{bar('skeleton-action')}</>;
  else if (shape === 'table' || shape === 'operation' || shape === 'orders' || shape === 'calls') content = <>{[0, 1, 2].map(index => <article className="skeleton-ticket" key={index}><div className="skeleton-heading">{bar('skeleton-title')}{bar('skeleton-price')}</div>{bar('skeleton-line')}<div className="skeleton-chips">{bar()}{bar()}{bar()}</div>{shape !== 'calls' && bar('skeleton-control')}</article>)}</>;
  else content = <>{shape === 'menu' && <div className="skeleton-chips">{bar()}{bar()}{bar()}</div>}{[0, 1, 2, 3].map(index => <div className="skeleton-row" key={index}>{bar(shape === 'staff' ? 'skeleton-avatar' : 'skeleton-thumb')}<div>{bar('skeleton-title')}{bar('skeleton-line')}</div>{bar('skeleton-price')}</div>)}</>;
  return <div className={`content-skeleton skeleton-${shape}`} role="status" aria-busy="true" aria-label="Carregando"><span className="sr-only">Carregando…</span><div aria-hidden="true">{content}</div></div>;
}
