# Anexo de tratamento de dados pessoais — minuta

**RASCUNHO — NÃO PUBLICAR / NÃO ASSINAR** · Versão 0.1 · Redação em 13/11/2026 · **Sem vigência**. Anexo proposto para revisão junto ao contrato SaaS. Base: LGPD, orientações ANPD e fatos documentados em `../LEGAL_AUDIT.md`. Não altera o sistema nem autoriza novos tratamentos.

## 1. Partes e papéis por finalidade

Fornecedor TapServe: **[PENDENTE DE CONFIRMAÇÃO: identificação jurídica, representante e contato]**. Estabelecimento contratante: **[PENDENTE DE CONFIRMAÇÃO: identificação e representante]**. Contrato principal: **[PENDENTE DE CONFIRMAÇÃO: referência/versão/data]**.

Este anexo deve disciplinar os tratamentos em que o estabelecimento decide finalidades/meios essenciais e o TapServe executa operações em seu nome. Não atribui papel universal: tratamentos próprios do fornecedor, como relacionamento contratual, obrigações próprias ou segurança com finalidade autônoma, precisam de análise e transparência separadas. **[PENDENTE DE CONFIRMAÇÃO: matriz final de controlador/operador por fluxo, inclusive auditoria]**.

## 2. Objeto, categorias e instruções

O objeto observado é o processamento necessário ao atendimento presencial e à organização operacional: mesa/sessão, participantes, pedidos/opcionais/preços/observações/status, chamados/conta, equipe/permissões, autenticação, produção e registros de recebimentos externos. Categorias de titulares possíveis: consumidores, funcionários, representantes e administradores. Dados técnicos de acesso e trilhas de auditoria podem ser relacionáveis a esses titulares.

**[PENDENTE DE CONFIRMAÇÃO: inventário aprovado com categorias, finalidades, bases, frequência, duração, destinatários, unidades abrangidas e operações permitidas]**. Não incluir dados pessoais da demo do site: a simulação usa dados fictícios em memória, sem backend.

As instruções devem ser documentadas, lícitas e limitadas ao escopo contratado. Mudanças materiais devem ser registradas e avaliadas antes de implementação. Se houver dúvida sobre legalidade/segurança da instrução, definir escalonamento e suspensão apenas da operação afetada quando necessária, com informação e revisão. **[PENDENTE DE CONFIRMAÇÃO: responsáveis e procedimento]**.

## 3. Deveres do estabelecimento e do fornecedor

O controlador deve definir finalidade/base adequada, informação aos titulares, necessidade do conteúdo inserido e permissões de sua equipe; deve fornecer instruções e atender direitos e obrigações sob sua competência. Esses deveres não eliminam as obrigações próprias do operador.

O operador deve tratar os dados dentro das instruções e da lei, restringir acesso a pessoas autorizadas, manter confidencialidade e não reutilizar conteúdo operacional para publicidade, venda, compartilhamento estranho ao contrato ou treinamento de IA sem fundamento e instrumento apropriados. Não delegar irrestritamente a terceiros nem conceder acesso geral a outra unidade/empresa.

**[PENDENTE DE CONFIRMAÇÃO: procedimentos de admissão/desligamento, compromissos de confidencialidade, treinamento, segregação, gestão de acesso e revisão de privilégios]**. A existência de controles no código não comprova todos esses processos na operação.

## 4. Dados sensíveis e menores

Observações livres podem conter alergias ou outras informações pessoais sensíveis. Nomes de participantes não oferecem garantia de maioridade. **[PENDENTE DE CONFIRMAÇÃO: fluxo real, necessidade, minimização, base do art. 11 quando aplicável, salvaguardas e análise do melhor interesse de crianças/adolescentes]**.

Não coletar dados sensíveis ou de menores por padrão sem finalidade e regime adequados. O anexo final deve definir instruções para conteúdo excessivo, acesso restrito e encaminhamento de solicitações, sem prometer mecanismo de detecção/remoção inexistente.

## 5. Segurança e evidências

O código possui mecanismos de autenticação, autorização, sessões/credenciais e eventos de auditoria. Uma descrição contratual de medidas deve refletir configuração e processos efetivos: **[PENDENTE DE CONFIRMAÇÃO: controles de produção, criptografia aplicável, acessos administrativos, monitoramento, gestão de vulnerabilidades, testes, backups/recuperação e continuidade]**.

O anexo não declara certificação, “LGPD 100%”, ausência de incidentes ou SLA. Evidências podem ser fornecidas de forma proporcional e segura, preservando segredos, dados de terceiros e integridade do serviço. **[PENDENTE DE CONFIRMAÇÃO: rotina de cooperação/auditoria, responsáveis, periodicidade, escopo e forma de acesso às evidências]**. Não conceder auditoria irrestrita a produção ou credenciais.

## 6. Suboperadores e transferências internacionais

Identificar cada fornecedor que receberá/acessará dados: **[PENDENTE DE CONFIRMAÇÃO: nome, serviço, categorias, operações, localização, contrato e garantias]**. Definir mecanismo de autorização e informação de alterações compatível com o arranjo real. Contratar obrigações adequadas de proteção e confidencialidade e manter responsabilidade conforme lei/contrato, sem terceirização como exoneração automática.

Se houver transferência internacional, documentar origem/destino, base legal e mecanismo válido da LGPD/regulamentação ANPD, inclusive cláusulas-padrão quando aplicáveis. **[PENDENTE DE CONFIRMAÇÃO: países, transferências posteriores, instrumentos e transparência]**. Não afirmar armazenamento exclusivo no Brasil. Adequação reconhecida para determinado destino não dispensa a análise do fluxo efetivo.

## 7. Direitos dos titulares e solicitações de autoridades

O operador deve auxiliar o controlador com informações e ações tecnicamente disponíveis necessárias ao atendimento de direitos. Solicitação recebida diretamente deve ser registrada e encaminhada ao responsável competente, observando a verificação proporcional de identidade e a segurança do envio. **[PENDENTE DE CONFIRMAÇÃO: canais, responsáveis, prazos internos compatíveis com prazos legais, registros e formas de cooperação]**.

Pedidos de autoridades devem ser avaliados quanto a competência, fundamento, escopo e sigilo; informar a outra parte quando permitido e fornecer apenas o necessário juridicamente exigido. **[PENDENTE DE CONFIRMAÇÃO: procedimento e responsáveis]**. Não declarar atendimento automático de toda requisição nem oposição absoluta a determinações válidas.

## 8. Incidentes

Definir detecção, contenção, avaliação, preservação de evidências e comunicação segura ao controlador, incluindo natureza, dados/titulares afetados, riscos, medidas e atualizações quando conhecidos. **[PENDENTE DE CONFIRMAÇÃO: canal urgente, responsáveis, critério de ciência, prazo contratual de aviso e continuidade]**.

O controlador deve avaliar comunicação à ANPD/titulares conforme risco/dano relevante e regulamentação vigente. A regra geral de três dias úteis da Res. 15/2024 e eventuais regimes aplicáveis precisam ser respeitados; não usar esse prazo como atraso padrão de aviso do operador. Não assumir dispensa ou prazo diferenciado de pequeno porte sem enquadramento comprovado.

## 9. Retenção, término e devolução

Inventariar retenção por categoria, finalidade e obrigação. **[PENDENTE DE CONFIRMAÇÃO: tabela efetiva, descarte e acesso]**. A rotina técnica observada é opt-in, exige referência de política aprovada e preserva histórico operacional/auditoria/equipe/mídia; não é comprovação de política global de eliminação.

Ao término, definir devolução/exportação e eliminação ou conservação permitida sob instruções lícitas, com identificação do que permanece, fundamento, limitação de acesso e prazo. **[PENDENTE DE CONFIRMAÇÃO: formato, canal seguro, prazo, processo executável, backups/expiração, registros e evidência de conclusão]**. Não prometer exclusão imediata de toda cópia nem manter dados indefinidamente sem justificativa.

## 10. Responsabilidades, revisão e aceite

Cada parte responde pelas obrigações que lhe cabem, conforme conduta, lei e contrato, sem renúncia genérica de direitos ou exclusão total de responsabilidade. **[PENDENTE DE CONFIRMAÇÃO: análise jurídica dos limites, cooperação em demandas e relação com o contrato principal]**.

A assinatura deste anexo exige inventário preenchido, aprovadores, versão, data real e prova de aceite/entrega. Alterações em finalidade, suboperadores, localização ou escopo precisam de revisão. **[PENDENTE DE CONFIRMAÇÃO: processo e responsáveis]**. Manter fora da distribuição pública enquanto esses pontos estiverem abertos.
