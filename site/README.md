# TapServe — site comercial

Site independente em React/TypeScript. A comunicação apresenta a experiência NFC; planos e a antiga rota comercial com QR foram retirados. As 13 páginas comerciais têm HTML pré-renderizado. Não há formulário de contato, coleta de leads, cookies ou armazenamento da demonstração.

## Execução local

Node >=22.12; no Windows, use `npm.cmd`.

```powershell
cd C:\Users\pedro\Desktop\tapserve\site
npm.cmd run build
npm.cmd run preview
```

Preview de produção: **http://127.0.0.1:4321**. Escuta apenas em loopback; aceita GET/HEAD, devolve 404 reais e bloqueia escrita HTTP. Encerre com Ctrl+C.

Desenvolvimento: `npm.cmd run dev -- --port 5180`. HMR fica desativado para manter `connect-src 'none'`; recarregue a página depois de editar. O cliente do Vite ainda pode registrar tentativas de WebSocket bloqueadas pela CSP; use o preview estático para a auditoria de produção. Alterações em `vite.config.js` exigem reiniciar o servidor.

## Demonstração fiel e isolada

`src/demo/` importa componentes e estilos originais de `../frontend/`: cardápio, produto/opcionais, carrinho, pedidos e atendimento. O frontend e o backend do SaaS não são editados por esse mecanismo.

Somente no build do site, `vite.config.js` resolve o módulo de API dos componentes para `src/demo/api.ts`. Esse adaptador responde em memória e rejeita operações não previstas. Fotos de produto são mapeadas para arquivos estáticos. O build falha se o trecho de `ProductImage` usado pelo mapeamento mudar. CSP proíbe conexões de rede. Não há proxy operacional, autenticação ou persistência na demo.

`produto-demo.html` é um documento separado para isolar o CSS do produto. Apenas essa rota admite iframe da mesma origem (`SAMEORIGIN`); as páginas comerciais continuam com `DENY`. O host de produção deve preservar essa distinção.

O fixture preserva 22 produtos da Unidade Centro Demo do QA, consultados em 13/11/2026. A apresentação interativa seleciona os três produtos com fotos originais disponíveis: Hambúrguer Clássico, Batata Frita e Suco Natural. Os outros 19 não têm foto no catálogo de origem e não são apresentados com placeholders. Categorias, produto, opcionais, carrinho e pedidos continuam usando os componentes reais. O build verifica a existência e o formato das fotos selecionadas. Dados e valores são exemplos. As sete capturas em `public/assets/screenshots/` vieram do aplicativo real, pela Mesa 08 e pelo painel operacional. Origem: [relatório anterior](../docs/site/REFINAMENTO_LANDING_2026-11-13.md) e [manifesto](../docs/site/ASSET_MANIFEST.md).

O preloader está em `produto-demo.html` e usa o símbolo oficial, sem alterar proporções ou cores. Aparece depois de 180 ms apenas se o módulo ainda estiver carregando, é substituído pela interface assim que ela inicia e oferece recuperação após oito segundos. `public/assets/brand/loader.js` controla a visibilidade sem depender das animações CSS e limpa seus timers quando a interface inicia. Não há espera mínima nem overlay nas páginas comerciais pré-renderizadas. A animação respeita movimento reduzido; se o próprio bootstrap falhar, os links de recuperação permanecem disponíveis no HTML.

## Verificação

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npm.cmd test
npm.cmd run test:http
npm.cmd run test:browser
```

As duas últimas verificações precisam do preview aberto. `test:browser` usa o servidor **playwright-local MCP em http://127.0.0.1:8931/mcp**; não inicia um navegador pelo sandbox. Se o navegador já estiver reservado por uma sessão MCP, informe o identificador dessa sessão por `TAPSERVE_MCP_SESSION`, sem imprimi-lo. A suíte valida 13 rotas e uma rota inexistente em 360, 390, 430, 768, 1024, 1280, 1440 e 1920 px, os fluxos interativos, todas as fotos selecionadas e o preloader lento/recuperação. Evidências e screenshots ficam em `test-results/`.

No refinamento final, TypeScript, lint, build de produção, nove testes e HTTP passaram. A auditoria MCP aprovou 112 combinações de rota/largura, os fluxos interativos e as fotos. O preloader final passou novamente após a correção de temporização em movimento reduzido. Uma tentativa intermediária de build encontrou `spawn EPERM`; a execução padrão seguinte concluiu sem alterações de segurança no sistema. Resultados e limitações estão no [relatório final](../docs/site/REFINAMENTO_FINAL_LANDING_2026-11-13.md).

## Assets e publicação

Logo e plaquinha originais são preservados. `scripts/compose_assets.py` mantém os derivados da arte original e deixou de gerar material para planos ou ícone comercial de QR. Os arquivos retirados estão arquivados em `assets/originals/retired/`. `scripts/asset_manifest.py` atualiza o inventário de 70 IDs, distinguindo capturas reais, não capturados e itens não aplicáveis.

`/privacidade` e `/termos` apresentam os documentos completos, com versão de 14/11/2026, índice por seção e campos pendentes explicitamente sinalizados. O conteúdo e o estilo estão em `../frontend/src/legal/` e são reutilizados nas rotas públicas do aplicativo, sem autenticação. Os contatos também são compartilhados. Não há banner de cookies porque o site não implementa tecnologias opcionais; login não é tratado como aceite contratual e a contratação continua externa ao software.

Antes da publicação, preencher identificação jurídica, inscrição, endereço, encarregado ou responsável pelo canal, prestadores e países, retenção e descarte, avaliação e medidas para menores, condições comerciais e vigência. O site permanece noindex, com robots Disallow e sitemap vazio; não houve deploy. `npm.cmd run check:release` continua verificando as evidências reais em `../docs/site/RELEASE_APPROVALS.json`; esta implementação não preenche aprovações de publicação.
