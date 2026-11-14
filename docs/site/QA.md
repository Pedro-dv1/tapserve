# QA técnico — 13/11/2026

## Resultados observados

| Verificação | Resultado | Evidência e limite |
|---|---|---|
| `npm.cmd run lint` | PASSOU | ESLint, sem erros; somente código novo do site |
| `npm.cmd run typecheck` | PASSOU | TypeScript estrito; também incluído no build |
| `npm.cmd run build` | PASSOU | Cliente + SSR de build + 14 HTMLs por rota + 404; sem backend |
| `npm.cmd test` | 10 PASSARAM, 0 falhas | Regras/fluxos em memória, cálculos, validação, catálogo, links, HTML, privacidade do código e contraste de cores planas |
| `npm.cmd run test:http` | PASSOU | 14 rotas HTTP200, assets/srcset/OG carregáveis, quatro rotas ausentes HTTP404, POST405, headers |
| Validação Pillow | PASSOU | 68 imagens raster públicas decodificadas; cinco OG 1200×630; originais separados |
| Plaquinha | INSPECIONADA | Composição F02 e O01 vistas; corte da arte original, sem recriação/QR; escala/luz/acrílico ainda precisam de aprovação física/visual |
| Fotografias | INSPECIONADAS | Geração real, 19 selecionadas; painel VISUAL_BOARD.jpg; D03/D04 corrigidos após conteúdos inadequados; F17 lettering da máquina removido pelo imagegen |
| `npm.cmd run check:release` | BLOQUEIO ESPERADO | Retorna código 1: seis categorias de aprovação ausentes. Não é teste funcional falhando |
| `git diff --check` | PASSOU | Avisos LF→CRLF de arquivos preexistentes não são falhas de espaço; nenhum conteúdo deles foi reformulado |
| `graphify update .` | PASSOU | AST sem LLM; grafo atualizado e demo encontrada por query |

## O que os testes da demo provaram

Obrigatórios, SINGLE/MULTIPLE, min/max, IDs inválidos e duplicados, quantidades fracionárias/fora de 1–20, limite de 20 linhas, carrinho vazio, alteração de quantidades, edição de opções, remoção, valores inteiros em centavos, confirmação única, cópia do pedido, transições limitadas aos quatro estados e reset completo. Chamados e conta geram mensagens explicitamente simuladas. Todos os oito produtos podem ser escolhidos com seus mínimos válidos.

O fluxo de regressão usa hambúrguer + adicionais + batata, confere totais e edita/remove antes de confirmar. O simulador comercial testa 50→51→70→71 mesas, limites de unidades, Pro 80→81 e entradas inválidas; as mesas são compartilhadas e pacotes arredondam para cima.

Os testes estáticos verificam um H1 por rota, metadata, noindex, ausência de formulários e `/obrigado`, destinos centralizados, identificadores ausentes do texto de Contato/Suporte, links/imagens locais, rotas legais sem placeholders públicos e ausência de APIs/rede/storage no código cliente. A CSP de produção é `connect-src 'none'`; o servidor local recusa POST. Isso não substitui observar requests num navegador nem auditar futura infraestrutura.

## Navegador e inspeção visual: PENDENTES

1. CUA: inventário sem superfícies; criação de tab retornou `Browser is not available: iab`.
2. Playwright padrão: executável Chromium headless shell ausente.
3. Google Chrome instalado: lançamento headless com `chromiumSandbox: true` retornou **`browserType.launch: spawn EPERM`**.

Não foi solicitado privilégio, alterada proteção do Windows, desativado sandbox ou reutilizado perfil do usuário para contornar o bloqueio. `site/test-results/browser.json` e a cópia `EVIDENCIA_BROWSER.json` registram a falha. A suíte `site/tests/browser.mjs` está pronta para execução local, mas **não passou nem chegou às interações neste ambiente**.

Assim, NÃO foram verificados visualmente: 320/390/834/1440px, overflow renderizado, hierarquia/contraste sobre fotografias, foco real, teclado/toque, menu, tabs, scroll, animações, comportamento da demo no browser, hidratação/console, outros navegadores, leitor de tela e impressão. O CSS e os controles correspondentes foram implementados e revistos; implementação não equivale a resultado visual aprovado.

## Acessibilidade e performance

Verificado no código: links/botões semânticos, labels, fieldsets, alt, skip link, foco visível, tabs com setas/Home/End, accordions nativos, anúncios locais, min/max, reduced motion e controle global. Teste numérico aprovou contraste mínimo 4,5:1 em sete pares de cores planas. Contraste sobre foto e controles efetivamente renderizados dependem de QA visual.

Build observado: JS principal ~290 kB (~89 kB gzip), CSS ~51 kB (~11 kB gzip). Todos os assets públicos somam ~7,54 MB **incluindo variantes não baixadas juntas**. Hero tem srcset e prioridade; outras fotografias e produtos têm tamanhos reservados e lazy loading; masters não são servidos por `public/`. Ausência de vídeo pesado/trackers. Esses valores de bundle/arquivos não são benchmark de experiência.

**Lighthouse, LCP, INP e CLS não foram medidos.** A suíte de navegador possui captura de LCP/CLS local, mas não a executou devido ao bloqueio. Medir no host/dispositivo/rede representativos antes do lançamento.

## Reprodução

Seguir `site/README.md`. Executar preview em um terminal e `test:http`/`test:browser` em outro. Manter a prévia em loopback. Resolver o bloqueio de execução pelo ambiente apropriado, sem enfraquecer controles. Após QA, registrar defeitos e evidências; somente marcar `qa_final_de_lancamento` aprovado com revisores e provas reais.
