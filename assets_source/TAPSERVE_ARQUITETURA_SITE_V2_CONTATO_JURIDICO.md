# TapServe — Arquitetura do Site Institucional e Comercial
**Versão:** 2.0 — 12/11/2026
**Status:** especificação atualizada para implementação; documentos jurídicos sujeitos a validação das práticas reais e revisão profissional antes da publicação
**Tipo:** home institucional com narrativa de landing page + páginas comerciais especializadas
**Marca:** TapServe (não TAPself)
**Referências:** Goomer (clareza), me&u (atmosfera premium), OlaClick (produto em ação); linguagem própria.

**Alterações V2:** seção jurídica ampliada; suporte por WhatsApp/e-mail; site público sem formulários, sem backend de leads e sem rota de sucesso de envio.

## 0. Decisão central de produto e posicionamento
- Promessa de alto nível: **"Seu atendimento começa com um toque. Sua operação ganha outra dinâmica."** (copy de trabalho).
- Categoria: plataforma para atendimento e operação de estabelecimentos com consumo presencial.
- Fio visual condutor: **card físico na mesa → NFC/QR Code → cliente → pedido → equipe/cozinha → gestão**.
- Público que decide: proprietários, gerentes e administradores de restaurantes, lanchonetes, bares, hamburguerias e cafeterias.
- Conversão principal: **Solicitar demonstração comercial por WhatsApp ou e-mail**, com link direto para o aplicativo escolhido. Conversões secundárias: **Explorar demonstração interativa**, **Ver planos**, **Falar com o suporte**. **Não haverá formulários de contato, cadastro de leads nem formulário de suporte nesta versão.**
- Não criar promessa de recursos não confirmados: pagamento online nativo, conciliação bancária, emissor fiscal, gestão de delivery, IA, integrações com PDVs específicos ou métricas de aumento de faturamento. O TapServe pode registrar pagamento externo e solicitar conta, mas isto **não é checkout online integrado**.
- Fotos, depoimentos e números comerciais só podem ser publicados com autorização e comprovação.

## 1. Identidade, layout e fotografia

### Paleta
- paleta do sistema ja utilizada

### Linguagem
- Tipografia sem serifa com excelente legibilidade: testar **Manrope** ou **Inter** para interface; títulos com peso e personalidade. Definir fontes finais apenas após teste com o logotipo.
- Grid desktop de até 1200–1320 px; bastante espaço em branco; títulos grandes e copy curta.
- Fotografia editorial realista, iluminação quente, alto nível de detalhe nos materiais, sem parecer banco de imagens genérico.
- Não misturar dispositivos/renderizações de estilos diferentes. Todos os mockups devem ter o mesmo tratamento, escalas e iluminação.
- Fotografias podem ser produzidas com fotógrafo ou IA, mas **o card TapServe e as telas devem ser inseridos fielmente a partir dos originais**, sem logos inventados e sem falsas funcionalidades.

### Card físico — regra visual obrigatória
- **Retângulo horizontal largo, branco, fixado/colado sobre a mesa**, não em suporte vertical.
- Logotipo original com wordmark preto, proporcionalmente grande.
- Área de aproximação: círculo preto abrangendo a área NFC e a indicação "Aproxime aqui", seguindo a arte original aprovada.
- QR Code na versão física correspondente, se o modelo da cena incluir QR.
- Usar arte original fornecida pelo usuário como base, não redesenhar "aproximadamente".

## 2. Navegação pública (sitemap)

```text

/
├── /como-funciona
├── /funcionalidades
├── /nfc-e-qr-code
├── /para-quem
├── /planos
├── /demonstracao
├── /contato
├── /suporte
├── /duvidas
├── /sobre
├── /privacidade
├── /termos
├── /cancelamento
├── /cookies              (somente se aplicável, após inventário)
├── /termos-assinatura     (apenas quando conteúdo contratual for aprovado)
└── /404                  (estado para rotas inexistentes)

```

**Sem rota `/obrigado`:** não existe envio de formulário. Não criar página de sucesso ou afirmar que um contato foi enviado. Abertura de WhatsApp/e-mail **não confirma envio ou recebimento**.

**Menu desktop:** logotipo | Como funciona | Funcionalidades (menu com categorias) | NFC + QR | Planos | [Ver demonstração] | [Solicitar demonstração].

**Menu mobile:** logo | botão menu | CTA visível para demonstração ou menu fixo reduzido; painel deslizante com links e CTA.

**Rodapé:** visão geral, produto, empresa, central de suporte, contato, privacidade, termos, cancelamento, cookies quando aplicável, redes verificadas e copyright dinâmico. Identificação do fornecedor e informações exigidas legalmente devem estar acessíveis na forma apropriada, sem criar dados fictícios.

**Login do sistema:** link externo/rota de produto claramente identificada, somente se disponível; não confundir a home com aplicação operacional.

### Canais oficiais — regra obrigatória para todo o site

- **WhatsApp (link técnico):** `https://wa.me/5517997585762`
- **E-mail (link técnico):** `mailto:pedrocarrega5@gmail.com`
- **Textos visíveis nos botões:** **Enviar mensagem** (`MessageCircle` / ícone WhatsApp adequado) e **Enviar e-mail** (`Mail` / ícone de envelope).
- **Não exibir o número de telefone nem o endereço de e-mail em texto visível nas páginas de contato e suporte.** Mostrar somente os dois botões com ícones e seus rótulos. Os identificadores devem existir apenas nos destinos dos links/configuração e, quando uma obrigação legal exigir informações de identificação/contato em documentos jurídicos, aplicar a exigência após revisão profissional.
- WhatsApp abre a conversa oficial; `mailto:` abre o aplicativo de e-mail padrão do visitante. Usar links sem bibliotecas externas, sem API paga, sem servidor de envio. Não mostrar toast de “mensagem enviada”.
- Mensagem pré-preenchida no WhatsApp é opcional e **contextual**: comercial (“Olá, gostaria de conhecer o TapServe.”) ou suporte (“Olá, preciso de ajuda com o TapServe.”). Codificar parâmetros corretamente (`encodeURIComponent`). Não adicionar dados pessoais automaticamente ao texto.
- Botões devem possuir ícones acessíveis, nomes acessíveis, foco visível, contraste adequado, funcionamento em toque/teclado e indicação de abertura em aplicativo externo quando útil.
- Links de CTA como “Solicitar demonstração” podem levar a `/contato` ou diretamente ao WhatsApp comercial; nunca abrir um formulário.
- Configurar canais em **um único arquivo centralizado** (`src/config/contact.ts`, por exemplo), consumido por Header, Footer, Contato, Suporte, Planos, FAQ e CTAs. Não duplicar telefone/e-mail em vários componentes.

### O que lançar primeiro

- **P0, lançamento principal:** `/`, `/como-funciona`, `/funcionalidades`, `/nfc-e-qr-code`, `/planos`, `/demonstracao`, `/contato`, `/suporte`, `/privacidade`, `/termos`, `/cancelamento` e estado `404`. As páginas legais só podem ser publicadas com conteúdo real aprovado.
- **P1, após material comercial pronto:** `/para-quem`, `/duvidas`, `/sobre` (a Home e Planos já contêm FAQ suficiente no início); `/cookies` se o inventário justificar uma página específica; `/termos-assinatura` antes de oferecer contratação sob esses termos.
- **P2, só com conteúdo real recorrente:** estudos de caso, blog, materiais, ajuda técnica/artigos e páginas individuais por segmento. Não criar páginas vazias nem SEO artificial.

## 3. HOME (`/`) — roteiro de 13 seções

| # | Seção | Objetivo e conteúdo | Materiais | Motion / interação | CTA |
|---|---|---|---|---|---|
| H00 | Header flutuante | Logo, links e CTA principal; fundo acompanha contraste | B01–B04 | Entrada sutil; transição ao rolar; menu mobile acessível | Solicitar demo |
| H01 | Hero cinematográfico | Título: "Seu atendimento começa com um toque." Subtítulo: NFC/QR, pedidos e operação conectados | C01, F01–F03, S01, V01 opcional | Entrada por camadas; movimento leve, poster estático e replay | Ver como funciona / Solicitar demo |
| H02 | Faixa de valor | "Aproxime. Peça. Acompanhe. Organize." + quatro vantagens curtas | B05–B06, ícones SVG | Stagger discreto | Explorar |
| H03 | Storytelling de mesa | Cena real → aproximação NFC → abertura do cliente | F02–F04, S01–S03, C02, V02 | Scroll-linked com estados, sem travar rolagem | Testar |
| H04 | Pedido em ação | Navegar cardápio, opcionais, carrinho e confirmação | S02–S06, C03, V03 | Smartphone sticky com transições de interface | Ver demo |
| H05 | Da mesa à operação | Pedido chega ao staff/KDS; atendimento e chamados | S09–S15, F06–F07, C04, V04 | Transição cliente→cozinha, estados de pedidos | Funcionalidades |
| H06 | Dentro do TapServe | Explorador com abas Cliente / Equipe / Cozinha / Administração | S01–S20, C06 | Troca de telas controlada pelo visitante; hotspots | Explorar todos os recursos |
| H07 | Produto físico | Destaque de card original colado na mesa; NFC e QR | F08–F12, C05 | Close e troca de ângulo; sem 3D desnecessário | Conhecer NFC + QR |
| H08 | Benefícios em bento | Atendimento, organização, autonomia, controle | F05–F08, recortes UI | Bento assimétrico; hover moderado | Como funciona |
| H09 | Onde funciona | Restaurantes, bares, lanchonetes, hamburguerias, cafeterias | F13–F17 | Galeria editorial; rolagem suave | Ver aplicações |
| H10 | Prévia dos planos | Essencial vs Pro, limites claros, adicionais e setup | Sem fotos; UI tipográfica | Alternância de plano só se existir periodicidade real; não inventar desconto | Ver planos |
| H11 | Dúvidas essenciais | 5–6 perguntas: app, NFC, QR, implantação, unidades, suporte | Ícones SVG, sem fotos | Accordion acessível | Outras dúvidas |
| H12 | Final comercial + footer | "Seu próximo atendimento pode começar aqui." | F18 / C01 variação, B02 | Fecho elegante, transição do fundo | Solicitar demonstração / WhatsApp |

**Regra de narrativa:** o visitante que rolar apenas a Home deve compreender o valor do TapServe sem depender das páginas internas. As páginas internas aprofundam, não duplicam literalmente os mesmos blocos.

## 4. Páginas internas — roteiro completo

### P01 — Como funciona (`/como-funciona`)
1. Hero claro com celular e card em contexto (`F03`, `S01`), título "Da aproximação ao atendimento, sem complicação".
2. Passos 1–4: aproximar/escanear, abrir cardápio, fazer pedido, acompanhar.
3. Timeline visual real com frames das telas (`S01`–`S08`); opção de reproduzir o fluxo, sem entrar numa sessão operacional real.
4. Passos da equipe: chamado ou pedido → staff → KDS → conclusão (`S09`–`S15`).
5. Como começa a implantação: cadastro, configuração, preparação/ativação dos cards e treinamento, apenas conforme processo de venda real.
6. FAQ contextual e CTA para teste ou reunião.

### P02 — Funcionalidades (`/funcionalidades`)
1. Hero com montagem de dispositivos (`C06`).
2. Navegação interna por áreas: **Cliente**, **Mesas & atendimento**, **Pedidos**, **Cozinha/KDS**, **Gestão**, **Unidades**, **Relatórios**.
3. Cliente: cardápio, escolha de opcionais, carrinho, acompanhamento, pedir garçom e solicitar conta (`S01`–`S08`).
4. Equipe: visualização de mesas, pedidos, chamados e acompanhamento de atendimento (`S09`–`S12`).
5. Cozinha: fila de produção e estados de pedido (`S13`–`S15`).
6. Gestão: cardápio, equipe, unidades e ferramentas de administração (`S16`–`S19`); mostrar relatórios somente se a tela real suportar a descrição.
7. Segurança e controle de acesso: apenas claims verificados, sem divulgar detalhes internos sensíveis.
8. Integração narrativa, tabela-resumo e CTA para demonstração.

### P03 — NFC e QR Code (`/nfc-e-qr-code`)
1. Hero fotográfico focado no card real (`F08`, `F09`).
2. Fotogaleria do produto: vista superior, ângulo 45°, macro e card aplicado em mesa (`F08`–`F12`).
3. Comparativo simples de ação: **NFC — aproxime o celular** e **QR — aponte a câmera**; explicar compatibilidade sem prometer NFC universal.
4. O que o cliente vê ao abrir o link (`S01`, `S02`).
5. Como cards são configurados e ativados, conforme fluxo validado do sistema.
6. Modelos físicos disponíveis e valores de card apenas com orçamento/precificação confirmados.
7. FAQ sobre resistência, instalação, NFC, QR e substituição. CTA.

### P04 — Para quem é (`/para-quem`) [P1]
1. Hero com galeria editorial (`F13`–`F17`).
2. Cinco categorias: restaurantes, hamburguerias, lanchonetes, bares e cafeterias; cada uma com situação de uso realista, sem inventar automações.
3. Um exemplo de jornada por segmento (somente contexto, sem inventar funcionalidades novas).
4. Gestão multiunidade quando aplicável (`S18`).
5. CTA contextual "Ver como funcionaria no meu estabelecimento".

### P05 — Planos (`/planos`)
1. Hero direto, predominantemente claro: "Um plano para o tamanho da sua operação".
2. **Essencial:** referência de decisão anterior R$ 159,90/mês; até 5 unidades e 50 mesas no total.
3. **Pro:** referência de decisão anterior R$ 229,90/mês; até 10 unidades e 80 mesas no total.
4. **Adicional:** +20 mesas por R$ 59,90/mês, conforme definição anterior.
5. Diferenciais exatos dos planos: **preencher somente após matriz funcional aprovada**; não inventar limite de pedidos, usuários ou recursos exclusivos.
6. Taxa de configuração e custo por card apresentados separadamente, após confirmação final do valor.
7. Exemplo interativo de escolha do plano por unidades/mesas; os cálculos devem considerar os limites compartilhados de mesas.
8. Comparativo, FAQ de cobrança, CTA para orçamento/demonstração.
9. Nada de riscar preço original ou inventar avaliações e promoções.

### P06 — Demonstração (`/demonstracao`)
1. Hero com CTA "Experimente a jornada" (`C03`, `S01`).
2. **Demo guiada isolada/simulada:** cliente acessa a mesa → menu → item → opcionais → adicionar → enviar pedido → status → pedir atendimento/conta.
3. Alternar para visão da equipe e da cozinha, com dados fictícios identificados como demonstrativos (`S09`–`S15`).
4. Controles: Reiniciar, Avançar etapa, Voltar, Alternar visão, Desativar animações; navegação por teclado e toque.
5. Se demo funcional não estiver pronta, usar vídeo/capturas reais em etapa P0 e deixar a simulação interativa para P1; nunca expor o ambiente QA/admin a visitantes.
6. CTA "Quero ver o TapServe no meu estabelecimento".

### P07 — Contato (`/contato`)

1. Hero curto: “Vamos conversar sobre o seu estabelecimento?”; apresentar que os canais disponíveis no momento são WhatsApp e e-mail.
2. **Exatamente dois botões de contato, com ícones:** **Enviar mensagem** (ícone WhatsApp, destino oficial `wa.me`) e **Enviar e-mail** (ícone de envelope, destino `mailto:`). Nunca exibir o número ou e-mail em texto nessa área.
3. Usar os links centralizados da seção 2, com mensagem contextual opcional apenas no WhatsApp. Os botões são ações reais; nada de controles decorativos ou simulados.
4. Explicar que o visitante será direcionado ao aplicativo escolhido e que uma conversa pode ser iniciada por lá; não prometer horários, atendimento imediato nem resposta em prazo não confirmado.
5. **Não implementar formulário, campos de dados, captchas, upload, lista de leads, endpoint de contato, mensagens de envio confirmado nem redirecionamento para `/obrigado`.**
6. Manter acesso fácil a `/suporte`, `/privacidade` e `/termos`.

### P07B — Central de suporte (`/suporte`) [P0]

1. Hero objetivo: “Precisa de ajuda com o TapServe?”; página pensada para dúvidas, orientações e solicitações sobre o serviço.
2. **Exatamente dois botões principais, com ícones:** **Enviar mensagem** (WhatsApp) e **Enviar e-mail** (`mailto:`). Não mostrar número/e-mail em texto nem criar formulário.
3. Reaproveitar os destinos centralizados da seção 2; suporte pode abrir WhatsApp com texto inicial “Olá, preciso de ajuda com o TapServe.”, sem enviar automaticamente.
4. Incluir orientações concisas de onde encontrar FAQ e políticas, sem inventar horários de atendimento, SLA, suporte 24/7, tickets ou chat embutido.
5. No futuro, uma base de ajuda pode complementar a página; **não criar sistema de chamados, campos, contas de suporte ou upload** nesta versão.
6. Links visíveis para Privacidade, Termos e Cancelamento; dúvidas envolvendo dados pessoais devem ter encaminhamento interno adequado, conforme a seção 13.

### P08 — Dúvidas (`/duvidas`) [P1]
- Grupos: Como funciona / NFC e QR / Implantação / Planos e cobrança / Operação / Suporte.
- Busca simples por pergunta (filtro local), deep links e CTAs contextuais.
- Respostas aprovadas por produto/comercial antes de publicar.

### P09 — Sobre (`/sobre`) [P1]
- Por que o TapServe existe, a proposta da marca, missão e como o produto foi pensado.
- Fotos originais ou retratos verdadeiros, caso autorizados; **nunca equipe fictícia ou marcos inventados**.
- Diferenciação do produto e CTA para `/contato` com os dois botões de WhatsApp/e-mail; sem formulário.

### P10 — Política de Privacidade (`/privacidade`) [P0]

- Página jurídica pública e acessível no rodapé; texto elaborado **somente** após inventário real de dados e fluxos. Abranger site comercial e, conforme o arranjo jurídico confirmado, distinguir tratamento de dados no SaaS operacional.
- Seguir as instruções, pontos de verificação e requisitos de aprovação da **seção 13**. Prever versão/data, responsável, finalidades, fundamentos legais, direitos, contatos, terceiros, transferências e retenção quando aplicáveis.
- **Não afirmar que o site coleta dados por formulário:** nesta versão não existe formulário. Ainda assim, investigar logs técnicos, cookies, analytics, WhatsApp/e-mail e serviços terceiros.

### P11 — Termos de Uso do Site (`/termos`) [P0]

- Regras para acesso e uso do **site público**, propriedade intelectual, limitações apropriadas, links externos, informações comerciais e canal de contato.
- Não confundir com o contrato de assinatura do serviço operacional. Não inserir cláusulas abusivas nem prometer direitos/obrigações inventados. Seguir seção 13.

### P11B — Cancelamento e reembolso (`/cancelamento`) [P0]

- Explicar como solicitar cancelamento pelos canais atuais (WhatsApp e e-mail), com **dois botões com ícones**, sem mostrar os identificadores em texto na área de contato.
- Informar regras concretas de renovação, encerramento, eventuais taxas, devolução de cards físicos e reembolsos **apenas quando aprovadas**; observar CDC e normas aplicáveis a cada relação de contratação, sem afirmar automaticamente que toda contratação B2B é relação de consumo.
- Não inventar prazo, multa, restituição ou política de arrependimento. Requisitos e validação na seção 13.

### P11C — Cookies (`/cookies`) [condicional]

- Criar **somente após inventariar cookies e rastreadores**, suas finalidades, fornecedores, duração e bases legais. Se o site não usar rastreadores não essenciais, não criar banner invasivo por padrão.
- Se houver tratamento que exija consentimento, implementar escolhas válidas e controles proporcionais, conforme orientações da ANPD. Ver seção 13.

### P11D — Termos de assinatura do SaaS (`/termos-assinatura`) [condicional]

- Publicar ou fornecer antes da contratação **se o canal de venda e o modelo jurídico exigirem**; sua eventual URL pública depende da estratégia contratual aprovada. Documento distinto dos termos do site, com condições comerciais, suporte, responsabilidades, dados, saída e cancelamento.
- Não criar conteúdo definitivo sem confirmar fornecedor, planos e prestação real. Seguir seção 13.

### P12 — Página “Obrigado” (`/obrigado`) [retirada desta versão]

- **Não criar rota, interface nem mockup.** Não há formulário nem processamento de envios no site.
- O clique em WhatsApp/e-mail abre um canal externo; não comprova que uma mensagem foi enviada, entregue ou recebida.

### P13 — 404

- Headline simples “Esta mesa não foi encontrada” (tom leve), botão para Home e links principais. Sem animação pesada.

## 5. Inventário fechado de produção visual (59 entregáveis planejados)
**Legenda:** P0 = essencial; P1 = aperfeiçoamento após base; foto = fotografia/rénder fotorrealista fiel; captura = screenshot real; composição = peças de fotos/capturas; vídeo = microfilme/recorte animado. As resoluções são **mestres de produção**, não tamanhos finais de download.

### 5.1 Identidade — 6 arquivos

| ID | Nome sugerido | Especificação | Uso | Pri. |
|---|---|---|---|---|
| B01 | `logo-wordmark-black.svg` | Logo original preta sem fundo | Header claro, rodapé claro | P0 |
| B02 | `logo-wordmark-white.svg` | Variante aprovada sobre preto | Hero/rodapé escuro | P0 |
| B03 | `logo-mark.svg` | Símbolo isolado aprovado | Marca, loader, mockups | P0 |
| B04 | `favicon.svg` | Ícone adaptado a tamanho pequeno | Navegador | P0 |
| B05 | `icon-nfc.svg` | Ícone NFC vetorial coerente com marca | Steps, FAQ | P0 |
| B06 | `icon-qr.svg` | Ícone QR vetorial, não um QR funcional falso | Steps, FAQ | P0 |

### 5.2 Fotografia e produto físico — 18 originais

| ID | Nome de produção | Enquadramento e conteúdo | Uso | Pri. |
|---|---|---|---|---|
| F01 | `hero-restaurant-wide` | 2400×1350 (16:9), restaurante sofisticado realista, mesa em primeiro plano, área de respiro para o texto | Home hero | P0 |
| F02 | `card-fixed-on-table` | 1600×1200 (4:3), cartão **colado** à mesa, logo original, vista 3/4 | Home, NFC | P0 |
| F03 | `phone-near-card` | 1600×1200, mão segurando smartphone sobre o NFC, sem enganar sobre posição de leitura | Home, Como funciona | P0 |
| F04 | `customer-using-menu` | 1600×1200, cliente em ambiente real navegando no celular | Home, Como funciona | P0 |
| F05 | `food-and-phone` | 1600×1200, alimento real bem fotografado, celular em cena secundária | Benefícios | P1 |
| F06 | `staff-on-floor` | 1600×1200, equipe em salão com dispositivo, contexto operacional plausível | Home, Funcionalidades | P0 |
| F07 | `kitchen-kds-real` | 1600×1200, cozinha com monitor exibindo **tela real do KDS** | Home, Funcionalidades | P0 |
| F08 | `card-product-45deg` | 1800×1350, card físico isolado em mesa, ângulo 45°, material fiel | Home, NFC | P0 |
| F09 | `card-topdown` | 1800×1350, card visto de cima, legibilidade perfeita | NFC | P0 |
| F10 | `card-macro-nfc` | 1800×1350, detalhe da área preta "Aproxime aqui" | NFC | P0 |
| F11 | `card-qr-closeup` | 1800×1350, modelo com QR legível em contexto, QR demonstrativo explicitado se não real | NFC | P0 |
| F12 | `card-lifestyle-table` | 1800×1350, mesa montada, card fixado, ambiente comercial real | NFC, Home | P1 |
| F13 | `venue-restaurant` | 1600×1200, salão restaurante | Para quem | P1 |
| F14 | `venue-hamburger` | 1600×1200, hamburgueria | Para quem | P1 |
| F15 | `venue-snack` | 1600×1200, lanchonete | Para quem | P1 |
| F16 | `venue-bar` | 1600×1200, bar | Para quem | P1 |
| F17 | `venue-cafe` | 1600×1200, cafeteria | Para quem | P1 |
| F18 | `final-cta-restaurant` | 2400×1100, foto ambiente premium sem informação excessiva, composição distinta do hero | Home fecho | P1 |

**Observação:** F01–F12 podem render várias variações e recortes. Não precisam ser 12 sessões fotográficas; idealmente vêm de **uma direção de arte consistente e poucas sessões**. Não usar fotos de concorrentes comercialmente sem licença.

### 5.3 Capturas reais de interface — 20 telas

| ID | Tela exata a capturar | Formato | Uso | Pri. |
|---|---|---|---|---|
| S01 | Abertura da mesa do cliente | Mobile 390×844 ou resolução real equivalente | Hero, demo | P0 |
| S02 | Cardápio, categorias e produtos | Mobile | Jornada | P0 |
| S03 | Detalhe do item e opcionais | Mobile | Jornada | P0 |
| S04 | Carrinho antes do pedido | Mobile | Jornada | P0 |
| S05 | Pedido confirmado | Mobile | Jornada | P0 |
| S06 | Status/acompanhamento de pedido | Mobile | Jornada | P0 |
| S07 | Chamar garçom | Mobile | Funcionalidades | P0 |
| S08 | Solicitar conta | Mobile | Funcionalidades | P0 |
| S09 | Visão das mesas pela equipe | Mobile ou tablet real | Operação | P0 |
| S10 | Lista de pedidos da equipe | Mobile/tablet | Operação | P0 |
| S11 | Chamados/atendimentos | Mobile/tablet | Operação | P0 |
| S12 | Detalhe de pedido/mesa | Mobile/tablet | Operação | P1 |
| S13 | KDS: novos pedidos | Desktop/tablet 1440×900+ | Cozinha | P0 |
| S14 | KDS: em preparo | Desktop/tablet | Cozinha | P0 |
| S15 | KDS: pronto/entrega | Desktop/tablet | Cozinha | P1 |
| S16 | Painel principal da administração | Desktop | Funcionalidades | P0 |
| S17 | Gerenciamento de cardápio | Desktop | Funcionalidades | P0 |
| S18 | Gestão de unidades/equipe | Desktop | Funcionalidades | P1 |
| S19 | Relatórios (se existentes e validados) | Desktop | Funcionalidades | P1 |
| S20 | Estado da mesa/conta no painel | Desktop/tablet | Funcionalidades | P1 |

**Fonte:** captura do TapServe em ambiente demonstrativo autorizado, com dados fictícios plausíveis, sem informação pessoal verdadeira. Capturas devem representar a versão que será vendida, ou identificar claramente o estado de demonstração. Não retocar funcionalidades inexistentes.

### 5.4 Composições publicitárias — 6 arquivos

| ID | Composição | Entradas | Uso | Pri. |
|---|---|---|---|---|
| C01 | Hero produto + card + celular | F01–F03, B01/B02, S01 | Home | P0 |
| C02 | Do card ao celular | F02/F03 + S01–S03 | Home storytelling | P0 |
| C03 | Sequência do pedido no smartphone | S02–S06 em moldura consistente | Como funciona / demo | P0 |
| C04 | Pedido conectado à cozinha | S05/S09/S13 e F07 | Home / Funcionalidades | P0 |
| C05 | Galeria consistente do card físico | F08–F11 e B01/B05 | NFC | P0 |
| C06 | Ecossistema: cliente/staff/KDS/admin | S01/S09/S13/S16 | Home / Funcionalidades | P0 |

### 5.5 Animações/vídeos — 4 entregáveis (poster + vídeo comprimido)

| ID | Motion | Conteúdo e duração sugerida | Implementação | Pri. |
|---|---|---|---|---|
| V01 | `hero-loop` | 6–8 s: ambiente com movimento discreto e foco no card; **sem texto embutido** | WebM/MP4 + poster estático; vídeo opcional | P1 |
| V02 | `nfc-tap` | 4–6 s: aproximação, retorno visual do acesso no celular | Vídeo ou camadas CSS/JS | P0 |
| V03 | `ordering-flow` | 10–15 s: cardápio → opcionais → carrinho → pedido | Melhor como animação de screenshots e interação, não vídeo obrigatório | P0 |
| V04 | `order-to-kitchen` | 5–8 s: confirmação do cliente → chegada ao KDS | Camadas de interfaces e motion | P0 |

### 5.6 Compartilhamento social — 5 arquivos

| ID | Arquivo | Uso | Pri. |
|---|---|---|---|
| O01 | `og-default` | Home, contato, sobre | P0 |
| O02 | `og-nfc` | NFC e QR | P0 |
| O03 | `og-features` | Funcionalidades | P0 |
| O04 | `og-pricing` | Planos | P0 |
| O05 | `og-demo` | Demonstração | P0 |

**Total de tipos/entregáveis mapeados:** 6 + 18 + 20 + 6 + 4 + 5 = **59**. Isso não significa 59 fotos diferentes: há marcas vetoriais, capturas, composições e versões sociais. O design pode reaproveitar os mesmos originais com recortes seguros para mobile.

## 6. Matriz de imagem por página

| Página | Imagens principais | Imagens complementares |
|---|---|---|
| Home | C01, C02, C03, C04, C05, C06, F01–F04, F06–F08 | F05, F12–F18, S01–S20 |
| Como funciona | F03, F04, C02, C03, S01–S08 | F06/F07, S09–S15 |
| Funcionalidades | C06, S01–S11, S13, S14, S16, S17 | S12, S15, S18–S20 |
| NFC/QR | F02, F08–F11, C05 | F12, S01–S02 |
| Para quem | F13–F17 | S18 |
| Planos | O04 para compartilhamento; interface tipográfica, sem fotografia obrigatória | Pequena miniatura C06 opcional |
| Demonstração | C03, S01–S15, O05 | V03, V04 |
| Contato | O01; ícones WhatsApp/e-mail e layout, sem foto de banco desnecessária | F18 opcional |
| Suporte | Ícones WhatsApp/e-mail e design tipográfico; sem foto ou formulário | Links legais e FAQ |
| Cancelamento | Tipografia clara e dois botões de contato com ícones | Sem fotografia obrigatória |
| Cookies / Termos de assinatura (se criados) | Marca B01/B02; apresentação documental | Nenhuma |
| Dúvidas | O01; ícones vetoriais | F10 e S01 como apoio se necessário |
| Sobre | B01/B02; foto original de marca/equipe se existente | F01 ou F18 apenas como atmosfera |
| Privacidade/Termos | B01/B02; sem fotos | Nenhuma |
| 404 | B03, ícones simples; sem foto | Nenhuma |

## 7. Regras de animação e interação

### Cinco momentos especiais
1. **Abertura:** título e produto entram sem impedir leitura; hero funciona em imagem estática se vídeo falhar.
2. **Aproximação:** zoom leve guiado pela rolagem do card para o smartphone.
3. **Pedido:** celular sticky com etapas que avançam durante a rolagem, com controles manuais acessíveis.
4. **Conexão:** pedido saindo do celular e chegando à cozinha, depois painel da equipe/admin.
5. **Galeria do card:** troca de ângulos do produto e detalhe NFC/QR, com fonte visual fiel.

### Efeitos rotineiros
- Menus: 180–250 ms, foco visível, sem hover obrigatório no mobile.
- Entrada de conteúdo: 250–550 ms, principalmente opacidade/translação curta.
- Seções scroll-linked: devem acompanhar a rolagem; nunca sequestrar a roda do mouse nem bloquear o conteúdo.
- Hotspots/tabs: troca de interface em 150–350 ms; estado inicial inteligível sem JS.
- Accordion: abrir/fechar suavemente, teclado e leitor de tela funcionando.
- Respeitar `prefers-reduced-motion`, permitir pausar motion automático e não comprometer layout sem animações. Ver WCAG 2.2: https://www.w3.org/Translations/WCAG22-pt-BR/ e técnica https://www.w3.org/WAI/WCAG22/Techniques/css/C39.html.

## 8. Comportamento responsivo

### Desktop (≥ 1024 px)
- Hero com texto à esquerda e fotografia/card/celular à direita ou fullscreen com overlay legível.
- Narrativa com sticky pin limitado a uma seção por vez; alternar com áreas estáticas para descanso visual.
- Galeria com quatro interfaces em bento; nav horizontal.

### Tablet (768–1023 px)
- Hero em 2 blocos; reduzir parallax e densidade das montagens.
- Duas colunas em features/planos; tabs roláveis horizontalmente com controles.

### Mobile (320–767 px)
- Hero vertical: título legível, CTA acima da imagem e card sem corte.
- Não exibir modelos de desktop minúsculos; aplicar zoom, recortes ou carrossel para KDS/admin.
- Scroll narrativo vira etapas/telas acionáveis, sem sticky longo que monopolize o viewport.
- Imagens verticais derivadas dos mesmos originais; menu de fácil toque e CTA comercial acessível.
- Cuidar de desempenho em conexões móveis; vídeo não é pré-requisito para compreender a Home.

## 9. Arquitetura técnica sugerida

```text

src/
├── app/                # roteamento e shell do site
├── components/
│   ├── navigation/     # header, menu mobile, footer
│   ├── ui/             # buttons, typography, accordions, tabs
│   ├── motion/         # animações reutilizáveis, reduced motion
│   ├── product/        # mockup phone, showcase, stepper, screens
│   └── conversion/     # links WhatsApp/e-mail, CTAs, pricing cards
├── pages/
│   ├── Home/
│   ├── HowItWorks/
│   ├── Features/
│   ├── NfcQr/
│   ├── Industries/
│   ├── Pricing/
│   ├── Demo/
│   ├── Contact/
│   ├── Faq/
│   ├── About/
│   ├── Support/
│   ├── Cancellation/
│   └── Legal/
├── config/             # links de contato centralizados (WhatsApp/e-mail)
├── content/            # copy e dados estruturados aprovados
├── styles/             # tokens, grid, cores, fontes
├── assets/             # gerenciados por ID B/F/S/C/V/O
└── lib/                # SEO, analytics opcional e utilidades de links

```

- **Front-end:** React + TypeScript; Vite para SPA ou framework com geração estática/SSR (ex. Next.js/Astro) a decidir conforme SEO, hosting e experiência do time. Preferência técnica: renderização estática/SSR das páginas comerciais, principalmente SEO.
- **Motion:** CSS + Motion para microinterações; GSAP ScrollTrigger apenas nos capítulos de rolagem onde agrega valor. Evitar incluir dois motores para a mesma tarefa.
- **Imagens:** masters de alta resolução; servir tamanhos responsive em AVIF/WebP + fallback; especificar `width/height`, `srcset`, `sizes`, lazy load abaixo da dobra; hero prioritário.
- **Vídeo:** poster imediatamente visível, carregamento sob demanda quando possível; não carregar vídeos de todas as seções juntos.
- **SEO:** títulos/meta e canonical individuais, sitemap.xml, robots.txt, Open Graph, estrutura semântica, schema somente quando aplicável e verificável.
- **Acessibilidade:** foco visível, alt text útil, labels, contraste, teclado, reduced motion, botões e links semanticamente corretos.
- **Performance:** monitorar Core Web Vitals e peso da Home; a narrativa não pode sacrificar usabilidade.
- **Contato e suporte:** nesta versão, apenas `<a href>` real para WhatsApp (`https://wa.me/5517997585762`) e e-mail (`mailto:pedrocarrega5@gmail.com`) com ícones e os rótulos **Enviar mensagem** e **Enviar e-mail**. Não criar API de leads, formulário, envio automático, confirmação falsa ou `/obrigado`. Reutilizar `src/config/contact.ts` e evitar exibir identificadores em texto nas seções visuais de contato/suporte.
- **Analytics (opcional):** se aprovado após inventário de privacidade, medir visitas, cliques em CTAs, abertura dos links de WhatsApp/e-mail, início/fim de demo e seleção de planos. **Não existe dado sobre mensagem enviada/recebida no aplicativo externo**, nem eventos de formulário. Exigir base legal/consentimento válido quando aplicável; não usar rastreadores antes da decisão de cookies da seção 13.
- **Segurança:** não reutilizar dados/clientes/credenciais do sistema real para demo pública. Demonstrador isolado, seed público, sem ações sobre ambientes produtivos.

## 10. Conteúdo e limites do que podemos afirmar
**Pode ser demonstrado, depois de validar funcionamento real:** NFC/QR, navegação de cardápio, pedidos, chamados, solicitação de conta, atendimento staff, KDS, gerenciamento de unidades, configurações e relatórios efetivamente existentes.
**Não afirmar como existente sem evidência:** pagamentos dentro do site, splits automáticos, integradores fiscais/PDV, programas de pontos no lançamento, delivery, melhorias quantitativas de faturamento, casos de clientes reais ou tempo de implantação garantido.
**Preços de trabalho a confirmar antes de publicar:** Essencial R$159,90/mês (5 unidades, 50 mesas); Pro R$229,90/mês (10 unidades, 80 mesas); adicional de 20 mesas por R$59,90/mês; taxa de setup e hardware separadas. A matriz de benefícios por plano ainda precisa ser validada.

## 11. Entregas em ordem de execução

### Fase A — Base verdadeira
- [ ] Logo oficial em vetor, arte do card final, fontes e identidade aprovadas.
- [ ] Verificar e documentar todas as features efetivamente prontas (sem conflitar com o projeto TapServe).
- [ ] Capturar as telas S01–S20 possíveis, registrar as que ainda não existem.
- [ ] Aprovar copy, CTAs e preços.

### Fase B — Arte e layout
- [ ] Storyboard desktop e mobile de todas as páginas P0.
- [ ] Produzir fotografias P0 e composições; foco nas F01/F02/F03/F07/F08–F11.
- [ ] Preparar versão estática completa antes dos efeitos.
- [ ] Definir tratamentos de movimento e estados interativos.

### Fase C — Desenvolvimento comercial
- [ ] Header, footer, design system, Home, páginas P0, legal e contato.
- [ ] CTAs de WhatsApp/e-mail funcionando (desktop e mobile), sem formulários; SEO e analytics somente se legalmente configurados.
- [ ] Demo guiada sem conexões ao ambiente real.
- [ ] Motion progressivo e otimizado.

### Fase D — Qualidade e publicação
- [ ] Validar desktop/tablet/mobile e vários navegadores.
- [ ] Testar acessibilidade e redução de movimento.
- [ ] Auditar LCP/INP/CLS, peso e legibilidade.
- [ ] Revisar conteúdo jurídico e comercial, prints e imagem do card; confirmar os canais de contato e as obrigações da seção 13.
- [ ] Publicar somente após checklist de funcionamento completo.

## 12. Insumos necessários para produzir os materiais reais
1. Logotipo TapServe original (preferência SVG) e arquivo da arte final do card horizontal fixado à mesa.
2. Screenshots reais do TapServe em todos os fluxos, ou acesso seguro a um ambiente demo autorizado para capturar.
3. Definição do modelo físico final (só NFC? NFC + QR? dimensões? superfície/acabamento?).
4. Confirmação da tabela comercial de benefícios por plano, taxas e política de instalação.
5. Canais oficiais atuais: WhatsApp `+55 17 99758-5762` (link `wa.me/5517997585762`) e e-mail `pedrocarrega5@gmail.com` (link `mailto:`). **Na interface, exibir somente os botões “Enviar mensagem” e “Enviar e-mail”, com ícones.**
6. Identificação jurídica real do fornecedor, regime de contratação, inventário de tratamento de dados, provedores, informações de suporte e políticas efetivamente praticadas para aprovação das páginas legais.

---

## 13. Conformidade jurídica e proteção de dados — instruções obrigatórias para criação das páginas legais

> **Natureza desta seção:** especificação de requisitos, pesquisa e validação; **não é parecer jurídico nem texto final**. O objetivo é reduzir erros e exposição jurídica, **não garantir ausência de processos, multas ou reclamações**. Antes da publicação, validar a legislação vigente e submeter os documentos e a operação a profissional habilitado em direito digital/contratos e LGPD. Nenhum documento pode ser marcado “aprovado” por um gerador de texto ou por um teste técnico.

### 13.1 Normas e fontes que precisam ser conferidas na redação

- **LGPD — Lei 13.709/2018:** princípios, agentes, bases legais, informação ao titular, direitos, segurança, responsabilidade, incidentes e transferências.
- **Marco Civil da Internet — Lei 12.965/2014 e regulamentação:** uso da internet, direitos dos usuários, registros e obrigações aplicáveis a provedores, **após enquadramento jurídico**.
- **Código de Defesa do Consumidor — Lei 8.078/1990** e **Decreto 7.962/2013 (comércio eletrônico)**, nas relações em que forem aplicáveis; incluir informação do fornecedor, transparência, canais de atendimento, cancelamento e arrependimento pertinentes.
- **ANPD:** orientações atuais sobre controlador/operador, cookies, encarregado, agentes de pequeno porte (Res. 2/2022), incidentes (Res. 15/2024), atuação do encarregado (Res. 18/2024) e transferências internacionais (Res. 19/2024), **se incidentes, compartilhamentos ou transferências se enquadrarem**. Verificar sempre a versão vigente das regras e eventuais alterações antes de publicar.
- Avaliar, com assessoramento jurídico, normas contratuais e obrigações acessórias relevantes ao modelo específico de assinatura e venda de material físico. **Não pressupor** que toda venda entre empresas afaste automaticamente o CDC nem que toda contratação seja regida por ele.

### 13.2 Levantamento obrigatório ANTES de redigir qualquer política ou termo

Criar registro verificável com as respostas e evidências para:

1. **Quem presta o serviço:** razão social/nome empresarial, CNPJ (se existente), endereço e contatos legais, responsável contratual, domínio, país e capacidade de contratar. **Não inventar CNPJ, endereço ou pessoa jurídica.** Validar identificação do fornecedor exigida na oferta/contratação digital, mesmo que o layout visual de `/contato` e `/suporte` mostre apenas botões.
2. **Onde dados entram:** site público **sem formulários**; logs de servidor/CDN, hospedagem, cookies, analytics se houver, cliques em links externos; contatos iniciados voluntariamente no WhatsApp/e-mail; e, separadamente, dados no aplicativo operacional dos estabelecimentos.
3. **Dados reais por fluxo:** visitantes (por exemplo, IP e registros técnicos, se coletados), interessados que entram em contato, representantes dos clientes contratantes, funcionários dos estabelecimentos, consumidores nas mesas e logs de auditoria. Mapear campos **efetivamente usados**, sem presumir que todos são coletados.
4. **Finalidade e base legal por operação:** apresentar hipótese legal específica e justificativa para cada tratamento; **não usar “consentimento” como base genérica para tudo** nem afirmar consentimento quando não existe mecanismo válido.
5. **Retenção e exclusão:** prazos efetivos por categoria (inclusive backups, logs e obrigação de guarda), critério de cálculo, responsáveis e rotina de descarte. Não declarar “apagamos imediatamente” sem verificar backups e limites legais.
6. **Terceiros e infraestrutura:** hospedagem, armazenamento, CDN, provedores de mensagens, analytics, processadores de cobrança e outros operadores/suboperadores efetivamente utilizados, inclusive países de acesso/armazenamento. Avaliar transferências internacionais e instrumentos exigidos pela LGPD/ANPD, se aplicáveis.
7. **Segurança real:** controles implantados e efetivamente operacionais (autenticação, autorização, logs, criptografia quando usada, backups, monitoramento e resposta a incidentes). Não divulgar segredos técnicos nem alegar certificações, conformidade absoluta ou disponibilidade garantida sem evidência.
8. **Direitos dos titulares e canal:** como receber, identificar com segurança, registrar, analisar e responder solicitações de acesso, correção, eliminação, oposição, portabilidade e outras, conforme base legal, limites e regras aplicáveis.
9. **Contratação:** forma real de fechamento de contrato e aceite, preço, impostos quando pertinentes, renovação, método de cobrança, reajuste, unidades/mesas e adicionais, instalação, cards físicos, suporte, suspensão, cancelamento e devolução. Não estabelecer condições que não existam no processo comercial.
10. **Encarregado / canal de contato:** verificar obrigação de indicação, possibilidade de dispensa para agentes de pequeno porte quando cabível e forma de divulgação. Uma dispensa não significa ausência de obrigação de manter canal de comunicação com titulares.

**Entregável de auditoria:** matriz `fluxo → dados → finalidade → base legal → controlador/operador → sistema/terceiro → retenção → direitos → evidência`, atualizada sempre que a arquitetura real mudar.

### 13.3 Política de Privacidade (`/privacidade`) — tópicos mínimos

- Identificação verdadeira de quem controla cada tratamento e contato adequado para privacidade.
- Escopo claro: **site institucional vs. plataforma operacional**, inclusive separação das finalidades comerciais e do tratamento realizado em nome de estabelecimentos.
- Categorias de dados **realmente** tratados e fontes de coleta; evitar afirmações falsas sobre formulários inexistentes.
- Finalidades, bases legais e, quando exigido, informações sobre legítimo interesse e salvaguardas específicas.
- Compartilhamentos, provedores, eventuais transferências internacionais e meios de proteção aplicáveis.
- Retenção e exclusão por critério verificável, não números arbitrários.
- Direitos do titular e **procedimento claro para exercê-los**, usando canal funcional. A área visual de suporte pode permanecer com dois botões; os avisos/documentos legais devem disponibilizar identificação e contato suficientes conforme a lei.
- Cookies e tecnologias semelhantes, se existirem, com remissão à informação/painel correspondente.
- Proteções relevantes, limites reais e processo de revisão da política; informar **data de vigência e última atualização** reais.
- Se houver tratamento de dados de crianças/adolescentes, analisar o regime específico e adequar práticas de tratamento e transparência; não afirmar que não ocorre sem verificar o produto.

### 13.4 Relação TapServe × estabelecimentos: papéis, contratos e instruções

- Determinar **por operação** quem decide finalidade/meios e quem executa o tratamento. O estabelecimento **pode ser controlador** de dados de clientes e funcionários em determinados fluxos, enquanto o TapServe **pode ser operador**; em outros, o TapServe pode atuar como controlador para suas próprias finalidades. **Não declarar classificação universal sem análise.**
- Incluir no instrumento contratual apropriado cláusulas de tratamento de dados (**DPA/anexo de proteção de dados**, se necessário), instruções documentadas, limites de uso, confidencialidade, operadores/suboperadores, segurança, solicitações dos titulares, colaboração em incidentes, retenção, devolução/eliminação e auditoria, compatíveis com a realidade.
- Distinguir dados do contratante/administrador e dados de consumidores finais. Não utilizar dados operacionais dos restaurantes para marketing, compartilhamento não contratado ou treinamento de IA sem fundamento e autorização apropriados.
- Confirmar eventual transferência internacional e os mecanismos legais correspondentes; não prometer localização exclusiva no Brasil sem prova.

### 13.5 Termos de Uso do site (`/termos`) versus contrato de assinatura

**Termos do site (`/termos`)** devem tratar: acesso ao conteúdo público, identificação do fornecedor, finalidade informativa, propriedade intelectual do produto e das imagens, links de terceiros, limites legais de responsabilidade, regras de uso e canal de contato.

**Termos/contrato do SaaS (`/termos-assinatura` ou contrato comercial aprovado)** devem tratar, conforme a contratação efetiva:

- Qual serviço e funcionalidades contratados; requisitos operacionais; responsabilidades de cada parte.
- Planos **Essencial e Pro**, quantidades de unidades e mesas, adicionais, eventuais limites, preços, taxas de configuração, custo/entrega/substituição de cards, impostos quando pertinente e hipótese de alteração comercial.
- Data do ciclo, método de cobrança, renovação, inadimplência, aviso prévio, reajuste e regras de eventual mudança de plano, **somente conforme modelo efetivo**.
- Suporte realmente oferecido, canais e horários **se aprovados**, manutenção e indisponibilidade, sem SLA fictício ou isenção de responsabilidade incompatível com a lei.
- Política de cancelamento, tratamento de pedidos pendentes, reembolso, restituição, acesso/exportação de dados e eliminação após encerramento, incluindo obrigações de guarda.
- Propriedade intelectual, autorização de uso da plataforma, dados do estabelecimento e deveres de segurança de credenciais.
- Limites de responsabilidade razoáveis e juridicamente revisados; **não** inserir renúncias genéricas de direitos, exoneração total por culpa própria, foro abusivo nem cláusulas contraditórias com a oferta.
- Mecanismo real de informação e aceite/assinatura, versão e histórico comprovável do instrumento, especialmente se a contratação ocorrer online. **O site V2 não terá checkout nem formulário de contratação.**

### 13.6 Cancelamento e reembolso (`/cancelamento`)

- Informar como o cliente solicita cancelamento **pelos dois canais atuais**, sem inventar fluxo automatizado, botão de cancelamento efetivo ou portal de tickets.
- Não escolher arbitrariamente multa, reembolso integral/parcial, fidelidade, prazo de processamento, período mínimo, prazos de arrependimento ou obrigações envolvendo cards físicos.
- Confirmar com análise contratual e jurídica o regime de cada contratação, inclusive quando houver relação de consumo e eventual direito de arrependimento no prazo legal aplicável; alinhar página, orçamento, proposta e contrato.
- Se houver obrigação de confirmar recebimento/solicitação no canal utilizado, definir processo real para cumpri-la; **abrir WhatsApp ou `mailto:` não equivale a confirmar recebimento**.

### 13.7 Cookies, analytics e banners (`/cookies`, condicional)

- Auditar cookies próprios/de terceiros, scripts de métricas, pixels, embeds, SDKs, identificadores e armazenamento local **antes de definir banner**.
- Classificar necessários e não necessários; atribuir bases legais conforme finalidade. Se cookies/rastreadores não necessários dependerem de consentimento, **não ativar antes de opção válida**; oferecer aceitar/rejeitar de forma equivalente e mecanismo posterior de revisão quando aplicável.
- Sem cookies/rastreadores não essenciais, não criar banner decorativo; ainda assim documentar o uso de registros técnicos necessários na política de privacidade.
- Não implementar mecanismos de rastreamento nem relatórios pessoais “por padrão” enquanto o inventário e as decisões legais estiverem pendentes.

### 13.8 Segurança, incidentes e continuidade

- Definir papéis internos, rotina de resposta, trilhas de evidência, registro de incidentes, proteção de credenciais, permissões, backups e exclusões antes de afirmar conformidade.
- Na hipótese de incidente com dados pessoais capaz de causar **risco ou dano relevante**, avaliar os deveres de comunicação do controlador à ANPD e aos titulares. A **Resolução CD/ANPD 15/2024** prevê, em regra, **três dias úteis** e admite particularidades legais/regulatórias, incluindo regras para agentes de pequeno porte quando comprovadamente aplicáveis. **Conferir redação vigente e orientação jurídica no momento do incidente**.
- Definir em contrato fluxos de aviso do TapServe ao estabelecimento quando estiver atuando como operador, para não inviabilizar prazos do controlador.
- Não publicar descrições de autenticação, MFA, backup, hospedagem, criptografia ou segurança que ainda não tenham sido verificadas em produção.

### 13.9 Interface de contato e obrigações de transparência

- **Regra visual definida pelo proprietário:** em `/contato`, `/suporte` e CTAs visuais de contato, **mostrar apenas dois botões com ícones**: **Enviar mensagem** e **Enviar e-mail**. Sem exposição direta do número/e-mail no corpo visual dessas páginas.
- Links técnicos oficiais: WhatsApp `https://wa.me/5517997585762`; e-mail `mailto:pedrocarrega5@gmail.com`. Essas informações ficam centralizadas em configuração; confirmar sua titularidade, disponibilidade e adequação para uso comercial antes do lançamento.
- Não implementar formulário, coleta de leads pelo site, envio automático, chat próprio, criação de ticket nem `/obrigado`.
- **A regra visual não dispensa informações legalmente exigidas** sobre identidade/contato do fornecedor em documentos, rodapé ou ambiente contratual quando aplicável. Se houver conflito, ajustar a apresentação do site ao requisito legal, com revisão profissional; nunca omitir informação obrigatória só para manter a estética.
- Considerar que o contato voluntário pelo WhatsApp/e-mail envolve serviços de terceiros e que as interações subsequentes podem gerar tratamento de dados fora do site; refletir isso na Política conforme os fatos.

### 13.10 Regras estritas para Codex/IA elaborar textos jurídicos

1. **Não publicar texto jurídico automaticamente.** Preparar minutas claramente marcadas **“RASCUNHO — NÃO PUBLICAR”** até revisão e aprovação do responsável e, preferencialmente, de advogado qualificado.
2. Usar fontes oficiais vigentes no momento da redação (leis federais, ANPD e normas pertinentes); informar quais fontes e datas foram verificadas. Não se basear apenas em “modelos prontos” de concorrentes.
3. **Nunca inventar** nome empresarial, CNPJ, endereço, representantes, encarregado, certificações, práticas de segurança, banco de dados, cookies usados, suboperadores, transferências, bases legais, prazos de retenção, prazos de suporte, regras de pagamento ou benefícios de assinatura.
4. Marcar itens ainda não validados como **`[PENDENTE DE CONFIRMAÇÃO]` no documento interno**, mas **não publicar páginas contendo placeholders**; bloquear a publicação até resolver o que for obrigatório.
5. Redigir português do Brasil claro e preciso, acessível para quem contrata e para titulares de dados; evitar ambiguidades e cláusulas abusivas.
6. Preservar **consistência entre site, contrato comercial, política, fluxo operacional, cobrança, suporte e código efetivo**. Se houver discrepância, corrigir o produto/texto antes de publicar.
7. Identificar versão, data real de vigência e histórico de alterações; revisar documentos antes de ativar novos rastreadores, integrações, dados coletados ou serviços.
8. Não tratar LGPD como checkbox de página. Exigir evidência de implementação das práticas descritas; revisão jurídica **não substitui adequação técnica e operacional**.

### 13.11 Checklist de bloqueio de publicação das páginas legais

- [ ] Identificação legal do fornecedor e dados de contato obrigatórios confirmados; enquadramento B2B/CDC e canal de contratação documentados.
- [ ] Inventário de dados completo para site e SaaS, com fluxos, terceiros e bases legais revisados.
- [ ] Política de Privacidade redigida com informações verdadeiras, canal funcional e procedimento de direitos dos titulares.
- [ ] Termos do site e instrumento de assinatura corretamente separados e coerentes com preços, oferta e contrato real.
- [ ] Política de cancelamento/reembolso definida, validada e efetivamente executável pelos canais atuais.
- [ ] Cookies/analytics inventariados; escolhas de consentimento, quando necessárias, funcionais e testadas.
- [ ] Papéis entre TapServe e estabelecimentos avaliados, com cláusulas contratuais de proteção de dados apropriadas.
- [ ] Segurança, retenção, incidentes e serviços de terceiros verificados; não existem promessas falsas de conformidade.
- [ ] `/contato` e `/suporte` testados: botões com ícones, links corretos, sem exibir número/e-mail em texto na área visual, sem formulário e sem página de sucesso fictícia.
- [ ] Todos os textos foram revisados juridicamente e aprovados por responsável identificado antes da publicação; não existem placeholders.

### 13.12 Referências oficiais para consulta e verificação na data da redação

- LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- Marco Civil da Internet: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm
- CDC: https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm
- Decreto do comércio eletrônico: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/decreto/d7962.htm
- ANPD — orientações sobre agentes de tratamento: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-para-definicoes-dos-agentes-de-tratamento-de-dados-pessoais-e-do-encarregado
- ANPD — cookies: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_cookies_e_protecao_de_dados_pessoais
- ANPD — regulamentações e atualizações: https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd
- ANPD — incidentes: https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis
- ANPD — Res. 19/2024, transferências internacionais: https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024

---

**Princípio final:** **fotos chamam atenção, motion mantém interesse, demonstrações reais geram confiança e a proposta comercial converte**. A beleza tem de servir à compreensão do sistema.
