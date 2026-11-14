import { useState } from 'react';
import { Icon, Tabs } from './ui';

export function Plaque({ className = '' }: { className?: string }) {
  return <img className={`plaque ${className}`} src="/assets/product/plaque-cutout.webp" width="520" height="780" alt="Plaquinha original TapServe preta, com marca branca e âmbar, área de aproximação NFC e base transparente. Mesa 08." />;
}
const screens = [
  ['S01-client-entry', 'Início do atendimento na Mesa 08'],
  ['S02-client-menu', 'Cardápio real do TapServe com categorias e produtos'],
  ['S03-client-product-options', 'Produto e opções na interface real do TapServe'],
  ['S04-client-cart', 'Carrinho real do TapServe, antes de enviar um pedido'],
  ['S06-client-order-status', 'Acompanhamento de pedidos no TapServe'],
] as const;
export function PhonePreview({ step = 1 }: { step?: number }) {
  const screen = screens[step] ?? screens[0];
  return <div className="phone-preview"><div className="phone-speaker" aria-hidden="true" /><img src={`/assets/screenshots/${screen[0]}.png`} width="390" height="844" alt={screen[1]} loading="lazy" /></div>;
}
function DesktopScreen({ file, alt }: { file: string; alt: string }) {
  return <div className="desktop-capture"><div className="capture-scroll" role="region" aria-label={alt} tabIndex={0}><img src={`/assets/screenshots/${file}.png`} width="1440" height="900" alt={alt} loading="lazy" /></div><p className="caption">Captura original do TapServe, com dados de demonstração. Em telas menores, deslize para explorar.</p></div>;
}
export function OperationFlow() {
  return <div className="operation-flow"><div className="flow-controls"><h3>Escolhido na mesa.<br />Organizado na cozinha.</h3><p>A produção reúne os itens por etapa, com as escolhas do cliente e o contexto de cada mesa.</p><ul className="operation-states"><li>Recebido</li><li>Em preparo</li><li>Pronto para entrega</li></ul></div><DesktopScreen file="S13-kds-new-orders" alt="Tela real de produção do TapServe, com novos pedidos, itens em preparo e prontos" /></div>;
}
export function Showcase() {
  const [active, setActive] = useState(0);
  const titles = ['A escolha fica nas mãos do cliente.', 'Cada mesa, com o contexto que a equipe precisa.', 'A produção ganha uma visão própria.'];
  const descriptions = ['Cardápio, opcionais, carrinho, pedidos e solicitações de atendimento.', 'Mesas, pedidos e chamados reunidos para apoiar o atendimento.', 'Itens por setor e estados de preparo para acompanhar a produção.'];
  return <div className="showcase"><Tabs name="Áreas do TapServe" labels={['Cliente', 'Equipe', 'Cozinha']} active={active} change={setActive}><div className={`showcase-inner${active ? ' wide-capture' : ''}`}><div><h3>{titles[active]}</h3><p>{descriptions[active]}</p><p className="caption">Interface original do TapServe, com dados de demonstração.</p></div><div className="showcase-screen">{active === 0 ? <PhonePreview step={1} /> : <DesktopScreen file={active === 1 ? 'S09-staff-tables' : 'S13-kds-new-orders'} alt={active === 1 ? 'Tela real das mesas no painel da equipe' : 'Tela real de produção do TapServe'} />}</div></div></Tabs></div>;
}
const journey = [
  ['Acesse a mesa', 'Aproxime um celular compatível da plaquinha NFC. O atendimento abre no navegador, seguindo as regras do estabelecimento.'],
  ['Explore o cardápio', 'Encontre categorias e produtos e confira as descrições e os preços.'],
  ['Personalize sua escolha', 'Escolha as opções disponíveis e a quantidade para o seu pedido.'],
  ['Confira o carrinho', 'Revise os itens, as escolhas e o total antes de enviar.'],
  ['Acompanhe o atendimento', 'Veja o andamento dos pedidos e solicite ajuda à equipe quando precisar.'],
];
export function Journey() {
  const [step, setStep] = useState(0);
  return <div className="journey"><div><ol>{journey.map(([title], index) => <li key={title}><button aria-current={step === index ? 'step' : undefined} onClick={() => setStep(index)}>{title}<Icon name="arrow" size={16} /></button></li>)}</ol><div className="journey-description" aria-live="polite"><h3>{journey[step]?.[0]}</h3><p>{journey[step]?.[1]}</p></div><div className="row"><button className="button secondary" disabled={step === 0} onClick={() => setStep(value => value - 1)}>Voltar</button><button className="button" disabled={step === journey.length - 1} onClick={() => setStep(value => value + 1)}>Avançar etapa<Icon name="arrow" /></button></div></div><div className="journey-phone"><PhonePreview key={step} step={step} /></div></div>;
}
export function NfcPlaque() {
  return <div className="nfc-plaque reveal"><Plaque /></div>;
}
