# Refinamento da landing page TapServe — 13/11/2026

## Estado da entrega

As alterações comerciais solicitadas estão implementadas no site existente. O preview auditado está em **http://127.0.0.1:4321**; a landing em desenvolvimento responde em **http://127.0.0.1:5180**. O aplicativo original em 5176 e o health check do backend em 8003 também responderam HTTP 200 na conferência final.

**Há uma pendência ambiental na validação de build:** builds de produção anteriores geraram as 13 rotas e foram utilizados na auditoria visual e funcional. A repetição final de `npm.cmd run build` passou pelo TypeScript, mas o Vite terminou com `[commonjs--resolver] spawn EPERM` em `optimizeSafeRealPathSync`, ao tentar iniciar um processo auxiliar do Windows. Uma tentativa anterior também encontrou bloqueio ao iniciar esbuild. O último artefato aprovado continua disponível no preview; não se deve interpretar a tentativa final como build aprovado. O ajuste final de limpeza do nome temporário foi conferido diretamente no servidor de desenvolvimento.

Não houve deploy, commit, publicação ou alteração das aprovações humanas. O gate de publicação permanece bloqueado pelas aprovações existentes e pela revisão jurídica.

## Alterações implementadas

- **Conteúdo e estrutura:** retirados eyebrows decorativos, números de posição de seção, seção/página de planos, preços de assinatura da apresentação, links exclusivos para planos e controle de animações do rodapé. Reorganizados headings, espaços e sequência comercial. Labels funcionais, números do produto e avisos jurídicos foram preservados.
- **Comunicação NFC:** removidas as referências comerciais a QR, inclusive FAQ, navegação e metadados. A nova rota é `/nfc`; as rotas comerciais antigas removidas retornam 404. Os recursos internos do SaaS foram preservados.
- **Plaquinha:** a seção “A mesa é o ponto de partida” contém apenas a imagem original, acompanhada do texto da seção. Não há galeria, seletor, botão adicional ou hotspot. A arte preta vertical, sua base, marca e proporções foram preservadas.
- **Celular:** reconstruída a moldura em torno de capturas reais 390 × 844. A tela usa `aspect-ratio: 390 / 844`, `height: auto` e `object-fit: contain`; a moldura acrescenta bordas e arredondamentos sem deformar o conteúdo. O tamanho e a composição variam por breakpoint.
- **Interfaces:** hero, jornada, áreas do produto e operação passaram a usar screenshots do TapServe real. As abas Cliente, Equipe e Cozinha mantêm altura estável; capturas operacionais podem ser exploradas por rolagem e teclado, sem redesenhar seu conteúdo.
- **Demo:** substituída a interface comercial própria por componentes e CSS originais do aplicativo. O catálogo contém produtos reais do QA. Carrinho, participantes, pedidos, estados e atendimento são demonstrações locais, identificadas como tal, com reinício completo. Não há conexão operacional, pedido enviado, cookie ou armazenamento persistente.
- **Header e contato:** navegação desktop com espaçamento responsivo e tratamento de larguras intermediárias; menu mobile preservado. Título, apoio, meios de contato e botões centralizados, com larguras consistentes. Os canais e destinos de contato existentes foram mantidos.
- **Identidade e acessibilidade:** logos originais preservados; ajustes de tipografia, ritmo, alinhamento, bordas, profundidade, estados de interação e foco. Conteúdo comercial pré-renderizado continua disponível sem JavaScript.

## Arquivos e finalidade

Os caminhos abaixo são relativos à raiz do repositório. O diretório `site/` já estava sem rastreamento no Git no início desta etapa; por isso a relação também documenta os arquivos novos, que não aparecem em um `git diff` convencional.

| Arquivo ou conjunto | Finalidade |
| --- | --- |
| `site/src/App.tsx` | Header/footer, retirada do controle manual de movimento e efeitos de ponteiro; entrada progressiva com IntersectionObserver. |
| `site/src/components/ui.tsx` | Headings sem eyebrows, navegação NFC, CTA, teclado/Escape e foco do menu; retirada de componentes sem uso. |
| `site/src/pages.tsx` | Revisão das páginas e seções, retirada de planos/numerações/QR, seção da plaquinha, contato e demo. |
| `site/src/components/product.tsx` | Telefone proporcional, plaquinha única, jornada e apresentação das capturas reais. |
| `site/src/components/Demo.tsx` | Documento isolado da demo e orientações comerciais. |
| `site/src/data/routes.ts` | 13 rotas, títulos/metadados NFC e retirada das rotas comerciais antigas. |
| `site/src/data/faq.ts` | Perguntas e respostas sem QR nem oferta de planos não confirmada. |
| `site/src/data/product-catalog.json` | Catálogo sanitizado de 22 produtos reais disponíveis e cinco categorias do QA. |
| `site/src/demo/main.tsx` | Composição dos componentes reais, navegação e estado local da demonstração. |
| `site/src/demo/api.ts` | Adaptador em memória, validações originais, totais em centavos e rejeição de operações não suportadas. |
| `site/src/demo/product-demo.css` | Controles explícitos da simulação e transição discreta, com movimento reduzido. |
| `site/src/main.tsx` | Entrada dos estilos comerciais e dos refinamentos. |
| `site/src/styles/site.css` | Limpeza dos estilos das apresentações retiradas e preservação da base visual. |
| `site/src/styles/refinements.css` | Proporção do celular, responsividade, header, contato, capturas, foco e microinterações. |
| `site/produto-demo.html` | Documento da demo com CSP restrita, noindex e estilos isolados do site. |
| `site/vite.config.js` | Entrada adicional da demo; resolução da API e fotos locais somente no build comercial; React compartilhado. |
| `site/tsconfig.json` | Importação tipada do fixture JSON. |
| `site/package.json` | Execução dos testes sem processo-filho por arquivo no ambiente restrito e auditoria pelo MCP externo. |
| `site/scripts/preview.mjs` | Preview estático com headers; somente o documento da demo permite iframe da mesma origem. |
| `site/scripts/compose_assets.py` | Interrupção da geração dos materiais comerciais de QR e planos retirados. |
| `site/scripts/asset_manifest.py` | Inventário atualizado, distinguindo captura real, item não obtido e item não aplicável. |
| `site/public/assets/screenshots/*.png` | Sete screenshots capturados na aplicação original. |
| `site/public/assets/catalog/*.webp` | Três fotos originais dos produtos do catálogo QA. |
| `site/public/brand/TapServe_logo_wordmark.svg` | Logo original no caminho esperado pelos componentes reutilizados. |
| `site/assets/originals/retired/` | Preservação dos derivados comerciais de QR/planos retirados da pasta pública. |
| `site/tests/product-demo.test.mjs` | Regras reais de produto, catálogo, valores, operações locais e reinício. |
| `site/tests/site.test.mjs` | Rotas, conteúdo, assets, links, isolamento da demo e remoções solicitadas. |
| `site/tests/http.mjs` | Respostas HTTP, assets, 404/405 e headers de segurança. |
| `site/tests/browser-audit.mjs` | Auditoria das seis larguras e fluxos interativos reais. |
| `site/tests/browser.mjs` | Cliente do Playwright MCP externo; não inicia navegador no sandbox. |
| `site/README.md` | Instruções atuais de execução, isolamento, verificação e publicação. |
| `docs/site/ASSET_MANIFEST.md`, `docs/site/TAPSERVE_ASSET_MANIFEST_V3.json` | Manifesto atualizado de 70 IDs. |
| `docs/site/REFINAMENTO_LANDING_2026-11-13.md` | Este relatório e suas pendências. |
| `graphify-out/` | Grafo e navegação atualizados após as alterações. |

Foram retirados da implementação comercial `site/src/components/Pricing.tsx`, `site/src/data/pricing.ts`, `site/src/data/demo.ts` e `site/tests/demo.test.mjs`. Os três documentos de referência originais e a arte original da plaquinha não foram modificados. Nenhum arquivo do frontend ou backend do SaaS foi editado nesta etapa.

## Origem e fidelidade das interfaces

O acesso foi realizado no **playwright-local MCP externo**, usando o navegador já configurado pelo usuário. Primeiro foi aberto `https://example.com` e capturado um screenshot de teste.

Foi localizada uma mesa **já existente**, a Mesa 08 da Unidade Centro Demo, na empresa QA. O endereço NFC verdadeiro foi obtido pelo mecanismo existente de geração de URL do próprio sistema, em consulta com transação somente leitura. O token não foi publicado nem incorporado à landing. Em seguida foi percorrido o acesso normal do cliente, com autorização do dispositivo pelo painel da equipe. Não foi necessário criar mesa, conta, PIN ou redefinir autenticação/MFA.

O acesso gerou os registros técnicos normais de login, sessão e admissão/autorização de dispositivo. **Não foram criados ou alterados pedidos, pagamentos, participantes, solicitações ou outros dados comerciais persistentes do QA.** O carrinho capturado foi apenas cotado; não foi confirmado. Os pedidos das capturas operacionais já existiam no ambiente.

| Captura em `site/public/assets/screenshots/` | Origem real |
| --- | --- |
| `S01-client-entry.png` | Início do atendimento do cliente na Mesa 08, pronto para interação. |
| `S02-client-menu.png` | Cardápio com categorias e produtos reais. |
| `S03-client-product-options.png` | Produto com suas regras de opcionais. |
| `S04-client-cart.png` | Carrinho antes de enviar o pedido. |
| `S06-client-order-status.png` | Acompanhamento dos pedidos já existentes do QA. |
| `S09-staff-tables.png` | Painel real de mesas da equipe. |
| `S13-kds-new-orders.png` | Tela real de produção, com os estados existentes do QA. |

As cinco capturas do cliente têm 390 × 844; as duas operacionais têm 1440 × 900. Catálogo e três fotos foram obtidos por leitura autenticada do aplicativo em 13/11/2026. Não há credencial ou token de admissão no fixture comercial.

A demonstração importa `MenuBrowser`, `ProductSelection`, `CartPage`, `OrdersPage`, `ServiceRequests`, `CustomerHeader`, `Button`, `Icon` e `StickyActionBar` do frontend original, além de `base.css`, `customer.css` e `motion.css`. As regras de seleção e cálculo também vêm do produto. O adaptador substitui somente a comunicação na compilação do site; rotas desconhecidas falham explicitamente. A CSP usa `connect-src 'none'`. O build verifica o trecho original que mapeia fotos e falha se ele mudar, para evitar uma integração silenciosamente incorreta.

Não foi obtida captura administrativa protegida por autenticação forte; ela não foi substituída por uma tela inventada. As demonstrações visuais limitam-se às interfaces efetivamente acessadas.

## Animações e microinterações

- Hero com entrada curta de título, apoio, ações e produto em sequência.
- Seções com entrada única de opacidade/deslocamento discreto via IntersectionObserver. Sem suporte à API, o conteúdo permanece visível.
- Botões com pequenas respostas de elevação, borda/sombra e clique; links com deslocamento sutil do ícone; foco visível preservado.
- Cards com pequena elevação, sem o antigo acompanhamento do ponteiro ou inclinação contínua.
- Abas, FAQ, menu mobile e telas da demo com transições curtas e legíveis. A área das abas tem altura estável entre Cliente, Equipe e Cozinha.
- Header com variação discreta de fundo/sombra por scroll quando a API CSS é suportada, sem depender dela para navegação.
- `prefers-reduced-motion` desativa animações/transições e rolagem suave automaticamente. Não há botão manual no footer, animação por caractere, parallax agressivo, biblioteca adicional ou movimento flutuante infinito.

## Validações e evidências

| Verificação | Resultado observado |
| --- | --- |
| TypeScript | Passou na etapa `tsc --noEmit` do comando final, antes da falha ambiental do Vite. |
| ESLint | Passou novamente na conferência final. |
| Testes Node | **8/8 passaram**, sem testes ignorados. Incluem contraste, catálogo, opcionais, limites, centavos, isolamento, rotas, contato e remoções. |
| Build de produção | Builds anteriores concluídos com bundle comercial, demo, SSR e 13 páginas + 404. **Última repetição bloqueada por `spawn EPERM`; pendente.** |
| HTTP | Passou novamente: 13 rotas, imagens/srcset/OG/assets, quatro 404 reais, POST 405 e headers. |
| Browser MCP | Suíte completa aprovada no preview: **13 rotas × seis larguras = 78 combinações**, sem overflow horizontal, sobreposição do header ou erros de console. |
| Fluxos da demo | Aprovados: filtro, busca/categorias, opcionais obrigatórios, edição/remoção/quantidade, totais, pedido local, estados, histórico, atendimento, conta e reinício. 63 requisições estáticas; nenhum erro, chamada operacional ou armazenamento. |
| Teclado e movimento | Abas, FAQ, menu, Escape/restauração de foco e preferência por movimento reduzido conferidos. |
| Touch | Contexto móvel do mesmo navegador MCP: produto + queijo, total R$ 28,90; captura salva. |
| Falha de JS/API | Conteúdo pré-renderizado conferido com JavaScript bloqueado; conteúdo continua visível sem IntersectionObserver. |
| Conferências finais | Abas com alturas `[900,900,900]` em 390 px e `[740,740,740]` em 1440 px; imagens analisadas visualmente. Nome temporário vazio e participantes vazios depois de reiniciar a demo atual em 5180. |
| Remoções | Busca e testes sem eyebrows, números decorativos, planos, controle de animações, links removidos ou comunicação pública de QR. O campo interno tipado `qr_enabled: false` da demo não é comunicação comercial nem remoção de recurso do SaaS. |
| Publicação | `check:release` bloqueou corretamente as seis aprovações pendentes. Nenhuma aprovação foi forjada. |

Larguras conferidas: **360, 390, 768, 1024, 1440 e 1920 px**. A auditoria mede também a relação física da moldura, a relação exata da tela 390/844, a plaquinha única, centralização do contato, botões com larguras iguais, assets e referências.

Evidências em `site/test-results/`:

- `browser.json`: resultados das 78 combinações e fluxos.
- `http.json`: respostas HTTP e headers.
- `hero-{largura}.png`, `home-{largura}.png`, `nfc-section-{largura}.png`, `nfc-{largura}.png`, `contato-{largura}.png` e `demonstracao-{largura}.png`: capturas das seis larguras.
- `showcase-final-390.png`, `showcase-final-1440.png`: composição final das interfaces operacionais.
- `touch-demo-390.png`, `no-javascript.png`, `demo-cart-desktop.png`, `after-demo-desktop.png`: verificações complementares.

As capturas principais de hero, celular, plaquinha, contato, demo e abas foram abertas e analisadas visualmente, além das medições automatizadas. A ausência de erros relatada pela suíte corresponde ao **preview de produção**, não ao Vite de desenvolvimento.

`graphify update .` gravou o grafo atualizado, com 2676 nós e 9540 relações. O CLI apresentou ciclos repetidos de indexação e avisos de extração paralela no Windows; uma execução foi interrompida após salvar. O JSON foi validado e uma consulta posterior localizou `ProductDemo`, `restart`, `Showcase`, `NfcPlaque` e suas relações com os componentes reais. Não foi omitida a atualização por o grafo estar sem rastreamento no Git.

## Pendências reais e limites

1. **Repetir o build final em um processo Windows com permissão normal para subprocessos.** O bloqueio atual ocorre no Vite/Windows, não em diagnóstico de TypeScript ou regra de aplicação. Não foi contornado por elevação, alteração do SaaS ou enfraquecimento da CSP. A saída da tentativa está em `.local/site-final-build.log`.
2. **Servidor Vite em 5180:** a navegação e a demo funcionam, mas o cliente de desenvolvimento emite dois avisos de WebSocket bloqueado pela CSP. O preview estático em 4321 não emite esses erros. O HMR está desativado; a CSP restrita foi preservada.
3. **Publicação:** seis aprovações humanas e minutas jurídicas continuam pendentes em `RELEASE_APPROVALS.json`. Este trabalho não autoriza publicação.
4. **Cobertura:** não houve teste em Safari/Firefox, aparelho físico, leitura física de NFC ou medição de Core Web Vitals de usuários reais. A inspeção utilizou o Chromium do MCP externo, incluindo emulação touch e movimento reduzido. Não se declara certificação de acessibilidade completa nem métricas de campo.
5. **Capturas do QA:** mostram dados demonstrativos existentes e podem envelhecer. Screenshots operacionais são imagens exploráveis por rolagem; apenas a demo do cliente é interativa. Uma atualização futura do produto exige recaptura e nova validação da integração comercial.

Não foram identificadas regressões funcionais nos cenários executados. A reprodução do build final permanece explicitamente pendente pelo bloqueio ambiental acima; este relatório não declara aprovação integral dessa etapa.
