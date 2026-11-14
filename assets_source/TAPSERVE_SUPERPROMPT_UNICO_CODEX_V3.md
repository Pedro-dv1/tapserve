# TAPSERVE — SUPERPROMPT ÚNICO DE EXECUÇÃO SEQUENCIAL (SITE INSTITUCIONAL)

Você é o agente de desenvolvimento responsável por **analisar, projetar, produzir os recursos visuais, implementar e testar** o site institucional/comercial do **TapServe**. Execute as etapas abaixo **na ordem**, avançando automaticamente à próxima assim que concluir a anterior. **Não pare depois de fazer apenas um plano.** Trabalhe até concluir tudo o que for tecnicamente possível na execução atual; se algo estiver bloqueado, registre a pendência específica e continue nas tarefas independentes. Não faça deploy nem publique o site.

## 0. Hierarquia das fontes, escopo e restrições

1. Antes de modificar arquivos, examine o repositório, `AGENTS.md`, instruções locais, documentação e os seguintes arquivos, quando disponíveis:
   - `TAPSERVE_ARQUITETURA_SITE_V2_CONTATO_JURIDICO.md`
   - `TAPSERVE_ASSET_SHEET_V3.md`
   - `TAPSERVE_BRIEF_IMAGENS_V3.md`
   - `TAPSERVE_ASSETS_IMPORTAVEL_V3.csv` ou manifesto de assets equivalente
   - arte da plaquinha: `assets-source/card/tapserve-placa-referencia.png` (localize por nome caso a extensão/caminho sejam diferentes)
   - arquivos originais da logo TapServe, se existirem.
2. Este prompt **consolida decisões posteriores**: (a) a demonstração clicável é obrigatória, mas inteiramente simulada; (b) sem formulários no site; (c) contato/suporte somente pelos dois botões especificados; (d) animações, transições e mouse triggers são importantes; **(e) NÃO implementar agora a animação do celular se aproximando/encostando na tag NFC**. Se documentação anterior exigir V02/scroll de aproximação, considere especificamente essa animação **adiada**, não um requisito desta entrega; imagens estáticas de NFC e explicação do recurso continuam permitidas.
3. Respeite a arquitetura V2 e os inventários V3 onde não houver conflito com estas decisões. Registre divergências no relatório de decisões, sem introduzir funcionalidades de produto fora do escopo. A **imagem original enviada da plaquinha** é fonte visual soberana para seu formato, cores, tipografia, posição do NFC, arredondamento discreto e proporções. A arte final de referência prevalece sobre descrições genéricas anteriores se houver divergência visual.
4. Mantenha o **site de marketing separado do backend e dos bancos** do TapServe. Analise o sistema existente **somente em leitura**, para verificar funcionalidades e dados jurídicos, e capture telas apenas de ambiente demo/QA autorizado, sem alterar infra, bancos, credenciais, dados persistentes ou produção. Não acione ações reais de pedido, atendimento ou cobrança durante a criação do site.
5. Nunca invente integração, funcionalidade, depoimento, cliente, resultado estatístico, certificação, equipe, CNPJ, razão social, política comercial ou termos contratuais. Não copie imagens/textos de concorrentes; Goomer, me&u e OlaClick são referências de *abordagem*, não templates nem conteúdo a reproduzir.
6. Não faça deploy, não altere DNS, não compre serviços, não envie mensagens/e-mails e não aceite contratos. Evite mudanças destrutivas. Se uma ferramenta necessária estiver indisponível (por exemplo, geração de imagens ou browser), continue com estrutura funcional e deixe pendências identificadas — nunca declare sucesso fictício.

## 1. Objetivo e conceito criativo

Criar uma **home page comercial com narrativa de landing page** + páginas internas especializadas. A pessoa deve perceber em poucos segundos o que é o TapServe, entender a experiência do cliente e a operação do restaurante, experimentar uma simulação e ter um caminho claro para pedir uma demonstração. Público: proprietários, gerentes e administradores de restaurantes, hamburguerias, lanchonetes, bares e cafeterias.

**Direção visual:** SaaS premium/editorial, elegante, moderno, comercial, original e acessível; fotografia fotorrealista com luz quente e tratamento consistente; tipografia marcante, textos curtos, muito respiro. Evitar site genérico de cards repetidos, excesso de gradientes, efeitos gratuitos e seções intermináveis iguais. Alternar áreas escuras de impacto e áreas claras de leitura. Paleta: preto `#111111`, branco `#FFFFFF`, cinza `#F5F5F3`, âmbar `#E5A62B`. Testar Inter ou Manrope sem alterar o desenho do wordmark. Copy de trabalho: **“Seu atendimento começa com um toque.”** Não confundir nome: é **TapServe**, nunca TAPself/TapSurf.

**Narrativa de conteúdo:** card na mesa → NFC/QR abre o sistema → cliente escolhe no cardápio → faz pedido → equipe e cozinha recebem → gestor administra o negócio. Esse fluxo deve ficar inteligível **sem** a animação física de aproximação NFC nesta versão. Animações atuais podem destacar telas, pedidos, interfaces, galerias e transições entre capítulos, mas não simular o celular tocando na tag.

## 2. Plano de execução contínua (faça tudo em sequência)

Execute estas fases e mantenha um checklist no repositório (`docs/site/EXECUCAO.md`). Não peça autorização para decisões triviais de implementação; escolha alternativas seguras e documente. Se um requisito dependente de dados desconhecidos não puder ser concluído, marque como `PENDENTE` e siga adiante. Revise e teste a fase anterior antes de começar a seguinte.

**Fase 1 — Auditoria e planejamento:** reconhecer estrutura do repositório, identificar onde criar o site sem modificar o app, ler instruções, inventariar assets existentes, verificar ambiente/tooling, mapear funcionalidades reais e preparar matriz do site. Verificar se há ferramentas de geração de imagem e browser/screenshots; não afirmar capacidade sem testar.

**Fase 2 — Direção de arte e assets:** estabelecer design tokens, layouts desktop/mobile, guia de fotografia, organização de assets e lista de material disponível/pendente. Produzir os assets por lotes coerentes usando ferramenta real de imagem, quando disponível; gerar primeiro cenas que não exigem interface verdadeira, depois compor card/brand com artes originais; capturar prints reais autorizados quando possível; criar formatos responsivos e capas sociais. Controlar nomes por ID. Não transformar fotos de concorrentes em material comercial.

**Fase 3 — Fundação do site:** configurar aplicação, rotas, layout global, tipografia, header sticky, menu mobile, footer, links, componentes de CTA, temas, utilitários de motion, SEO e tratamento de imagens. Preferir **Next.js + TypeScript + Tailwind CSS** com geração estática/SSR para páginas comerciais se não houver stack existente melhor estabelecida. Utilizar Motion para microinterações, CSS para efeitos simples e GSAP/ScrollTrigger somente em experiências narrativas que realmente precisem dele; evitar bibliotecas redundantes.

**Fase 4 — Implementar TODAS as páginas descritas na seção 4**, com conteúdo estruturado, estados, responsividade e CTAs funcionais. Não encerrar o trabalho apenas com a Home.

**Fase 5 — Construir demonstração clicável**, usando componentes reais de interface adaptados ou reprodução visual fiel, mas um motor de simulação **100% local/isolado**, sem backend real; reutilizar a mini demo na Home.

**Fase 6 — Aplicar motion e mouse triggers** nos pontos definidos na seção 6. Fazer acabamento premium por página. **Excluir a animação de aproximação NFC desta versão**, inclusive seus gatilhos de scroll e autoplay. Preparar componentes reutilizáveis para futura implementação sem gerar uma animação falsa agora.

**Fase 7 — Auditoria de dados e minutas jurídicas:** inspecionar a plataforma somente em leitura, levantar fatos e fontes oficiais atuais, redigir minutas e criar páginas legais com bloqueio de publicação enquanto não aprovadas; registrar questões em aberto. Jamais declarar conformidade total nem afirmar que os documentos eliminam risco jurídico.

**Fase 8 — QA e revisão final:** executar lint/typecheck/build/testes apropriados, inspecionar desktop/tablet/mobile, verificar acessibilidade, performance, SEO, links e demo, revisar alinhamento visual e listar defeitos resolvidos/persistentes. Registrar evidências; não publicar.

**Fase 9 — Entrega:** entregar site implementado, assets com manifesto, relatório das páginas, relatório de testes, pendências de asset e checklist comercial/jurídico. Deixar instruções reproduzíveis de execução local e de como substituir imagens pendentes.

## 3. Padrão de assets e uso da plaquinha fornecida

A foto crua da plaquinha foi fornecida **para servir de referência exata**, não para ser mostrada como uma fotografia pronta de mesa. Preserve arte, proporções, wordmark, símbolo, cor, orientação, localização do NFC e cantos de raio discreto. Em fotografias, a plaquinha deve ficar **horizontal e fixada/colada diretamente à mesa**, nunca em suporte vertical, salvo se o arquivo aprovado explicitamente mostrar outro modelo. Não criar bordas excessivamente arredondadas nem trocar frente pelo verso. Se a referência não tiver QR, não adicione QR à variante por conta própria.

**MUITO IMPORTANTE:** geradores podem distorcer logotipo, tipografia e QR. Prefira gerar a **fotografia do cenário sem texto/cartão** e aplicar a **arte original do card** em composição/perspectiva por ferramenta de edição/código; igualmente, sobrepor **screenshots reais** nas telas de celulares, tablets e KDS. Não afirmar fidelidade se houver deformação: marque para revisão. Não criar QR scannable falso nem link que direcione a pedidos reais. Não usar imagem de terceiro sem licença.

Inventário e nomes canônicos (consulte as especificações detalhadas V2/V3; não renumere arquivos arbitrariamente):

- **B01–B06 (marca e ícones):** logo preta, variante clara, símbolo original, favicon, ícone NFC, ícone QR. Derivar da logo fornecida, sem inventar uma nova marca.
- **F01–F18 (fotografia):** F01 restaurante hero panorâmico; F02 card real fixado na mesa; **F03 celular aproximando do card = OPCIONAL, somente fallback/referência estática, NÃO animação**; F04 cliente usando o cardápio; F05 comida + celular; F06 garçom/equipe em operação; F07 cozinha com KDS real sobreposto; F08 card a 45°; F09 card visto de cima; F10 macro da área NFC; F11 detalhe do QR apenas de variante real; F12 card em mesa montada; F13 restaurante; F14 hamburgueria; F15 lanchonete; F16 bar; F17 cafeteria; F18 encerramento da Home. Priorize F01, F02, F04, F06–F11; produza o restante se houver geração disponível.
- **S01–S20 (prints REAIS):** S01 abertura da mesa; S02 cardápio; S03 produto e opcionais; S04 carrinho; S05 pedido confirmado; S06 status de pedido; S07 chamado de garçom; S08 solicitação de conta; S09 mesas staff; S10 pedidos staff; S11 chamados staff; S12 detalhes mesa/pedido; S13 KDS novos; S14 KDS preparo; S15 KDS prontos; S16 painel admin; S17 cardápio admin; S18 equipe/unidades; S19 relatórios (só se existir e validado); S20 mesa/conta no painel. Não inventar capturas reais. Dados exclusivamente fictícios/anonimizados.
- **D01–D08 (fotografias de itens da demo):** hambúrguer artesanal, batata frita, refrigerante, água, brownie com sorvete, milk-shake, sanduíche de frango, salada. Mesmo estilo, nomes e preços explicitamente simulados.
- **C01–C06 (composições):** hero foto/card/celular; percurso do card ao telefone em composição **estática**; fluxo do pedido em mockup; ligação visual cliente→cozinha; galeria do card físico; conjunto cliente/equipe/KDS/admin. Preferir composição de camadas HTML/CSS ou imagens montadas com originais reais.
- **V01–V04 (motion):** V01 loop suave de atmosfera no hero (opcional, sempre com poster); **V02 aproximação NFC = ADIADO, NÃO PRODUZIR/IMPLEMENTAR NESTA VERSÃO**; V03 mudanças do cardápio até confirmação (motion de UI real/simulada); V04 representação do pedido aparecendo no KDS (apenas ilustrativa, sem backend). Não é obrigatório produzir vídeo pré-renderizado quando a animação em código for melhor.
- **M01–M03 (camadas futuras):** mesa vazia, mão/celular recortados, card isolado — reservados para animação NFC futura, **não são bloqueadores do lançamento atual e não devem ser animados agora**.
- **O01–O05 (Open Graph):** capa Home, NFC, funcionalidades, planos e demonstração, padrão 1200×630, marca fiel.

Salve fontes/originais separadamente dos derivados. Gere `public/assets/...` e um manifesto (`docs/site/ASSET_MANIFEST.md` ou JSON) com ID, arquivo, origem, página, prioridade, estado `real / gerado / composto / placeholder / pendente`, licença e revisão. **Se não houver imagegen**, não afirme que gerou imagens: preserve posições/`aspect-ratio` e registre claramente os nomes e prompts dos assets pendentes. Não substitua cenas premium por emojis, gradientes aleatórios ou fotos incompatíveis. Nunca transmita uma imagem gerada de interface como captura real.

## 4. Sitemap e especificação de TODAS as páginas

### 4.0 Navegação e componentes globais
- Header: marca original, **Como funciona**, **Funcionalidades**, **NFC + QR**, **Planos**, **Demonstração** e CTA **Solicitar demonstração**; menu mobile acessível; navegação clara para Contato e Suporte.
- Footer: Produto, Empresa, Ajuda, Legal; links para páginas existentes, contato/suporte, políticas, termos, cancelamento; redes sociais somente se verificadas. Identificação do fornecedor onde obrigatória, sem inventar dados.
- Rotas: `/`, `/como-funciona`, `/funcionalidades`, `/nfc-e-qr-code`, `/para-quem`, `/planos`, `/demonstracao`, `/contato`, `/suporte`, `/duvidas`, `/sobre`, `/privacidade`, `/termos`, `/cancelamento`, `/cookies` **somente se justificável pelo inventário real**, `/termos-assinatura` **somente se houver minuta/contrato aplicável e revisão**; e estado `404` para rotas inexistentes. **NÃO criar `/obrigado` nem formulário**.

### 4.1 Home `/` — roteiro completo de 13 blocos
- **H00 Header flutuante:** logo, navegação, CTA; muda fundo conforme contraste, sem esconder links.
- **H01 Hero cinematográfico:** copy de impacto (“Seu atendimento começa com um toque.” ou alternativa aprovada), subtítulo NFC/QR, pedidos, atendimento e operação; foto F01/C01 com arte real do card; CTAs **Conhecer como funciona** e **Solicitar demonstração**. Entrada por camadas, possível vídeo atmosférico V01 com fallback estático. Sem celular encostando no NFC.
- **H02 Faixa de valor:** “Aproxime. Peça. Acompanhe. Organize.” ou copy equivalente curta, animação em sequência discreta.
- **H03 Como começa:** comparação/explicação visual estática e interativa de NFC e QR, fotos do card e telas reais de acesso; sem motion de aproximação.
- **H04 Pedido em ação:** mockup mobile com telas S02–S06 e/ou mini simulação do pedido (abas/etapas controladas pelo visitante), CTA para demo completa.
- **H05 Do cliente à operação:** motion ilustrativo de um pedido confirmado para atendimento/KDS com S09–S15; nunca escrever em servidor real.
- **H06 Dentro do TapServe:** tabs acessíveis Cliente / Equipe / Cozinha / Administração, screenshots reais S01–S20 quando disponíveis, descrições curtas e hotspots opcionais.
- **H07 Card físico:** fotografia publicitária premium F08–F12, ângulos, diferenciação NFC/QR, CTA da página específica.
- **H08 Benefícios:** composição bento assimétrica e fundamentada: agilidade de atendimento, organização, autonomia, controle; evitar ganhos quantitativos não provados.
- **H09 Para quem:** galeria editorial F13–F17 de restaurantes, bares, hamburguerias, lanchonetes e cafeterias, com links contextualizados.
- **H10 Planos resumidos:** Essencial / Pro com limites de unidades e mesas; avisos e adicionais apenas confirmados.
- **H11 FAQ essencial:** 5–6 perguntas úteis, accordion acessível.
- **H12 CTA final + footer:** foto F18 ou composição fiel, chamada de demonstração, dois caminhos de contato.

### 4.2 `/como-funciona`
Hero com card e interface verdadeira; sequência clara: acessar por NFC ou QR → abrir página da mesa → visualizar cardápio → selecionar item e opcionais → revisar/enviar pedido → acompanhar status → possíveis chamados e solicitação de conta. Depois, visão da equipe e cozinha: chegada do pedido, preparo e conclusão. Mostrar etapas de implantação **somente se confirmadas**. Timeline de telas reais, navegação de etapas, FAQ e CTA para demo.

### 4.3 `/funcionalidades`
Hero com ecossistema de dispositivos e navegação por categorias. Apresentar **Cliente** (cardápio, opcionais, carrinho, status, chamar garçom, pedir conta), **Mesas/Atendimento**, **Pedidos**, **Cozinha/KDS**, **Gestão/Administração**, **Unidades e Equipe**, **Relatórios** (somente se existir). Para cada área: uma captura real ou fallback rotulado, descrição curta, benefício verificável e interação visual. Mostrar segurança sem afirmações não verificadas ou divulgação de segredos.

### 4.4 `/nfc-e-qr-code`
Hero foto do card real; galeria vista superior/45°/macro/na mesa; explicar NFC vs QR com compatibilidade e limitações reais; mostrar tela que abre no celular, ativação dos cards apenas se fluxo existente; modelos e valores somente aprovados; FAQ e CTA. Não implementar agora a animação de aproximação do celular.

### 4.5 `/para-quem`
Galeria fotográfica por estabelecimento: restaurantes, hamburguerias, lanchonetes, bares, cafeterias. Apresentar cenários de uso plausíveis e funcionalidades reais, inclusive multiunidade se verificado. CTA por segmento; sem criar recursos diferentes para cada nicho que o produto não tenha.

### 4.6 `/planos`
Página comercial com comparação responsiva e CTA. **Dados de referência a validar antes de publicizar como oferta:** Essencial R$ 159,90/mês, até 5 unidades e **50 mesas no total entre todas as unidades**; Pro R$ 229,90/mês, até 10 unidades e **80 mesas no total**; adicional **+20 mesas por R$ 59,90/mês**. Taxa de implantação e preço de cada card físico separados e sujeitos a definição final. Não inventar diferenças de recursos, limites de usuários, descontos, períodos anuais, descontos tachados ou garantias. Se exibir simulador de quantidade de mesas, fazer contas corretas e deixar claro o caráter informativo dos valores não aprovados; caso não haja aprovação comercial, manter dados parametrizados com aviso interno e evitar alegações definitivas em interface publicada. FAQ comercial e contato.

### 4.7 `/demonstracao` — DEMO INTERATIVA OBRIGATÓRIA
Implementar um **pedido de mentira, mas uma experiência clicável de verdade**. Design inspirado nas telas existentes do cliente do TapServe (não inventar que é backend real). Sem login, sem envio de dados para servidor, sem requests de escrita, sem sessão real de restaurante, sem acesso a staff/admin real, sem pagamento. Toda a lógica pode ser JSON + estado local, resetável, com dados fictícios. Mostrar badge ou aviso discreto e permanente: **“Demonstração — nenhum pedido é enviado a um restaurante.”**

Fluxo completo:
1. abertura de “Mesa Demonstração” com contexto fictício;
2. exibição de categorias e produtos ilustrativos D01–D08;
3. detalhe do produto com opcionais coerentes (required/SINGLE/MULTIPLE/min/max quando aplicável), quantidade e preço demonstrativo;
4. adicionar/remover/alterar itens no carrinho com totais corretos;
5. revisar carrinho e confirmar **pedido simulado**;
6. mostrar “Pedido recebido” e avançar por estados simulados (“Em preparo”, “Pronto”, “Entregue”), com botões de controle acessíveis — não prometer atualização em tempo real;
7. simular “Chamar garçom” e “Solicitar conta”, com confirmação explícita de simulação;
8. fornecer **Reiniciar demonstração**, Voltar, Avançar, seções de orientação discretas e forma de sair para planos/contato;
9. opcionalmente mostrar uma **visão de cozinha/equipe inteiramente simulada** para ilustrar o mesmo pedido, claramente rotulada;
10. todas as interações devem funcionar com mouse, teclado e toque, sem loops bloqueantes nem dados persistidos desnecessariamente.

Reaproveitar o motor local da demo numa **mini demonstração da Home** (mais curta) para reduzir duplicação. Usar preços e nomes fictícios marcados como demonstração. Não reutilizar credenciais ou endpoints reais do TapServe para fazer a demo funcionar. Não criar rastreamento do comportamento da demo sem inventário/decisão de privacidade.

### 4.8 `/contato`
Layout limpo e convincente, sem foto desnecessária e **SEM formulário**. Texto curto, contexto de demonstração comercial e exatamente estes dois botões de ação com ícones: **“Enviar mensagem”** (WhatsApp) e **“Enviar e-mail”** (mailto). Não mostrar número/e-mail no corpo da página. Não inventar promessa de horário ou tempo de resposta.

### 4.9 `/suporte`
Central de suporte com apresentação breve, tópicos de ajuda (primeiros passos, NFC/QR, pedidos/mesas, equipe, planos/cobrança) e links relevantes ao FAQ; sem portal de tickets funcional e **SEM formulário**. Contato unicamente por dois botões com ícones: **“Enviar mensagem”** e **“Enviar e-mail”**. Não prometer suporte 24h nem prazos sem aprovação.

### 4.10 `/duvidas`
FAQ por categorias: como funciona, NFC/QR, implantação, planos e cobrança, operação, suporte. Busca local simples (sem enviar consultas ao backend), accordion acessível, CTAs para demo e contato. Respostas factuais e aprováveis; nada fictício.

### 4.11 `/sobre`
Propósito do TapServe, valor ao estabelecimento, visão da marca. Texto profissional e verificável, sem inventar biografia da empresa, equipe, clientes, fundadores, prêmios ou datas. Fotografias apenas autorizadas/geradas para ilustração, sem representar supostos funcionários reais.

### 4.12 `/privacidade`
Página legal legível e estruturada, a partir da auditoria obrigatória na seção 7; minuta não validada não deve ser apresentada ao visitante como política vigente. Não afirmar existência de formulários de contato, coleta de leads por formulário, consentimento inexistente ou práticas de segurança não verificadas. Quando faltarem dados obrigatórios, guardar minuta interna marcada “RASCUNHO — NÃO PUBLICAR” e deixar a rota pública bloqueada para publicação/revisão, sem texto legal falsamente definitivo.

### 4.13 `/termos`
Termos de Uso do **site institucional**, separados da contratação do SaaS. Regras de acesso, propriedade intelectual, links externos, responsabilidades legais em limites válidos, contato e versão. Minuta jurídica sujeita a revisão. Caso seja necessário instrumento distinto para assinatura da plataforma, preparar `/termos-assinatura` **como minuta separada**, sem fingir que foi aceita/validada ou publicá-la sem aprovação.

### 4.14 `/cancelamento`
Conteúdo sobre como solicitar cancelamento pelos canais atuais e minuta das condições efetivamente praticadas, de acordo com o modelo de assinatura e lei aplicável. Não inventar reembolso, arrependimento, multa, fidelização, prazo ou fluxo automatizado. Se faltarem definições, manter minuta interna com pendências e restringir a rota pública até aprovação.

### 4.15 `/cookies` (condicional)
Fazer antes inventário real de cookies, storage, SDKs, embeds e scripts de rastreamento. Se não houver necessidade, não criar banner decorativo; se houver cookies não essenciais, avaliar requisitos de consentimento e criar mecanismo apropriado antes da ativação. Texto e controles devem refletir rastreadores efetivamente usados, sem dizer que existem cookies inexistentes. Página somente se aplicável.

### 4.16 `404` e estados auxiliares
404 personalizada: “Esta mesa não foi encontrada”, com CTA para Home e links úteis; states loading, erro e vazio cuidadosamente escritos onde aplicável. Não criar `/obrigado` (não há formulário nem envio no site).

## 5. Canais oficiais e comportamento de CTAs

Centralize dados em um arquivo de configuração (por exemplo, `src/config/contact.ts`):
- WhatsApp: **`https://wa.me/5517997585762`** (número brasileiro +55; internamente pode receber parâmetro `text` corretamente codificado).
- E-mail: **`mailto:pedrocarrega5@gmail.com`**.
- Nos componentes das páginas de contato e suporte, mostrar **apenas ícone + rótulo visível “Enviar mensagem” e “Enviar e-mail”**. Não renderizar telefone nem e-mail como texto solto nessas páginas; os destinos existem em links. Um CTA “Solicitar demonstração” pode dirigir a `/contato` ou ao link comercial configurado.
- Diferenciar texto pré-preenchido de WhatsApp comercial (“Olá, gostaria de conhecer o TapServe e solicitar uma demonstração.”) e suporte (“Olá, preciso de ajuda com o TapServe.”). Usar `encodeURIComponent`, sem acrescentar dados pessoais automaticamente.
- Botões externos com acessibilidade, `aria-label` quando necessário e foco visível. **Abrir WhatsApp ou e-mail não confirma que uma mensagem foi enviada ou recebida**; não criar notificações de sucesso falsas.
- A regra estética de não exibir identificadores nas páginas não substitui a transparência/identificação do fornecedor exigida na documentação legal, contratação ou rodapé conforme lei; não esconder dados obrigatórios para simular cumprimento estético.

## 6. Animações, transições e mouse triggers — parte indispensável

Site elaborado e cheio de movimento **com propósito**, sem prejudicar leitura ou responsividade:
- **Hero:** texto e produto entram por camadas; fundo com parallax sutil em desktop, poster estático de fallback, movimento interrompível se automático.
- **Scroll storytelling (SEM aproximação NFC):** revelar telas e benefícios progressivamente, transição visual de pedido cliente → staff/KDS; sticky apenas em segmentos curtos e sem sequestrar scroll.
- **Mouse triggers:** brilho discreto que acompanha ponteiro em alguns cards, tilt 3D leve em peças selecionadas, paralaxe de poucos pixels em fotos/mockups, botões com resposta magnética muito sutil, hover e foco com transições; não substituir cursor padrão por efeito intrusivo.
- **Galeria card:** troca de ângulos, zoom de detalhes, hotspots explicativos, suporte toque/teclado; cada foto respeita o original.
- **Tabs e mockups:** troca animada entre interfaces do cliente/equipe/cozinha/admin; `aria`/controle acessível; conteúdo inteligível sem JS quando aplicável.
- **Demonstração:** transições entre categorias, adição ao carrinho, confirmações simuladas, status e alternância entre visões, sem tempos artificiais longos.
- **Planos, FAQ, nav:** reveals escalonados moderados, accordion sem travamento, menus fluidos e botões com feedback.
- **Regra inegociável:** respeitar `prefers-reduced-motion`, oferecer pausa de movimento automático relevante, não depender de hover em mobile, preservar foco/teclado e evitar animações que atrasem o conteúdo. Não usar `scroll-jacking`, loader longo ou vídeos pesados impedindo primeira dobra.
- **Explicitamente ADIADO:** celular aproximando/encostando no card/tag NFC e abertura da interface disparada por esse contato. Não implementar, não inserir código parcialmente ativo e não apresentar como concluído. Deixar apenas um registro no backlog para a futura fase.

## 7. Investigação real para política, termos e conformidade (sem promessas jurídicas fictícias)

**Antes de redigir**, fazer uma **auditoria somente em leitura** do site e, se o código estiver disponível, do TapServe operacional. Produzir `docs/site/LEGAL_AUDIT.md` com tabela: `fluxo | dados coletados | finalidade | base legal candidata | controlador/operador | origem/destino | terceiros | retenção efetiva | evidências | lacunas`.

Verificar sem presumir:
- identidade verdadeira do fornecedor, razão social/nome, CNPJ se existente, endereço/identificação exigida, país, canais de contato e contratação;
- ausência de formulários no site; logs HTTP/CDN/hospedagem, cookies e analytics reais, contatos voluntários por WhatsApp/e-mail, links externos;
- no SaaS: dados de estabelecimentos, responsáveis, funcionários, clientes nas mesas, sessões, pedidos, chamados, logs, pagamentos apenas conforme implementação real; categorias eventualmente de menores se existirem;
- finalidades/bases legais concretas, retenção/backups/exclusão, suboperadores/hospedagem, localização/transferência internacional, políticas reais de incidentes e direitos de titulares;
- quando o TapServe é controlador de seus próprios fluxos e quando pode atuar como operador de dados dos restaurantes; necessidade de anexo contratual/DPA;
- modelo real de assinatura, preços e adicionais, reajuste, suporte, suspensão, cancelamento, cobrança, eventual direito de arrependimento quando aplicável, entrega/instalação dos cards e aceites contratuais;
- não declarar “LGPD 100%”, selo de certificação, SLA, prazos ou condições sem comprovação. Não colocar cláusulas abusivas ou isenções gerais de responsabilidade.

**Consulta jurídica:** usar, se houver acesso de rede, **fontes oficiais vigentes** (LGPD Lei 13.709/2018, CDC Lei 8.078/1990 quando aplicável, Marco Civil Lei 12.965/2014, Decreto 7.962/2013 quando aplicável, orientações e resoluções da ANPD, inclusive agentes de tratamento, cookies, incidentes e transferência internacional). Registrar URLs, datas de consulta e pontos utilizados. Se não tiver acesso à legislação atualizada, **registrar impossibilidade de verificação** e não alegar atualização legal confirmada.

**Documentos a elaborar como MINUTA, sujeito a revisão:** política de privacidade do site e relação com SaaS; termos do site; termos comerciais/assinatura e eventual anexo de tratamento de dados se aplicável; cancelamento/reembolso; cookies somente conforme inventário. Português claro, escopo correto, versão e datas reais quando aprovados, canais verdadeiros, direitos dos titulares, bases legais, segurança e retenção verificadas. Onde faltar informação: `[PENDENTE DE CONFIRMAÇÃO]` **nos arquivos internos de minuta e checklist**, nunca em uma página apresentada como documento jurídico em vigor. Antes de aprovação, configurar páginas jurídicas em modo de revisão/não publicação e `noindex` conforme apropriado; registrar que estão bloqueadas para lançamento.

A própria implementação do site precisa ser coerente com a privacidade descrita: não instalar tracking não essencial por padrão, não incorporar pixels sem decisão, não criar formulários que a política não cobre. **Uma página jurídica correta não garante ausência de processo**; é preciso revisão jurídica humana e cumprimento efetivo das práticas.

## 8. Requisitos técnicos e testes

- Layout consistente e caprichado em **mobile 320–767 px**, tablet 768–1023 px e desktop ≥1024 px, inclusive menu, CTA, demo e comparativo de planos.
- Tipografia legível, sem overflow, botões com áreas de toque, acessibilidade com foco visível, navegação por teclado, headings semânticos, labels, alt real, contraste e redução de movimento.
- Imagens com dimensões reservadas, formatos responsivos AVIF/WebP quando adequados, poster antes de vídeo, carregamento prioritário do hero e lazy-load do restante; não gerar dezenas de arquivos enormes servidos integralmente no celular.
- SEO: metadata por rota, título e descrição reais, canonical somente após domínio confirmado, Open Graph com O01–O05, favicon, sitemap, robots, dados estruturados apenas quando verificáveis. Páginas jurídicas em rascunho não devem ser indexadas como versão aprovada.
- Segurança: não expor credenciais, segredos, dados pessoais reais nem URLs de QA sensíveis; demo local sem chamadas mutáveis a sistemas externos; sem coleta oculta de dados.
- Testes: lint, TypeScript, build, verificação de rotas, links WhatsApp/mailto, ausência de formulários e `/obrigado`, funcionamento dos carrinhos/opcionais/cálculos da demo, reinício e status, sem requests de pedido real, teclado/touch, `prefers-reduced-motion`, largura mobile, alt/contraste, imagens, console erros. Medir ou documentar Core Web Vitals/Lighthouse quando possível; não afirmar benchmark não executado.
- Se o browser falhar por permissões de ambiente, registrar erro com evidência, continuar com verificações de código/build e deixar teste visual pendente. Não comprometer os bancos do TapServe para “consertar” o ambiente de testes.

## 9. Critério de conclusão e saída obrigatória

Não pare ao concluir a primeira página, um protótipo ou a análise. O objetivo é uma **implementação integrada de todas as páginas**, com motion refinado, demo funcional, imagens produzidas ou pendências explícitas, e documentação. Concluir automaticamente as fases possíveis antes de encerrar. **Não publicar nem representar como aprovado juridicamente.**

No relatório final, apresentar:
1. páginas implementadas e rotas operantes;
2. assets gerados/capturados/compostos, com caminhos e IDs, e os que faltam;
3. como a imagem crua da plaquinha foi aplicada sem alterar a arte;
4. animações e mouse triggers efetivamente implementados, confirmando que aproximação NFC foi adiada;
5. demo clicável: fluxos testados, isolamento de pedidos reais e evidências;
6. botões WhatsApp/e-mail, confirmação de **nenhum formulário**;
7. documentos legais produzidos como rascunho, evidências encontradas, fontes oficiais consultadas, lacunas e bloqueios de publicação;
8. testes rodados, resultados, limitações de ambiente e instruções para iniciar localmente;
9. checklist curto do que o proprietário precisa enviar/aprovar antes do lançamento.

**Comece agora lendo os arquivos, siga a sequência integral e execute, não apenas descreva como faria.**
