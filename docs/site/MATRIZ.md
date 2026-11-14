# Matriz de páginas e experiência

Todas as páginas ficam em `site/`; não substituem `/` do app operacional.

| Rota | Conteúdo e interação | Material |
|---|---|---|
| / | H00–H12: hero, valor, acesso, mini demo, operação, explorador, placa, benefícios, segmentos, planos, FAQ, fecho | F01/F02, D01–D08, C01–C06 em DOM |
| /como-funciona | Jornada controlada por etapas, visão da equipe/cozinha, FAQ | Interfaces simuladas rotuladas |
| /funcionalidades | Cliente, mesas, pedidos, KDS, gestão, unidades/equipe, acesso | Explorador com tabs; sem relatórios não comprovados |
| /nfc-e-qr-code | Placa original, galeria/detalhes, NFC × QR, limitações e configuração | Original soberano, F02/F08/F10; F09 pendente; F11 não aplicável |
| /para-quem | Cinco cenários de uso, multiunidade e CTAs por segmento | F13–F17 |
| /planos | Essencial/Pro, limites compartilhados, simulador em centavos e FAQ | Tipografia e O04; valores de referência não aprovados |
| /demonstracao | Mesa, categorias, oito itens, regras de opcionais, carrinho, revisão, confirmação/status, atendimento, conta, reset, visões simuladas | D01–D08; sem APIs |
| /contato | Exatamente dois botões com ícones e contexto comercial | Links centralizados |
| /suporte | Dois botões, tópicos, FAQ e links legais | Sem tickets nem formulários |
| /duvidas | Busca local, grupos, deep links e accordions nativos | Sem telemetria |
| /sobre | Propósito e proposta do produto, sem biografia inventada | Fotografia ilustrativa rotulada |
| /privacidade | Estado de revisão sem minuta pública | Noindex, minutas internas |
| /termos | Estado de revisão, termos do site separados do SaaS | Noindex, minutas internas |
| /cancelamento | Estado de revisão e canais para solicitação | Noindex; sem condições inventadas |
| 404 | “Esta mesa não foi encontrada”, links de recuperação | 404.html estático |

`/cookies` não se aplica ao site sem cookies/storage/analytics. `/termos-assinatura` permanece minuta interna até decisão contratual. `/obrigado` não existe.

## Motion planejado

Entradas curtas em camadas; reveals via IntersectionObserver sem esconder conteúdo sem JS; transições CSS de interfaces; fluxo local cliente→KDS; galeria com zoom controlado e hotspots; foco/hover em botões; brilho/tilt discretos e resposta magnética apenas para ponteiro fino. Desativar motion por preferência do sistema e controle global. Sem scroll sequestrado, loop obrigatório, cursor personalizado ou aproximação NFC.

## Conferência da fase 1

Documentos obrigatórios lidos; fonte da placa inspecionada visualmente; nenhum manifesto importável/CSV adicional encontrado em `assets_source/`. Logos vetoriais existentes e três fotos do demo operacional encontrados; não confundir com screenshots. Dados legais e oferta comercial não comprovados permanecem bloqueios, não suposições.
