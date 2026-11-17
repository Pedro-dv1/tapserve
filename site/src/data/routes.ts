export const routes = [
  { path: '/', title: 'Seu atendimento começa com um toque.', description: 'Conheça o TapServe: acesso por aproximação NFC, cardápio, pedidos e operação do estabelecimento em uma jornada conectada.', og: 'O01-og-default.png' },
  { path: '/como-funciona', title: 'Da mesa à cozinha, tudo faz sentido.', description: 'Entenda a jornada do cliente e como a equipe acompanha pedidos, atendimento e produção.', og: 'O03-og-features.png' },
  { path: '/funcionalidades', title: 'Uma operação. Diferentes perspectivas.', description: 'Explore cardápio, opcionais, pedidos, mesas, KDS, equipe e administração no TapServe.', og: 'O03-og-features.png' },
  { path: '/nfc', title: 'Um ponto de partida na sua mesa.', description: 'Conheça o acesso por aproximação NFC e a plaquinha original TapServe.', og: 'O02-og-nfc.png' },
  { path: '/para-quem', title: 'O seu jeito de servir. Mais conectado.', description: 'Cenários de uso do TapServe em restaurantes, hamburguerias, lanchonetes, bares e cafeterias.', og: 'O01-og-default.png' },
  { path: '/demonstracao', title: 'Conheça o TapServe na prática.', description: 'Experimente uma demonstração local de cardápio, opcionais, carrinho, pedido e atendimento.', og: 'O05-og-demo.png' },
  { path: '/contato', title: 'Vamos conversar sobre o seu estabelecimento?', description: 'Solicite uma demonstração comercial do TapServe pelos canais de WhatsApp e e-mail.', og: 'O01-og-default.png' },
  { path: '/suporte', title: 'Precisa de ajuda com o TapServe?', description: 'Encontre orientações e os canais oficiais de suporte por WhatsApp e e-mail.', og: 'O01-og-default.png' },
  { path: '/duvidas', title: 'Boas respostas. Sem complicar.', description: 'Dúvidas sobre NFC, pedidos, implantação e suporte do TapServe.', og: 'O01-og-default.png' },
  { path: '/sobre', title: 'Mais presença à mesa. Mais clareza na operação.', description: 'A proposta do TapServe para conectar a jornada do cliente à rotina do estabelecimento.', og: 'O01-og-default.png' },
  { path: '/privacidade', title: 'Política de Privacidade', description: 'Saiba como o TapServe e os estabelecimentos tratam dados pessoais, utilizam cookies e atendem aos direitos dos titulares.', og: 'O01-og-default.png' },
  { path: '/termos', title: 'Termos de Uso', description: 'Condições de utilização do TapServe para estabelecimentos, administradores, equipes e consumidores.', og: 'O01-og-default.png' },
  { path: '/cancelamento', title: 'Cancelamento — condições em revisão', description: 'Solicite informações sobre cancelamento pelos canais de atendimento.', og: 'O01-og-default.png' },
] as const;
export const notFoundRoute = { path: '/404', title: '404 — Página não encontrada', description: 'Essa página não está no cardápio. O endereço que você tentou acessar não existe ou não está mais disponível.', og: 'O01-og-default.png' } as const;
export function routeFor(path: string) { return routes.find(route => route.path === (path.replace(/\/$/, '') || '/')); }
