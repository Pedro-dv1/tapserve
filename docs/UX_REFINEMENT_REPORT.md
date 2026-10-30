# TapServe — refinamento de UX/UI

Implementação de 29/10/2026. As alterações estão no diretório de trabalho, sem commit ou publicação. Não foram adicionadas dependências nem migrações de dados.

## A. Alterações implementadas

- Proteção compartilhada dos formulários de catálogo, funcionários, pontos de atendimento, identidade visual, configurações, plataforma e galeria. A confirmação oferece descartar, continuar e salvar antes de concluir a saída.
- Comparação dos valores reais, incluindo números equivalentes, checkboxes, arquivos, remoções de mídia e conjuntos de associações. Restaurar os valores originais elimina a pendência. Filtros auxiliares de seleção não são considerados dados editados.
- Confirmação personalizada para fechar, Escape, cancelar, links internos e troca das seções de dados/QR. A saída pelo navegador usa `beforeunload` apenas com pendências. Os modais existentes não permitem fechamento por clique no backdrop; esse comportamento foi preservado.
- Salvamento usa as validações e os handlers existentes. A saída aguarda a confirmação do servidor; falhas preservam campos e arquivos. Formulários múltiplos são salvos em sequência. Pedidos manuais com rascunho persistido e vínculos operacionais instantâneos não recebem a proteção indiscriminadamente.
- Busca com sugestões no gerenciamento do catálogo, seletores pesquisáveis e pedido manual. Há navegação por setas, Enter, Escape, mouse/toque e uma ação explícita de busca completa. Os resultados vêm das consultas já existentes, sem uma segunda requisição para sugestões.
- Busca no servidor normaliza espaços, caixa e acentos do português, prioriza correspondência exata/prefixo e filtra antes da paginação. Mantém os escopos, disponibilidade e permissões existentes.
- Cabeçalho dos editores acompanha a superfície do modal. O estilo próprio do botão de fechar foi preservado.
- Ações de chamados organizadas em um grupo com espaçamento, altura consistente e empilhamento em telas pequenas. Os seletores têm largura limitada e responsiva.
- Removidos os controles exclusivos de atualização de listas, pedidos, chamados, produção, mesas, fotos, vínculos, configurações e logo. Preservados salvar, atualizar cadastros, consultar comprovantes e recuperação após falha de renderização.
- Mantidos eventos WebSocket, deduplicação e recuperação por snapshot. Consultas operacionais usam fallback de 30 segundos, retorno de foco/conexão e atualização após mutações. Atualizações administrativas periódicas aguardam o término das edições pendentes.
- Removida a apresentação do nome da unidade nos headers superiores. A unidade continua nas configurações, contexto, permissões e identificação lateral.
- Removido “Todas as mesas” dos chamados filtrados por mesa, preservando a navegação global de chamados e o filtro `point`.
- Mensagens específicas para chamados, etapas dos pedidos, funcionários, catálogo, pontos, configurações, logo, setores e fotos, usando os componentes de feedback existentes.
- Indicador `!` em Pedidos nas navegações operacional e administrativa correspondentes, sem unificar os painéis. Considera itens READY que o funcionário pode assumir e DELIVERING sob sua responsabilidade. Abrir pedidos não limpa o alerta; concluir a entrega o remove quando não há outras pendências.
- Destaques fotográficos dos mais pedidos com nome, descrição, preço, botão Experimentar e vídeo sob demanda. A abertura segue para o produto existente, preservando opções, adicionais e carrinho. A seção é ocultada sem vendas elegíveis com fotografia.

## B. Principais arquivos

| Arquivos | Responsabilidade |
| --- | --- |
| `frontend/src/lib/formChanges.ts`, `usePendingChanges.ts` | Comparação dos formulários, coordenação do salvamento e proteção de saída. |
| `frontend/src/components/Modal.tsx`, `PendingChanges.tsx` | Integração do editor e aviso compacto em popover. |
| `frontend/src/components/SearchCombobox.tsx` | Sugestões acessíveis e busca explícita. |
| `frontend/src/features/staff/CatalogManagement.tsx`, `ManualOrder.tsx` | Busca integrada ao catálogo e aos fluxos autorizados. |
| `backend/apps/catalog/search.py`, `views.py` | Busca paginada, ordenação e produtos populares. |
| `backend/apps/orders/views.py` | Filtro de entregas que requerem atenção, com escopo e permissões do servidor. |
| `frontend/src/features/staff/OrderAttention.tsx`, `StaffScreen.tsx`, layouts e `MobileNavigation.tsx` | Consulta compartilhada e indicador na navegação. |
| `frontend/src/lib/useAutoRefresh.ts`, telas operacionais e administrativas | Fallback, foco/reconexão e preservação de formulários. |
| `frontend/src/lib/actionMessages.ts`, `ServiceRequests.tsx`, `Operation.tsx` | Mensagens por ação e ajustes dos chamados. |
| `frontend/src/features/staff/ProductPhotos.tsx` e demais editores | Preservação dos campos e integração da confirmação de sucesso. |
| `frontend/src/features/customer/MenuBrowser.tsx` | Destaques populares integrados ao produto e à navegação atual. |
| `frontend/src/design-system/base.css`, `staff.css`, `customer.css` | Superfícies, ações, sugestões, badge, safe areas e destaque fotográfico. |
| `frontend/tests/form-changes.test.mjs`, `ux-harness.tsx`, `ux-refinement.mjs` | Regressões de comparação/salvamento e roteiro automatizado para navegador. |
| `backend/tests/test_ux_refinement.py` e regressões de catálogo/entrega | Persistência real, busca, paginação, popularidade, isolamento e entregas. |

## C. Decisões técnicas

Os formulários existentes são majoritariamente não controlados. A proteção compartilha snapshots dos controles e compara os valores, em vez de assumir que qualquer evento significa alteração. Campos de estado que não eram submetidos diretamente, como remoções de mídia e permissões, passam a ter representação explícita. Seletores assíncronos declaram o valor inicial para evitar falsos avisos durante o carregamento.

O salvamento continua nos handlers atuais. Eles comunicam sucesso ou falha após a resposta do servidor. O coordenador respeita validação nativa, bloqueios de envio e confirmação de ações sensíveis. Na galeria, atualizações confirmadas alteram somente o registro correspondente e preservam outros formulários editados.

O combobox reutiliza a consulta paginada que já alimenta a tela. Debounce de 200–250 ms e AbortController preservam a ordem das respostas. O backend usa parâmetros do ORM, normalização por LOWER/TRANSLATE do PostgreSQL e ordenação por relevância sobre o queryset previamente autorizado.

O alerta usa o endpoint existente de entregas com o filtro adicional `attention=true`. O filtro mantém somente ações permitidas ao funcionário, considera todas as páginas pela contagem e retorna no máximo um item para reduzir o payload. O parâmetro é opcional e mantém os consumidores existentes compatíveis.

A apresentação do cardápio recebeu o campo adicional `presentation.popular`. Os campos anteriores foram preservados. A popularidade reutiliza a agregação existente, exclui CANCELLED/REJECTED e restringe explicitamente a unidade. As consultas acontecem no carregamento/invalidação, nunca durante a renderização de React.

## D. Histórico do cardápio

`git log --all` contém somente `95bdc12` (commit inicial), sem uma revisão Git anterior recuperável. Também foi localizada a cópia local `.local/v2-before/`. Nela, `MenuBrowser.tsx` e `customer.css` continham o banner com fotografia de fundo, degradê, título sobreposto e botão Experimentar.

Esses elementos visuais foram recuperados seletivamente e adaptados à seleção real de produtos populares. A cópia antiga escolhia o primeiro produto com imagem; essa seleção não foi reintroduzida. O destaque manual editorial atual, categorias, busca, vídeos, galeria, participantes e carrinho foram mantidos. Nenhum checkout de arquivos antigos foi realizado.

## E. Validação

| Verificação | Resultado |
| --- | --- |
| `npm.cmd test` | 51 testes passaram; nenhuma falha na última execução. |
| Suíte ampliada Django/PostgreSQL | 38 testes passaram. |
| Regressões adicionais de atenção, múltiplos itens e escopo | 6 cenários aprovados nas reexecuções; o teste de queries passou após corrigir a ordem de leitura da captura. Essas repetições não são somadas aos 38 testes distintos. |
| `npm.cmd run build` | TypeScript e bundle de produção passaram. |
| `npm.cmd run lint` | Passou. |
| Ruff nos arquivos Python alterados | Passou. |
| Mypy nos três arquivos de implementação Python alterados | Passou. |
| `makemigrations --check --dry-run --settings=config.settings.test` | Nenhuma migração pendente. |
| `git diff --check` | Sem erros. |
| `node tests/ux-refinement.mjs` | Não executou os cenários: Chrome bloqueado pelo ambiente com `spawn EPERM`. |
| Navegador alternativo do ambiente | Falhou ao inicializar: `failed to write kernel assets`. |

A suíte ampliada usou os arquivos `test_ux_refinement.py`, `test_catalog.py`, `test_operational_redesign.py`, `test_customer_ui_contract.py`, `test_v2_menu.py`, `test_orders.py`, `test_service_requests.py`, `test_production.py`, `test_realtime.py`, `test_http_flow.py` e `test_access.py`. O banco dos testes usa um schema PostgreSQL exclusivo criado pelo conftest; não utiliza o schema operacional para os cadastros de teste.

As regressões novas cobrem valores restaurados, números equivalentes, arquivos, associações, validação, falha/sucesso assíncrono, mensagens, busca sem acentos, paginação além da primeira página, catálogo permitido, cancelamentos/recusas, disponibilidade e alerta até a entrega efetiva. A suíte existente cobre preços, adicionais, carrinho, autenticação, eventos, deduplicação e reconexão.

Houve falhas intermediárias nos testes adicionados: atualização da expectativa do contrato de apresentação, disponibilização da fixture de mídia, tentativa inválida de alterar um item já terminal e leitura da captura de queries após outra requisição. Os testes foram corrigidos para respeitar os contratos e a imutabilidade do domínio; nenhuma proteção de produção foi removida.

## F. Pendências reais

A validação visual e os cenários completos de interação em navegador permanecem pendentes pelo bloqueio descrito acima. Não foram comprovados neste ambiente os tamanhos efetivamente renderizados, o teclado virtual, a posição do popover sob safe areas ou a execução ponta a ponta dos cliques de confirmação e sugestões.

O roteiro `frontend/tests/ux-refinement.mjs` está preparado para 320, 390, 768 e 1440 px, incluindo comparação de altura/espaçamento dos botões, superfície dos headers, preservação do botão de fechar, confirmação de saída e seleção de sugestões. Ele testa os componentes compartilhados com fixtures de teste e não substitui uma homologação com usuários autenticados.

Por essa razão, o refinamento não deve ser considerado integralmente homologado apenas pelos testes de código e pelo build aprovados.
