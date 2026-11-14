# Entrega do site TapServe V3

**13/11/2026 — implementação local, não publicada.** Nove fases executadas até o limite verificável do ambiente, com pendências explícitas. Código em `site/`; sistema operacional, bancos, ambientes, credenciais e alterações anteriores preservados. Nenhuma ação real de pedido, atendimento, cobrança ou comunicação externa foi executada.

## Páginas

| Rota | Entrega |
|---|---|
| `/` | H00–H12: header, hero com placa original, faixa de valor, NFC/QR estático, mini demo, cliente→KDS, explorador, produto físico, benefícios, cinco segmentos, planos, FAQ e fecho |
| `/como-funciona` | Oito etapas controláveis da jornada, interface ilustrativa e operação/KDS, contexto de implantação e FAQ |
| `/funcionalidades` | Cliente, mesas/atendimento, pedidos, produção, gestão, unidades/equipe e acesso; quatro perspectivas em tabs |
| `/nfc-e-qr-code` | Galeria de original/composição/macro, zoom e hotspot, compatibilidade/limites, alternativa QR e configuração verificada |
| `/para-quem` | Restaurantes, hamburguerias, lanchonetes, bares, cafeterias; links por cenário e contexto multiunidade |
| `/planos` | Essencial/Pro, comparação, simulador em centavos, limites compartilhados e pacotes; aviso de referências não aprovadas |
| `/demonstracao` | Mesa fictícia, oito produtos, categorias, detalhes/opcionais/quantidade, carrinho editável, revisão, confirmação, estados, equipe/cozinha, chamados/conta e reset |
| `/contato` | Contexto comercial e exatamente dois botões com ícones: Enviar mensagem / Enviar e-mail |
| `/suporte` | Dois canais, tópicos e links para dúvidas/políticas, sem promessa de horário/SLA |
| `/duvidas` | Busca e categorias locais, accordions, deep links e estado vazio |
| `/sobre` | Proposta do produto, sem empresa/equipe/clientes/resultados inventados |
| `/privacidade` | Rota com estado de revisão, sem publicar minuta como política vigente |
| `/termos` | Estado de revisão, separado do contrato SaaS |
| `/cancelamento` | Condições em revisão e dois canais para solicitar informações; sem multa/prazo/reembolso inventados |
| `404.html` | “Esta mesa não foi encontrada”, recuperação e HTTP404 no preview |

`/cookies` não criado: inventário atual sem cookies/analytics/storage. `/termos-assinatura` somente minuta interna. `/obrigado` inexistente e testado como 404. Sem login real ou links de administração/QA sensíveis. Header sticky, menu mobile, footer Produto/Empresa/Ajuda/Legal, metadados individuais, favicon e HTML pré-renderizado. Canonical aguarda domínio; robots bloqueia indexação e sitemap fica vazio nesta prévia.

## Imagens e arte original

**19 imagens geradas por ferramenta real:** F01, F04–F07, F13–F18 e D01–D08. Masters em `site/assets/originals/generated/`; WebP responsivos em `site/public/assets/photography/` e `demo-cardapio/`. Prompts completos, procedência, revisão e caminhos em [IMAGE_PROMPTS.md](IMAGE_PROMPTS.md) e [GENERATED_ASSETS.json](GENERATED_ASSETS.json). Painel de conferência: [VISUAL_BOARD.jpg](VISUAL_BOARD.jpg).

**Composições:** F02/F12 sobre mesa gerada e F10 crop da área NFC, cinco capas O01–O05 em 1200×630, B01–B06 preservados/derivados e C01–C06 em DOM. V03/V04 em componentes. Script reproduzível `site/scripts/compose_assets.py`; nenhum QR escaneável falso. Capas sociais usam os pixels da marca na placa original, sem recriar o wordmark como tipografia.

A referência `assets_source/card/Plaquinha.png` é preta e vertical, com base acrílica, marca branca/âmbar e nenhum QR. Prevaleceu sobre a descrição antiga de card branco horizontal. A fonte foi copiada sem alteração; contorno recortado preserva pixels/arte e as proporções, depois escalado/combinado com o cenário. F02/F12 são montagens ilustrativas, não instalações fotografadas. Luz/escala/acrílico e variantes precisam de aprovação física/visual.

**Pendências:** S01–S20 reais (QA exige autenticação/MFA/admissão com escrita; não realizada); S19/relatórios não anunciado sem comprovação; F07 tem monitor vazio aguardando S13; F08/45° e F09/vista superior requerem fonte fiel; F11 não se aplica ao original sem QR. F03 opcional dispensado; V01 vídeo opcional substituído pelo poster/efeitos leves; V02 e M01–M03 adiados. Fonte Manrope não baixada por bloqueio de rede; fallback local, sem dependência remota quebrada. Todos os **70 IDs** têm estado, origem, arquivo quando existente, prioridade, licença e revisão em [ASSET_MANIFEST.md](ASSET_MANIFEST.md) / [manifesto JSON](TAPSERVE_ASSET_MANIFEST_V3.json).

## Motion e interação

Hero em camadas e parallax sutil progressivo em desktop, reveals via IntersectionObserver com conteúdo inicialmente legível, spotlight/tilt moderado para ponteiro fino, botões magnéticos discretos, hover/foco, tabs e transições de UI, controles de pedido→KDS, galeria com zoom/hotspot e menus/accordions. Layouts CSS para desktop/tablet/mobile, sem scroll-jacking ou cursor intrusivo; conteúdo da mini demo rola naturalmente.

`prefers-reduced-motion` e controle global desativam motion; não há vídeo automático nem loop obrigatório. **Aproximação do celular à tag NFC não foi implementada**, inclusive gatilhos/parciais. Registro futuro apenas em EXECUCAO/MATRIZ/manifesto. Os efeitos implementados ainda precisam de inspeção real no navegador, bloqueada neste ambiente.

## Demo e canais

`site/src/data/demo.ts` contém catálogo e reducer compartilhados pela Home e `/demonstracao`. Regras required/SINGLE/MULTIPLE/min/max, limites, IDs e quantidades validados; valores em centavos; edição/remoção/totais; confirmação única; estados Pedido recebido → Em preparo → Pronto → Entregue, controlados pelo visitante. Chamados/conta explicitamente simulados e reset sem persistência. Badge permanente: “Demonstração — nenhum pedido é enviado a um restaurante.”

Sem backend, API, credencial, pedido real, pagamento, rastreamento, cookies ou storage. Verificação do código, testes do motor e CSP `connect-src 'none'`; cliques/rede efetiva no navegador ainda pendentes. Contatos centralizados em `site/src/config/contact.ts`, destinos exatos fornecidos, mensagens WhatsApp comercial/suporte codificadas. Identificadores não aparecem como texto em Contato/Suporte. **Nenhum formulário ou mensagem de envio fictícia.** Não abri canais nem enviei mensagens.

## Jurídico e comercial

[LEGAL_AUDIT.md](LEGAL_AUDIT.md) contém 20 fluxos, campos reais, evidências arquivo/linha, finalidades/bases candidatas, papéis, terceiros, retenção e lacunas. Consultadas em 13/11/2026 fontes oficiais Câmara e ANPD para LGPD, CDC, Marco Civil, Decreto 7.962, agentes, cookies, incidentes, encarregado e transferências. URLs, pontos e limitações estão na auditoria: Planalto apresentou CAPTCHA e algumas páginas DOU retornaram 502; fontes oficiais alternativas foram usadas.

Cinco minutas **RASCUNHO — NÃO PUBLICAR**, sem vigência, em `docs/site/legal/`: Privacidade, Termos do site, Assinatura, Cancelamento e DPA. Fora de `public/`. Sem identidade jurídica, CNPJ, endereço, suboperadores, práticas de retenção, SLA ou cláusulas comerciais inventadas. Questões abertas somente internas, com `[PENDENTE DE CONFIRMAÇÃO]`.

Páginas legais mostram aviso de revisão; nenhuma minuta foi apresentada como vigente. `check:release` falha enquanto seis aprovações documentadas faltam. Todas as páginas noindex; isso não é controle de acesso e não autoriza upload manual. Planos exibem referências não vinculadas a contratação pelo site: Essencial R$159,90 / até5 unidades / 50 mesas totais; Pro R$229,90 / até10 / 80 mesas; +20 mesas R$59,90. Oferta, implantação e placas aguardam aprovação; não presumir diferenças de recursos.

## Testes e execução local

Lint, TypeScript, build, **10 testes** e smoke HTTP passaram. HTTP verificou 14 rotas/assets/srcsets/OG, quatro 404, POST405 e headers. **68 rasters** decodificados; contraste de sete pares de cores planas aprovado. Build principal ~290kB JS/~89kB gzip e ~51kB CSS/~11kB gzip; não são métricas Lighthouse. Graphify atualizado por AST, sem API/LLM, incluindo a nova demo. `.gitignore` recebeu somente a exceção necessária para rastrear `docs/site/`; alterações anteriores preservadas.

**Bloqueios:** CUA indisponível; Chrome headless com sandbox retornou `spawn EPERM`. Suíte completa criada em `site/tests/browser.mjs`, mas não executou cliques. QA visual responsivo, teclado/toque renderizados, hidratação/console, leitores de tela, Lighthouse e Core Web Vitals **não aprovados/não medidos**. Detalhes e evidências em [QA.md](QA.md).

```powershell
cd C:\Users\pedro\Desktop\tapserve\site
npm.cmd ci --ignore-scripts
npm.cmd run build
npm.cmd run preview
```

Abrir http://127.0.0.1:4321. Preview encerrado ao concluir a tarefa; iniciar novamente com o comando acima. Testes HTTP/browser em segundo terminal. Instruções completas, substituição de imagens e cuidados com publicação em [site/README.md](../../site/README.md).

## Antes do lançamento

Seguir [OWNER_CHECKLIST.md](OWNER_CHECKLIST.md): fornecedor/domínio/host, canais, oferta/contratos/cancelamento, modelo físico/direitos/capturas reais, inventário/práticas de dados/DPA/incidentes, revisão jurídica, QA visual e aprovação expressa para publicar. Registrar aprovador/data/evidência reais em `RELEASE_APPROVALS.json`. Nenhum teste técnico equivale a autorização de publicação ou revisão jurídica.
