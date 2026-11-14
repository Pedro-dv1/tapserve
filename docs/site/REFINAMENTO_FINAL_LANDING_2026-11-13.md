# Refinamento final da landing page TapServe — 13/11/2026

## Status

**APROVADA COM RESSALVAS.** As alterações foram implementadas e as verificações de código, produção, responsividade, imagens e interação passaram. A ressalva é a seleção de três produtos com fotos originais completas; os outros 19 produtos do fixture QA não possuem foto de origem e não foram preenchidos com mídia inventada. A entrega é uma prévia local para apresentação e revisão, sem publicação.

Preview de produção: **http://127.0.0.1:4321**. Desenvolvimento: **http://127.0.0.1:5180**.

## Alterações implementadas

1. **Aviso da demo:** removido integralmente o parágrafo solicitado e seus estilos/espaçamentos exclusivos. Os controles existentes de reinício e simulação continuam nos locais apropriados. O adaptador em memória e a CSP `connect-src 'none'` foram preservados.
2. **Imagens da demonstração:** a apresentação seleciona Hambúrguer Clássico, Batata Frita e Suco Natural, os três produtos QA com fotos originais disponíveis. Não foram atribuídas fotos aleatórias aos outros produtos. Produto, categorias, opcionais, quantidades, carrinho, participantes, atendimento e pedidos continuam usando a interface original.
3. **Antes do primeiro toque:** adicionada abaixo do título/apoio a fotografia editorial já existente `F04-customer-using-menu`. A foto aparece a partir de 1024 px, na composição desktop de duas colunas. Em telas menores permanece oculta, sem novo espaço reservado. Usa proporção 4:3, acabamento de 8 px, `object-fit: cover` e carregamento lazy. O alt mantém a identificação da imagem ilustrativa gerada, sem alegar que retrata um cliente real.
4. **Funcionalidades:** retirado o bloco “Acesso para cada responsabilidade”, sem alterar as permissões do aplicativo nem os demais recursos apresentados. Não há card ou coluna vazia no lugar.
5. **CTA da demo:** alinhamento central em fluxo normal, largura adequada ao mobile e padding inferior responsivo entre 64 e 112 px. O destino continua `/contato`; não há posição absoluta ou margem negativa.
6. **Dúvidas:** título e subtítulo centralizados. Busca, filtros, perguntas e respostas conservam seu alinhamento de leitura.
7. **404:** número em preto/âmbar, título “Essa página não está no cardápio.”, descrição solicitada e botão “Voltar ao início”. Composição centralizada e responsiva; título e descrição próprios para SEO. A geração estática emite `404.html`; o servidor de preview retorna HTTP 404 para endereços inexistentes, inclusive acessos diretos a caminhos aninhados. Nenhum roteador do SaaS ou da API foi alterado.
8. **Preloader:** símbolo SVG oficial, sem redesenho ou alteração de proporção/cor. O fallback visual existe somente enquanto o módulo da demo ainda não iniciou. A marca só aparece depois de 180 ms, evitando flashes sem impor espera mínima; a interface o substitui assim que inicia. Após oito segundos, o movimento cede lugar a links de recuperação. Um bootstrap de 840 bytes controla a visibilidade independentemente das animações, e limpa os timers quando a interface inicia. Se esse próprio bootstrap não carregar, os links de recuperação permanecem disponíveis no HTML. Não há overlay global, captura de foco ou preloader nas páginas comerciais já pré-renderizadas. A preferência por movimento reduzido é respeitada.

## Causas e correções das imagens

O fixture QA preservado contém **22 produtos; 19 têm `has_image: false` e nenhuma foto adicional**. Esses espaços eram o fallback original do produto para ausência de mídia, não erro de capitalização ou CORS. As três imagens efetivamente disponíveis carregaram depois de entrar no viewport; uma imagem lazy fora da tela não deve ser classificada como quebrada antes da rolagem.

A demo agora apresenta somente a seleção com mídia original completa, com as três categorias correspondentes. O fixture completo não foi apagado nem o catálogo do QA foi alterado. Esta seleção reduz o conteúdo de exemplo, mantendo os componentes e os fluxos reais da interface.

| Produto | Asset original exportado para a landing |
| --- | --- |
| Hambúrguer Clássico | `site/public/assets/catalog/a78686ba-876a-56f8-94d2-346c8c780b99.webp` |
| Batata Frita | `site/public/assets/catalog/5d1a617c-acda-5d0f-8e19-867a80ef78ef.webp` |
| Suco Natural | `site/public/assets/catalog/21b43439-d413-505c-ba66-968bb83f8ae5.webp` |

O mapeamento das imagens continua restrito ao build comercial. Foi removida a regra que convertia silenciosamente um asset ausente em fallback. Agora a configuração lê cada foto selecionada, valida sua assinatura WebP e interrompe o build se o arquivo estiver ausente/inválido ou se novas mídias adicionais ainda não tiverem sido exportadas. O fallback original `onError` fica reservado a uma falha real de carregamento. Não houve inclusão de URLs externas, proxy de mídia, fotos genéricas ou acesso operacional pela demo.

## Principais arquivos modificados

| Caminho | Finalidade |
| --- | --- |
| `site/src/components/Demo.tsx` | Retirada do aviso solicitado. |
| `site/src/demo/api.ts` | Seleção dos produtos com mídia original e categorias correspondentes. |
| `site/vite.config.js` | Validação dos assets, mapeamento local e falha explícita diante de mídia incompleta. |
| `site/src/pages.tsx` | Foto desktop, retirada do bloco de permissões, intro de dúvidas e nova 404. |
| `site/src/styles/refinements.css` | Estilos delimitados à foto, CTA, centralização e 404; retirada dos estilos do aviso. |
| `site/src/data/routes.ts` | Metadados únicos da 404. |
| `site/src/main.tsx` | Título correto na navegação para endereço inexistente. |
| `site/src/render.tsx` | Exportação dos metadados compartilhados para SSR. |
| `site/scripts/prerender.mjs` | Geração do documento 404 com os novos metadados. |
| `site/produto-demo.html` | Fallback inicial com marca e links de recuperação. |
| `site/public/assets/brand/loader.css` | Marca centralizada, ciclos limitados e movimento reduzido. |
| `site/public/assets/brand/loader.js` | Atraso contra flash, recuperação e limpeza dos timers, independentes do CSS de movimento. |
| `site/tests/product-demo.test.mjs` | Integridade das três fotos, categorias e exclusão de amostras sem mídia. |
| `site/tests/site.test.mjs` | Regressões de conteúdo, foto desktop, 404 e fallback de inicialização. |
| `site/tests/http.mjs` | Status, texto, título e retorno ao início na 404. |
| `site/tests/browser-audit.mjs` | Responsividade, CTA, foto por breakpoint, dúvidas e 404. |
| `site/tests/media-loader-audit.mjs` | Fotos de cards/detalhes e carregamento lento/recuperação do preloader. |
| `site/tests/browser.mjs` | Execução das oito larguras e novas auditorias pelo MCP externo. |
| `site/README.md` | Catálogo selecionado, preloader e comandos/resultados atuais. |
| `docs/site/REFINAMENTO_FINAL_LANDING_2026-11-13.md` | Este relatório. |
| `graphify-out/` | Grafo atualizado após as mudanças. |

Não foram adicionadas dependências. Os documentos de referência, os assets originais, o fixture completo e os arquivos do SaaS foram preservados. Não foram alterados bancos de dados, fluxos operacionais, credenciais ou pedidos reais nesta etapa.

## Verificação já concluída

- `npm.cmd run typecheck`: aprovado.
- `npm.cmd run lint`: aprovado.
- `npm.cmd run build`: aprovado no código final — cliente comercial e demo, SSR e 13 páginas + 404. Uma repetição intermediária encontrou `spawn EPERM` no auxiliar do Vite/Windows; a execução padrão seguinte concluiu sem alterar permissões ou segurança do sistema. Não ficou pendência de build.
- `npm.cmd test`: **9/9 aprovados**, sem testes ignorados.
- `node --check public/assets/brand/loader.js`: aprovado; o comportamento também foi verificado no navegador.
- `npm.cmd run test:http`: aprovado — 13 rotas, assets/srcset/OG, quatro respostas 404, POST 405 e headers.
- Verificações finais de remoção e `git diff --check`: sem ocorrências indevidas nos arquivos verificados.
- Graphify atualizado; avisos do indexador no Windows não impediram a gravação do grafo.

## Auditoria visual e funcional concluída

A execução utiliza exclusivamente o **playwright-local MCP externo em 8931**. Nenhum Playwright ou navegador foi iniciado pelo sandbox.

As 13 rotas institucionais e uma rota inexistente são verificadas em **360, 390, 430, 768, 1024, 1280, 1440 e 1920 px**. As asserções cobrem overflow, header, proporção do celular, imagens, remoções, foto restrita ao desktop, alinhamento do CTA e contato, dúvidas e status 404. Screenshots são salvos em `site/test-results/`.

**Resultado: 112 combinações aprovadas — 14 rotas × oito larguras**, com screenshots, proporções, alinhamentos, assets e console. A navegação para a rota inexistente retorna o 404 esperado; esse registro de navegação é distinguido de falhas inesperadas de recursos.

Os fluxos dos componentes reais passaram: categorias, opcionais obrigatórios, quantidade, edição e remoção, totais exatos, pedidos locais, progressão e histórico, atendimento, conta, reinício, teclado, foco e movimento reduzido. Foram observadas 74 requisições estáticas nessa auditoria de interação, sem erro de console, chamada operacional, cookie ou armazenamento.

A auditoria de mídia abriu os três produtos, carregou e decodificou cada foto nos cards e nas telas de detalhes e confirmou ausência de placeholders permanentes. O módulo real de inicialização foi atrasado pelo navegador para verificar marca, proporção, movimento reduzido, links após oito segundos e retirada do preloader quando o módulo foi liberado. Uma consulta posterior do console retornou **zero erros e zero avisos**.

A revisão final detectou que o CSS global de movimento reduzido do produto também cancelava as animações usadas inicialmente para temporizar o fallback. Essa dependência foi removida: o bootstrap controla a visibilidade e o CSS controla apenas o movimento. O teste repetido confirmou que ativar movimento reduzido não antecipa nem impede a recuperação, que a marca é ocultada após o prazo e que o módulo liberado substitui o fallback. Depois dessa correção, build, testes, HTTP e a auditoria específica de mídia/preloader passaram novamente.

Também foram conferidos no navegador o refresh direto da rota inexistente (404), o retorno ao início pelo teclado, a navegação do header para funcionalidades e o CTA da demo chegando à página de contato.

As capturas de mobile/desktop da 404, foto do FAQ, título de dúvidas, CTA/demo, produtos e estados do preloader foram abertas e analisadas visualmente. Na revisão, o preloader recebeu centralização pela altura integral da área e limite de ciclos, para não manter animações após a recuperação. O restante das páginas não recebeu reformulação visual.

Uma execução preliminar aguardava `decode()` de uma foto lazy antes de rolar até ela e causou timeout da conexão. A ordem do teste foi corrigida; o usuário fechou a janela externa para liberar a sessão, e a suíte completa foi executada novamente com sucesso. O incidente não foi tratado como defeito do site.

Evidências:

- `site/test-results/browser.json`: oito larguras, 112 resultados, interação e auditoria de mídia/preloader.
- `site/test-results/http.json`: rotas, status e headers.
- `faq-section-{largura}.png`, `duvidas-{largura}.png`, `demonstracao-{largura}.png`, `funcionalidades-{largura}.png` e `404-{largura}.png`: áreas alteradas nas oito larguras.
- `product-1-390.png`, `product-2-390.png`, `product-3-390.png`: detalhes com as fotos originais.
- `preloader-390.png` e `preloader-recovery-390.png`: carregamento real atrasado e recuperação.
- `preloader-final.json`: repetição final após a correção de temporização e movimento reduzido.
- `navigation-final.json`: refresh 404, teclado, navegação e destino do CTA.

## Limites e publicação

- Para demonstrar os outros 19 produtos com imagens será necessário fornecer/exportar as fotos originais correspondentes. Não há impedimento para usar os três produtos já selecionados; nenhuma mídia foi inventada.
- Não foi realizado deploy, teste em um host público, leitura física NFC ou medição de Core Web Vitals de usuários reais. O fallback 404 foi verificado no artefato estático e no preview do projeto.
- Safari e Firefox não fazem parte desta auditoria Chromium.
- As aprovações de publicação e revisão jurídica existentes continuam sob controle do projeto. O preview mantém noindex e não equivale a autorização de lançamento.
