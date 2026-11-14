# TapServe — Asset Sheet completo V3

**Uso:** inventário operacional de todos os materiais visuais que serão fornecidos para o Codex e daqueles que ele poderá produzir.  
**Origem:** a arquitetura `TAPSERVE_ARQUITETURA_SITE_V2_CONTATO_JURIDICO.md` (59 itens B/F/S/C/V/O) + adendo para demo clicável (8 fotos D) + camadas de animação NFC (3 itens M).  
**Total:** **70 entregáveis mapeados**, sendo **56 P0** (para o site completo na qualidade desejada) e **14 P1** (melhorias pós-base).  
**P0 não significa que tudo precisa estar pronto para iniciar o código.** Significa que o item deve estar resolvido, substituído por solução aprovada ou marcado como não aplicável antes de considerar a experiência final concluída.

## 0. Prioridade real: o que VOCÊ precisa disponibilizar primeiro

1. **Logotipo original** (`B01`) em SVG ou PNG de alta resolução sem fundo; se possuir símbolo isolado, enviar também (`B03`).
2. **Arte FINAL do card NFC/QR** em SVG/PDF/PNG de alta resolução (arquivo-fonte separado do asset sheet), dimensões exatas e versões aprovadas. O cartão é **horizontal, largo, branco e colado à mesa**; wordmark preto, área/círculo preto incluindo o "Aproxime aqui"; QR só na variante com QR.
3. **Acesso de demonstração seguro** ao TapServe para capturar `S01–S20`, com dados fictícios e sem acesso ao ambiente de produção. Se houver bloqueio do navegador/Codex, capturar manualmente PNGs.
4. **Conferir catálogo da simulação** (oito itens D01–D08 e categorias/produtos/opcionais) — são exemplos comerciais, não itens reais de restaurante. As fotos podem ser geradas ou fotografadas.
5. **Aprovar a direção fotográfica** antes de produzir lote: restaurante elegante, tons neutros, luz quente, consistência, estética realista, sem marcas de terceiros. Usar o TapServe verdadeiro nos locais em que aparecem tela/logo/card.
6. **Validar a copy e planos**, aprovar dados da empresa para documentos jurídicos e revisar o material antes de publicar.

**Não faça manualmente** os ícones B04–B06, as composições C01–C06, capas O01–O05 nem os efeitos GSAP/CSS V02–V04, a menos que queira controle artístico extra. Esses itens normalmente podem ser feitos pelo Codex a partir dos originais aprovados.

## 1. Regras de produção

- Produzir arquivos **mestres** nas dimensões propostas e preservar os originais; o Codex cria derivados AVIF/WebP/mobile otimizados e `srcset`.
- Fotografia é ilustração; **telas do TapServe devem ser capturas reais**. Nunca deixar interface gerada por IA fingindo representar a versão comercial.
- Não aceitar arte do cartão com texto deformado, logotipo recriado, proporções erradas ou suporte vertical. Aplicar a arte fonte por composição fiel.
- Cada material com o mesmo ID da tabela. Se mudar extensão, atualizar o `TAPSERVE_ASSET_MANIFEST_V3.json` e documentar.
- Não usar fotos extraídas das landing pages dos concorrentes sem licença.
- Se houver rosto de pessoa real, garantir direitos de uso de imagem e tratamento apropriado; preferir modelos com autorização ou cenas geradas.
- No site, os botões de contato/suporte são **Enviar mensagem** e **Enviar e-mail**, com ícones, sem exibir identificadores como texto nessas seções, sem formulário e sem rota `/obrigado`. Isso não elimina exigências legais de identificação do fornecedor.
- Demo de pedido: **simulada e isolada**; sem requisições de escrita ao backend ou ambiente produtivo; status e notificações apenas ilustrativos, rotulados como demonstração.
- Motion: transições elegantes + mouse parallax, cartões interativos, hotspots, scroll cinematográfico. Em mobile, adaptar para toque; implementar `prefers-reduced-motion`, pausa e fallback estático.

## 2. Lista detalhada — os 70 materiais


### Identidade (6)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| B01 | `B01-logo-wordmark-black.svg` | Wordmark ORIGINAL aprovado com fundo transparente, sem recriar letras ou proporções. | vetor | P0 | Você: original |
| B02 | `B02-logo-wordmark-light.svg` | Variante OFICIAL aprovada em branco/tonalidade original para seções escuras. | vetor | P0 | Designer/Codex: adaptação aprovada |
| B03 | `B03-logo-symbol.svg` | Símbolo real da marca, se houver; não inventar um mascote ou novo símbolo. | vetor | P0 | Você ou designer |
| B04 | `B04-favicon.svg` | Derivado da marca oficial, reconhecível em 16, 32 e 48 px. | vetor | P0 | Codex/designer |
| B05 | `B05-icon-nfc.svg` | Ícone vetorial coerente com a identidade; não é símbolo funcional de pagamento. | vetor | P0 | Codex/designer |
| B06 | `B06-icon-qr.svg` | Ícone vetorial de referência de QR; não deve ser escaneável se for decorativo. | vetor | P0 | Codex/designer |


### Fotografias (18)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| F01 | `F01-hero-restaurant-wide.webp` | Foto wide premium: mesa em destaque no primeiro plano, restaurante contemporâneo ao fundo, espaço negativo para título. | 2400×1350 (16:9) | P0 | Você + IA de imagens/fotógrafo |
| F02 | `F02-card-fixed-on-table.webp` | Close da arte ORIGINAL em um cartão horizontal branco colado diretamente à mesa; círculo preto NFC. | 1600×1200 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F03 | `F03-phone-near-card.webp` | Mão com smartphone aproximando da área NFC física; câmera plausível, tela preparada para sobreposição real. | 1600×1200 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F04 | `F04-customer-using-menu.webp` | Cliente adulto em restaurante usando smartphone de modo natural; a tela final recebe captura verdadeira do TapServe. | 1600×1200 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F05 | `F05-food-and-phone.webp` | Foto editorial de comida no restaurante, celular como elemento secundário, sem logotipos fictícios. | 1600×1200 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F06 | `F06-staff-on-floor.webp` | Garçom/funcionário em restaurante com dispositivo de atendimento; contexto de operação realista. | 1600×1200 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F07 | `F07-kitchen-kds-real.webp` | Cozinha de restaurante com monitor; inserir a captura REAL S13/S14 na tela do monitor. | 1600×1200 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F08 | `F08-card-product-45deg.webp` | Produto físico premium: adesivo/cartão branco HORIZONTAL fixado à mesa, material e arte oficial nítidos. | 1800×1350 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F09 | `F09-card-topdown.webp` | Vista ortográfica de cima; wordmark e círculo NFC totalmente legíveis, geometria fiel ao card original. | 1800×1350 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F10 | `F10-card-macro-nfc.webp` | Macro fotográfica do círculo preto e indicação "Aproxime aqui", com fidelidade tipográfica. | 1800×1350 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F11 | `F11-card-qr-closeup.webp` | Variante física com QR Code verdadeiro para uma URL de demo aprovada ou identificado como ilustrativo. | 1800×1350 (4:3) | P0 | Você + IA de imagens/fotógrafo |
| F12 | `F12-card-lifestyle-table.webp` | Card original fixado em mesa de restaurante com pratos e copos; contexto lifestyle sem suporte vertical. | 1800×1350 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F13 | `F13-venue-restaurant.webp` | Fotografia editorial de salão de restaurante; coerente com campanha visual. | 1600×1200 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F14 | `F14-venue-hamburger.webp` | Fotografia editorial de hamburgueria contemporânea, de preferência mercado brasileiro. | 1600×1200 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F15 | `F15-venue-snack.webp` | Fotografia realista de lanchonete limpa e acessível. | 1600×1200 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F16 | `F16-venue-bar.webp` | Fotografia de bar contemporâneo, iluminação quente e ambiente profissional. | 1600×1200 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F17 | `F17-venue-cafe.webp` | Fotografia de cafeteria contemporânea, iluminação natural/quente. | 1600×1200 (4:3) | P1 | Você + IA de imagens/fotógrafo |
| F18 | `F18-final-cta-restaurant.webp` | Fotografia horizontal distinta do hero com atmosfera premium e espaço para CTA final. | 2400×1100 (~2.18:1) | P1 | Você + IA de imagens/fotógrafo |


### Screenshots (20)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| S01 | `S01-client-entry.png` | Abertura do cliente com identificação de mesa e ações principais | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S02 | `S02-client-menu.png` | Categorias, produtos e navegação do cardápio | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S03 | `S03-client-product-options.png` | Detalhe, grupos de opções, quantidade e valores | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S04 | `S04-client-cart.png` | Carrinho com itens reais da simulação | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S05 | `S05-client-order-confirmed.png` | Estado correto de confirmação de pedido | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S06 | `S06-client-order-status.png` | Status visual do pedido conforme aplicativo verdadeiro | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S07 | `S07-client-call-staff.png` | Ação/chamado de atendimento | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S08 | `S08-client-check-request.png` | Solicitação de conta pelo cliente | Mobile 390×844 referência | P0 | Codex com ambiente demo; ou você |
| S09 | `S09-staff-tables.png` | Painel de mesas da equipe | Mobile/tablet: captura real | P0 | Codex com ambiente demo; ou você |
| S10 | `S10-staff-orders.png` | Fila/listagem de pedidos | Mobile/tablet: captura real | P0 | Codex com ambiente demo; ou você |
| S11 | `S11-staff-service-requests.png` | Lista/estado de chamados de atendimento | Mobile/tablet: captura real | P0 | Codex com ambiente demo; ou você |
| S12 | `S12-staff-order-detail.png` | Detalhamento de pedido ou mesa da equipe | Mobile/tablet: captura real | P1 | Codex com ambiente demo; ou você |
| S13 | `S13-kds-new-orders.png` | Quadro de produção com pedidos novos | Desktop/tablet 1440×900 referência | P0 | Codex com ambiente demo; ou você |
| S14 | `S14-kds-preparing.png` | Quadro com pedidos em preparo | Desktop/tablet 1440×900 referência | P0 | Codex com ambiente demo; ou você |
| S15 | `S15-kds-ready.png` | Quadro de pedidos prontos/entrega | Desktop/tablet 1440×900 referência | P1 | Codex com ambiente demo; ou você |
| S16 | `S16-admin-dashboard.png` | Tela principal do painel administrativo | Desktop/tablet 1440×900 referência | P0 | Codex com ambiente demo; ou você |
| S17 | `S17-admin-menu-management.png` | Painel real para configurar produtos/cardápio | Desktop/tablet 1440×900 referência | P0 | Codex com ambiente demo; ou você |
| S18 | `S18-admin-staff-units.png` | Gerenciamento de unidades e equipe | Desktop/tablet 1440×900 referência | P1 | Codex com ambiente demo; ou você |
| S19 | `S19-admin-reports.png` | Relatórios verdadeiros, se disponíveis | Desktop/tablet 1440×900 referência | P1 | Codex com ambiente demo; ou você |
| S20 | `S20-admin-table-status.png` | Estado e acompanhamento de mesa/conta | Desktop/tablet 1440×900 referência | P1 | Codex com ambiente demo; ou você |


### Composições (6)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| C01 | `C01-hero-product-composite.webp` | Imagem/cena principal unindo restaurante, card original e celular com S01; texto não embutido. | 2400×1350 ou composição DOM | P0 | Codex/designer |
| C02 | `C02-card-to-phone.webp` | Montagem com transição NFC e entrada visual da interface no smartphone. | 1600×1200 ou composição DOM | P0 | Codex/designer |
| C03 | `C03-ordering-phone-sequence.webp` | Montagem consistente de celular mostrando cardápio→opcionais→carrinho→pedido. | 1600×1200 ou composição DOM | P0 | Codex/designer |
| C04 | `C04-order-to-kds.webp` | Montagem visual do cliente fazendo pedido e a cozinha recebendo no KDS. | 2000×1250 ou composição DOM | P0 | Codex/designer |
| C05 | `C05-nfc-card-gallery.webp` | Tratamento visual consistente de card em vários ângulos. | 1600×1200 ou galeria HTML | P0 | Codex/designer |
| C06 | `C06-tapserve-ecosystem.webp` | Quatro telas reais: cliente, equipe, KDS, admin, bem hierarquizadas. | 2000×1300 ou composição DOM | P0 | Codex/designer |


### Motion (4)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| V01 | `V01-hero-loop.webm` | 6–8s, restaurante e card com movimento leve, sem texto embutido; poster obrigatório. | 1920×1080 (16:9) | P1 | Codex + designer de motion |
| V02 | `V02-nfc-approach.tsx` | 4–6s equivalentes: celular aproxima → sinal visual ilustrativo → browser revela S01. | Desktop 16:9 + adaptação mobile | P0 | Codex + designer de motion |
| V03 | `V03-demo-order-flow.tsx` | 10–15s equivalentes: S02→S03→S04→S05; estados coerentes com demo. | Componente responsivo | P0 | Codex + designer de motion |
| V04 | `V04-order-to-kitchen.tsx` | 5–8s equivalentes: pedido enviado → equipe e KDS; visual, não transmissão de dados real. | Componente responsivo | P0 | Codex + designer de motion |


### Social (5)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| O01 | `O01-og-default.png` | Imagem de compartilhamento com marca oficial, mensagem legível e composição fiel ao produto. | 1200×630 (1.91:1) | P0 | Codex/designer |
| O02 | `O02-og-nfc.png` | Imagem de compartilhamento com marca oficial, mensagem legível e composição fiel ao produto. | 1200×630 (1.91:1) | P0 | Codex/designer |
| O03 | `O03-og-features.png` | Imagem de compartilhamento com marca oficial, mensagem legível e composição fiel ao produto. | 1200×630 (1.91:1) | P0 | Codex/designer |
| O04 | `O04-og-pricing.png` | Imagem de compartilhamento com marca oficial, mensagem legível e composição fiel ao produto. | 1200×630 (1.91:1) | P0 | Codex/designer |
| O05 | `O05-og-demo.png` | Imagem de compartilhamento com marca oficial, mensagem legível e composição fiel ao produto. | 1200×630 (1.91:1) | P0 | Codex/designer |


### Demo cardápio (8)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| D01 | `D01-demo-burger.webp` | Hambúrguer artesanal em fundo/cozinha da mesma campanha; foto apetitoso porém realista; sem marca. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D02 | `D02-demo-fries.webp` | Porção de batatas fritas; iluminação e tratamento idênticos à imagem D01. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D03 | `D03-demo-soda.webp` | Copo de refrigerante genérico com gelo, sem logo de fabricante. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D04 | `D04-demo-water.webp` | Copo/garrafa de água sem marca, fundo neutro. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D05 | `D05-demo-brownie.webp` | Brownie de sobremesa, prato coerente com restaurante da demonstração. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D06 | `D06-demo-milkshake.webp` | Milk-shake fotografado de forma consistente com os demais produtos. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D07 | `D07-demo-chicken.webp` | Sanduíche de frango genérico, sem marca. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |
| D08 | `D08-demo-salad.webp` | Salada/alternativa vegetariana com fotografia consistente. | 1200×1200 (1:1) | P0 | Você com IA de imagens/fotógrafo |


### Camadas NFC (3)

| ID | Nome do arquivo | O que precisa mostrar/ser | Base recomendada | Prioridade | Responsável |
|---|---|---|---|---|---|
| M01 | `M01-table-clean-plate.png` | Fundo fotográfico do mesmo ambiente do hero, mesa visível e livre, para permitir animação em camadas. | 2400×1350 (16:9) | P0 | Você + artista de composição; Codex pode preparar recortes |
| M02 | `M02-hand-phone-alpha.png` | Mão realista segurando smartphone em PNG com transparência, posição correta para aproximar do NFC; visor substituível por S01. | 2000×2000 com alpha | P0 | Você + artista de composição; Codex pode preparar recortes |
| M03 | `M03-nfc-card-alpha.png` | Card retangular horizontal reproduzido fielmente em PNG transparente, compatível com a perspectiva do M01. | 1600×1000 com alpha | P0 | Você + artista de composição; Codex pode preparar recortes |


## 3. Detalhamento especial da animação NFC (HOME e COMO FUNCIONA)

**Composição de camadas:** `M01` (mesa limpa de fundo) + `M03` (card original colado, imóvel) + `M02` (mão/celular recortados e móveis) + `S01` (tela TapServe sobreposta no display) + halo NFC em SVG/CSS. Essa separação é essencial para animações controladas pela rolagem e por ponteiro.

**Storyboard com estados testáveis:**

1. **Cena A — ambiente:** mesa, card fixado e celular fora da área de leitura; o texto aparece.
2. **Cena B — aproximação:** smartphone se desloca e inclina suavemente; acompanha progresso de scroll, nunca bloqueia a rolagem.
3. **Cena C — contato visual:** halo âmbar suave indica que o fluxo NFC foi acionado (ilustração, não simulação do sistema operacional).
4. **Cena D — abertura:** tela do navegador com a interface `S01` do TapServe; transição para close do smartphone.
5. **Cena E — continuidade:** interação com o cardápio/mini-demo, sem disparar pedido real.

**Interações de mouse:** parallax em camadas, foco no produto, hover dos hotspots, luz/borda no card e botão magnético discreto. Não usar movimentação exagerada do cursor. Não exigir mouse para acessar conteúdos.

**Entregáveis de código** (não são arquivos de imagem extras): componente `NfcStory.tsx`, timeline responsiva, estado reduzido, fallback estático, `poster`/thumbnail e testes de uso por teclado/toque.

## 4. Demonstração interativa do pedido (`/demonstracao`)

Fotos: `D01–D08`. Telas de referência: `S01–S08`. Telas de operação para mostrar continuidade: `S09`, `S13`, `S14`.

**Não basta exibir uma sequência de screenshots**: a demonstração precisa ser clicável. Codex implementa HTML/React sem conexão produtiva; os assets são imagens de produtos e referência estética.

**Fluxo funcional mínimo:** abrir Mesa Demonstrativa → escolher categoria → abrir produto → escolher opcionais (regras coerentes) → alterar quantidade → adicionar ao carrinho → editar/remover → confirmar pedido simulado → acompanhar progresso demonstrativo → voltar/reiniciar → testar chamar garçom/solicitar conta simulados. Nunca exigir cadastro.

**Dados de exemplo sugeridos (revisáveis):**

| ID | Item de demonstração | Categoria | Foto | Nota |
|---|---|---|---|---|
| P01 | Hambúrguer artesanal | Hambúrgueres | D01 | Exibir opcionais (ex.: queijo extra, ponto da carne se existir no fluxo de opções) |
| P02 | Batata frita | Porções | D02 | Opcional de tamanho, se a UI suportar |
| P03 | Refrigerante | Bebidas | D03 | Sem marcas comerciais |
| P04 | Água | Bebidas | D04 | Sem marcas comerciais |
| P05 | Brownie | Sobremesas | D05 | Sobremesa |
| P06 | Milk-shake | Sobremesas/Bebidas | D06 | Variação de sabor se a UI suportar |
| P07 | Sanduíche de frango | Hambúrgueres/Sanduíches | D07 | Alternativa ao hambúrguer |
| P08 | Salada | Saladas | D08 | Opção vegetariana |

O Codex deve criar `demoCatalog.ts` ou `demoCatalog.json`, com nomes, preços **claramente ilustrativos**, categoria, descrição e regras de opcionais compatíveis com o componente. A demonstração deve mostrar **"Ambiente demonstrativo • nenhum pedido real será enviado"** de maneira clara. Não criar ações ou estados do produto que o TapServe verdadeiro não possui.

**Estados vazios e erro:** sem itens, carrinho vazio, opção obrigatória não selecionada, confirmação do pedido simulado, recomeçar demo. Tais telas são componentes em HTML/CSS; não exigem novas imagens raster.

## 5. Outros arquivos e informações que NÃO são imagens

| Insumo | Nome/onde colocar | Responsável |
|---|---|---|
| Design tokens/paleta | `src/styles/tokens.css` ou JSON | Codex, utilizando preto `#111111`, branco `#FFFFFF`, cinza `#F5F5F3`, âmbar `#E5A62B` (confirmar com arte oficial) |
| Fontes legais/licenciadas | Arquivos importados de fornecedor autorizado ou CSS import | Codex; usar Manrope/Inter após avaliação |
| Arte fonte do card | `assets/originais/card/` | Você; **arquivo de origem**, sem redimensionar/remover marca |
| Logo fonte original | `assets/originais/marca/` | Você |
| Mockups/screenshots originais | `assets/screenshots/` | Codex ou você com ambiente demo seguro |
| Catálogo de demonstração | `src/data/demoCatalog.ts` | Codex, aprovação do usuário |
| Estado da demo isolado | componentes React, sem backend real | Codex |
| Dados oficiais de contato | `src/config/contact.ts` | Codex, a partir de V2; apenas dois links com ícones, sem exibir dados nos blocos de contato |
| Preços/benefícios aprovados | `src/data/pricing.ts` | Você aprova / Codex implementa |
| Dados legais da empresa | Conteúdo de acesso controlado para redação | Você fornece, não inventar |
| Política de Privacidade / Termos / Cancelamento | Conteúdo jurídico aprovado | Redação validada por você e revisão jurídica antes da publicação |
| Metadados SEO e OG | tags / `public/` / sitemap | Codex |
| Textos do site (copy) | `src/content/` | Codex propõe e você aprova |
| Domínio, hospedagem e ambiente | Configuração de deploy | Você decide quando publicar |

## 6. Estrutura sugerida para disponibilizar ao Codex

```text
tapserve-site/
├── TAPSERVE_ARQUITETURA_SITE_V2_CONTATO_JURIDICO.md
├── TAPSERVE_PROMPT_MESTRE_CODEX_SITE_V2.md
├── TAPSERVE_ASSET_SHEET_V3.md
├── TAPSERVE_ASSET_MANIFEST_V3.json
├── assets/
│   ├── originais/
│   │   ├── marca/                 # logo oficial original, se possível SVG
│   │   └── card/                  # design gráfico FINAL do card real
│   ├── branding/                   # B01–B06
│   ├── fotografias/                # F01–F18
│   ├── screenshots/                # S01–S20
│   ├── composicoes/                # C01–C06 (se não forem em DOM)
│   ├── motion/                     # V01–V04 (ou componentes em src)
│   ├── social/                     # O01–O05
│   ├── demo-cardapio/              # D01–D08
│   └── motion-camadas/             # M01–M03
└── src/ ...
```

**Regra de entrega:** não criar arquivos vazios fingindo ser imagens prontas. Se um asset estiver pendente, usar placeholder claramente sinalizado **somente no ambiente de desenvolvimento**, registrar no checklist e bloquear a aprovação final daquela experiência até resolução. Não publicar mockup enganoso.

## 7. Ordem de produção (para economizar trabalho)

1. **Primeira leva — essenciais originais:** B01, arte original do card, S01–S08, S09, S13–S14, S16–S17.
2. **Segunda leva — cenário NFC:** F01–F04, F08–F11, M01–M03.
3. **Terceira leva — outras operações:** F06–F07, S10–S11 e D01–D08.
4. **Quarta leva — composições e animações pelo Codex:** C01–C06, V02–V04, B02/B04/B05/B06, O01–O05.
5. **Quinta leva — aperfeiçoamento:** F05, F12–F18, S12, S15, S18–S20 e V01.

É aceitável iniciar desenvolvimento antes de concluir essas levas, desde que o Codex não confunda placeholders com materiais finais.

## 8. Critérios de aceite dos materiais

- **Identidade:** mesma logo e paleta em todas as imagens, nenhum wordmark inventado.
- **Card:** horizontal, branco, colado diretamente na mesa; círculo NFC preto e arte final correta.
- **Telas:** exatamente o produto real, dados falsos de demo, sem vazamento de usuário/senha/token.
- **Demo:** funcionalidades acessíveis, fluxo do pedido concluível, dados isolados, botão reiniciar, indicação de simulação.
- **Motion:** desktop/mouse + mobile/toque + teclado + movimento reduzido; sem scroll sequestrado.
- **Performance:** imagens responsivas, poster dos vídeos, sem precisar baixar masters pesados.
- **Legal/comercial:** preços e conteúdo aprovados, sem formulários, botões de contato reais, páginas legais não inventadas.

## 9. Instrução curta para enviar ao Codex

> Leia integralmente `TAPSERVE_ARQUITETURA_SITE_V2_CONTATO_JURIDICO.md`, `TAPSERVE_PROMPT_MESTRE_CODEX_SITE_V2.md`, `TAPSERVE_ASSET_SHEET_V3.md` e `TAPSERVE_ASSET_MANIFEST_V3.json` antes de executar qualquer alteração. O manifesto é o inventário de arquivos; não presuma que arquivos listados já existem. Verifique a existência e registre pendências. Para a demo de pedidos, crie componentes clicáveis isolados, sem integrar ao backend. Para a animação NFC, usar camadas M01–M03, interface S01 e GSAP/CSS conforme adequado, com fallback. Não invente imagens finais, marcas, telas, funções, preços ou textos legais. Não publique o site sem aprovação.
