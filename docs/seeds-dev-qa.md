# Seeds DEV e QA — execução real em 04/11/2026

## Resultado

Os dois bancos foram autenticados, migrados e populados. O seed foi executado e repetido em cada banco. A segunda execução e uma repetição final criaram zero registros e preservaram contagens e hashes SHA-256 de todas as tabelas públicas, inclusive históricos, hashes de credenciais, tokens cifrados, eventos e registros idempotentes.

**Dados e backend validados; frontend ainda não homologado neste contexto do Windows.** O Vite continua falhando com `spawn EPERM` ao executar o auxiliar `net use` em `windowsSafeRealPathSync`. Não se serviu um bundle antigo como prova, não se alteraram dependências/ACLs e não se desativou segurança. Execute os launchers em um terminal normal do operador para concluir o teste da interface e do proxy.

| Configuração | DEV | QA persistente |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432`, versão 17.11 | `127.0.0.1:5432`, versão 17.11 |
| Banco | `tapserve_dev` | `tapserve_qa` |
| Role/proprietário | `tapserve_dev_user` | `tapserve_qa_user` |
| Settings | `config.settings.dev` | `config.settings.qa` |
| Backend | `http://127.0.0.1:8004` | `http://127.0.0.1:8003` |
| Frontend | `http://127.0.0.1:5177` | `http://127.0.0.1:5176` |
| Env backend | `backend/.env.development.local` | `backend/.env.qa.local` |
| Env frontend | `frontend/.env.development.local` | `frontend/.env.qa.local` |

As duas roles têm LOGIN, não têm SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS e não possuem memberships. O CONNECT via PUBLIC e os grants cruzados foram removidos nos dois bancos. A tentativa real DEV→QA e QA→DEV falhou, com reconfirmação de conexão ao próprio banco. Nenhuma senha PostgreSQL foi alterada. O isolamento é lógico: ambos compartilham processo, recursos e administração da mesma instância. Nenhum banco de produção, de terceiros ou laboratório antigo foi acessado nesta execução.

Foram aplicadas **58 migrações existentes por ambiente**, incluindo MFA, DeviceAdmission, recebimentos externos e ciclo de vida de sessões. Nenhuma migração foi editada ou criada. Django check e verificação de migrações passaram nos dois destinos.

## Quantidades reais

| Recurso | DEV | QA |
| --- | ---: | ---: |
| Empresas | 2 | 2 |
| Unidades | 3 | 3 |
| Usuários de senha | 7 | 7 |
| Vínculos administrativos OWNER/ADMIN/MANAGER | 7 | 7 |
| Funcionários, incluindo vínculos administrativos | 23 | 23 |
| Funcionários operacionais | 16 | 16 |
| Mesas, incluindo Mesa Demo | 21 | 21 |
| Pontos totais, incluindo balcão e retirada | 23 | 23 |
| Cardápios | 3 | 3 |
| Categorias | 14 | 14 |
| Produtos | 56 | 56 |
| Grupos de opções / opções | 17 / 46 | 17 / 46 |
| Pedidos (OrderBatch) | 18 | 18 |
| Itens de pedidos | 22 | 22 |
| Sessões, abertas / encerradas | 14 / 2 | 14 / 2 |
| Chamados | 11 | 11 |
| Recebimentos externos, incluindo reversão | 6 | 6 |
| Produtos com imagem local | 9 | 9 |
| Admissões geradas por operações reais | 21 | 21 |
| Superusuários Django criados | 0 | 0 |

Os sete vínculos administrativos são três de proprietários (o proprietário A atua em duas unidades), um ADMIN e três MANAGER. Há seis usuários administrativos de tenant distintos e um operador de plataforma separado, totalizando sete usuários de senha. Funcionários operacionais usam PIN individual.

Estados dos itens: 9 NEW, 1 ACCEPTED, 3 PREPARING, 1 READY, 7 DELIVERED e 1 CANCELLED. Chamados: 4 OPEN, 3 ASSIGNED, 3 RESOLVED e 1 CANCELLED. Os registros externos têm 3 lançamentos MONEY, 2 CARD e 1 PIX; um MONEY é reversão do lançamento anterior. Os totais consideram a reversão corretamente, sem duplicar dinheiro declarado.

## Empresas, unidades e contas

Substitua `<env>` por `dev` ou `qa` nos códigos. Os nomes visíveis são fictícios e os registros são independentes entre bancos.

| Empresa | Código | Unidades |
| --- | --- | --- |
| TapServe Demo | `<env>-tapserve-demo` | `centro`, `shopping` |
| Restaurante Horizonte Demo | `<env>-horizonte-demo` | `principal` |

| Conta de senha | Papel e escopo |
| --- | --- |
| `<env>-owner-a` | OWNER da empresa A, Centro e Shopping |
| `<env>-owner-b` | OWNER da empresa B, Principal |
| `<env>-admin` | ADMIN do Centro |
| `<env>-manager` | MANAGER do Centro, Gerente 01 |
| `<env>-manager-shopping` | MANAGER do Shopping |
| `<env>-manager-horizonte` | MANAGER da Principal/Horizonte |
| `<env>-platform` | PlatformOperator, realm de plataforma, sem membership de tenant implícita |

Cada unidade tem `demo-waiter`, `demo-kitchen`, `demo-bar`, `demo-cashier` e `demo-limited`, com credenciais próprias por unidade. O Centro tem ainda `demo-waiter-2` (Atendente 02). O atendente restrito recebe somente VIEW_OPERATION. KITCHEN e BAR têm atribuições dos seus setores e não recebem VIEW_ALL_TABLES. Caixa recebe os grants reais de recebimento/encerramento; atendentes recebem aprovação de dispositivos e chamados, sem permissões gerenciais indiscriminadas. Gerentes e proprietários usam os templates reais, sem promoção a superusuário Django ou PostgreSQL.

### Credenciais e primeiro acesso

Senhas e PINs foram gerados por aleatoriedade segura e armazenados no banco somente como hashes. As credenciais iniciais ficam em `.local/environments/<env>/demo-credentials.enc`, cifradas pela chave local existente do ambiente. Nenhuma senha, PIN, recovery code ou token completo faz parte desta documentação, do código ou dos relatórios.

Abra um terminal interativo local do operador, sem transcript, gravação ou redirecionamento:

```powershell
.\backend\.venv\Scripts\python.exe scripts/local_env.py credentials --env dev
.\backend\.venv\Scripts\python.exe scripts/local_env.py credentials --env qa
```

O comando recusa stdout redirecionado e exige confirmação local antes de mostrar os segredos. Não o execute por um agente que capture sua saída. As chaves `owner-a`, `owner-b`, `admin`, `manager`, `manager-shopping`, `manager-horizonte` e `platform` correspondem às contas acima. Chaves como `a-centro:waiter` indicam empresa, unidade e funcionário. Transfira os valores para seu gerenciador de senhas. O cofre guarda credenciais iniciais; alterações posteriores feitas pelo operador não são revertidas pelo seed.

Na interface `/staff/login`, selecione login por senha para as contas administrativas e informe empresa, unidade e usuário corretos. Conclua o onboarding MFA com seu aplicativo autenticador e guarde os códigos de recuperação em local privado. A validação desta execução usou o fluxo real de MFA, mas **reverteu a matrícula de teste**: nenhuma conta foi entregue com fator desconhecido para o operador. MFA continua obrigatório. Para a plataforma, use `/platform`, com conta e realm próprios.

Funcionários operacionais entram por código e PIN da respectiva empresa/unidade. Não compartilhe o PIN de outro funcionário ou outro ambiente. O PIN continua restrito à rede configurada; os testes de acesso proibido não alteraram grants.

## Mesas e cenários

O Centro tem Mesas 01–10, Mesa 11 com nome **Mesa Demo**, Balcão 01 e Retirada 01. Shopping e Principal têm Mesas 01–05, com IDs/tokens próprios. Retirada é um tipo de ServicePoint existente; não foi habilitada uma funcionalidade nova de retirada pública ou venda externa.

| Mesa do Centro | Estado inicial preparado |
| --- | --- |
| 01 | Disponível, sem ocupação |
| 02 | Ocupada, pedidos novos, vários itens/quantidades, adicionais e um item cancelado com motivo |
| 03 | Ocupada, itens PREPARING e chamado de limpeza ASSIGNED |
| 04 | Ocupada, itens READY e chamado de talheres RESOLVED |
| 05 | Itens DELIVERED; recebimento declarado, reversão e lançamento corrigido, saldo zero |
| 06 | CHECK_REQUESTED, itens entregues e conta solicitada |
| 07 | Itens entregues, recebimento PIX parcial, saldo remanescente coerente |
| 08 | Dois participantes, mais de um dispositivo/pedido, itens NEW e ACCEPTED; chamado de guardanapo CANCELLED |
| 09 | Ocupada, chamado ATTENDANT OPEN e solicitação sintética de admissão |
| 10 | Disponível após duas ocupações independentes, entregues, quitadas e encerradas pelos serviços reais |
| 11 — Mesa Demo | Disponível, sem sessão, pedidos ou dispositivo pré-autorizado pelo seed |

Shopping e Principal têm Mesa 02 com pedidos novos, 03 em preparo, 04 com entregues, e 01/05 disponíveis. Os seus chamados e cardápios pertencem exclusivamente à unidade correspondente.

Há três admissões sintéticas pendentes no momento da criação e admissões aprovadas/revogadas produzidas pelas operações reais. Solicitações expiram normalmente em dez minutos e capacidades de dispositivo em doze horas. Os seeds **não prolongam autorizações nem recriam cenários já utilizados**. Se a solicitação preparada já tiver expirado, solicite um novo acesso real. Itens antigos também respeitam a janela real de edição do cliente.

### Abrir a Mesa Demo

1. Entre como proprietário/administrador do Centro e conclua MFA.
2. Abra Pontos de atendimento e localize **Mesa 11 · Mesa Demo**.
3. Em Editar → QR Code e NFC, obtenha a URL pelo endpoint autorizado ou abra o acesso.
4. No navegador do cliente, solicite admissão; no atendimento, confira o código exibido e aprove o dispositivo.
5. Confirme o primeiro pedido para abrir uma sessão. Teste participantes, produção, chamados, recebimentos externos e encerramento pelos fluxos normais.

Não existe URL pública fixa documentada. Tokens são aleatórios, cifrados e preservados entre seeds. Uma tag NFC física não é necessária para demonstrar o acesso pelo link. Escrita/lock físico de NFC ainda exige hardware compatível e não foi testado. Se a Mesa Demo já foi utilizada pelo operador, o seed preserva os seus dados; use uma nova mesa ou laboratório descartável para repetir uma apresentação do zero.

## Cardápios

Centro e Shopping têm cada um os 23 produtos solicitados: cinco hambúrgueres, quatro pizzas, quatro porções, seis bebidas e quatro sobremesas, com preços de referência do pedido. Horizonte tem dez produtos próprios de pratos, lanches, bebidas e sobremesas, sem compartilhar registros de produtos ou opções com a empresa A.

Há descrições, categorias ordenadas, produto em destaque, Pudim indisponível, adicionais opcionais múltiplos e escolhas obrigatórias. Ponto da carne tem Malpassado/Ao ponto/Bem-passado; adicionais têm Bacon +5, Queijo +4, Ovo +3 e Hambúrguer extra +9. Molhos são opcionais; gelo e açúcar são escolhas únicas independentes no suco. Pizzas compartilham o grupo de tamanho somente dentro da mesma unidade. As combinações mínimas/máximas são validadas pelos serviços reais de cotação.

As três imagens próprias de `assets/demo/` foram recodificadas e importadas pelo validador existente, em armazenamento separado por ambiente. Não foram baixadas imagens externas. Não há vídeo autorizado local para importar. Não foi inventado campo de ordenação em Product: a categoria usa `position`, e a aplicação conserva sua ordenação real dos produtos.

Não existem modelos implementados de taxas, gorjetas ou cupons para popular. Não foi adicionado gateway, cartão real ou integração bancária. ExternalReceipt continua representando somente uma declaração de recebimento externo por funcionário.

## Comandos executados e repetição segura

Na raiz do projeto, usando o Python já instalado no ambiente virtual, estes são os comandos equivalentes para repetir a preparação. Os quatro seeds registrados nas evidências foram executados por `manage.py seed_environment --env dev|qa`, com o mesmo ambiente validado pelo runner:

```powershell
$python = ".\backend\.venv\Scripts\python.exe"
& $python scripts/local_env.py harden --env dev
& $python scripts/local_env.py harden --env qa
& $python scripts/local_env.py migrate --env dev
& $python scripts/local_env.py migrate --env qa
& $python scripts/local_env.py check --env dev
& $python scripts/local_env.py check --env qa
& $python scripts/local_env.py dry-run --env dev
& $python scripts/local_env.py seed --env dev
& $python scripts/local_env.py seed --env dev
& $python scripts/local_env.py seed --env qa
& $python scripts/local_env.py seed --env qa
& $python scripts/local_env.py verify --env dev
& $python scripts/local_env.py verify --env qa
```

O dry-run DEV percorreu as operações reais e reverteu os registros, sem criar cofre/manifesto/mídia. Também foi feita verificação adicional das contas administrativas e KDS nos dois ambientes. Execute os comandos individualmente e pare se houver código de saída diferente de zero. A entrada direta equivalente é `seed_environment --env <dev|qa>`, com `TAPSERVE_ENV` e settings correspondentes; o runner evita misturar configuração herdada.

O seed verifica settings, nome/usuário efetivos da conexão, IP loopback, porta, owner, ausência de atributos administrativos/memberships e CONNECT cruzado negado. Usa transação e trava advisory. Recusa colisões de identificadores reservados, mantém UUIDs estáveis no catálogo e reconhece pontos/funcionários/cenários pelo manifesto e pelos resultados idempotentes **realmente produzidos pelos serviços**. Renomear um produto não cria outro. Não redefine senha, PIN, permissões, tokens ou histórico. Não há `--reset`.

O manifesto `.local/environments/<env>/seed-manifest.json` contém somente referências de controle, sem capacidades ou segredos. Não são gravados eventos de auditoria falsos para marcar seeds. Auditoria, DomainEvent, snapshots, ItemStatusEvent e registros idempotentes existentes são os efeitos normais das operações executadas. Se o manifesto faltar depois de criar dados, o comando exige restaurar o controle pelo backup ou diagnóstico das referências reais; não adota contas somente pelo nome. Se uma referência registrada apontar para entidade ausente ou outro escopo, o comando falha em vez de substituí-la silenciosamente. Uma falha de escrita do manifesto após o commit não apaga dados já criados.

Na saída, `total` são as contagens atuais; `created` são os acréscimos; `reused` são registros já presentes/preservados nas unidades; `ignored_scenarios` são cenários completos cuja evolução foi mantida. Na segunda execução em ambos os bancos: todos os `created` ficaram em zero e 15 cenários foram preservados.

Guarde `.env`, cofre e manifesto em backup local protegido. O seed é aditivo e não restaura estados consumidos. Para começar novamente do zero, provisione **outro banco descartável identificado**, com role própria, pelo procedimento de testes em [ambientes-locais.md](ambientes-locais.md). A fixture `test_environment_seed.py` monta e reverte o conjunto no laboratório descartável. Nunca use pytest destrutivo, restore com limpeza ou DROP/TRUNCATE no QA persistente. Não se enfraquece o guarda de destino para aceitar um banco arbitrário.

## Inicialização e verificações restantes

Em PowerShell normal do operador, em terminais separados:

```powershell
.\backend\.venv\Scripts\python.exe scripts/dev.py --env dev
.\backend\.venv\Scripts\python.exe scripts/dev.py --env qa
```

Após os dois frontends estarem ativos, execute `scripts/local_env.py smoke` para certificar o proxy HTTP/WS e a coexistência dos cookies. Para o teste de navegador existente, configure `TAPSERVE_E2E_ORIGIN` com a origem DEV e depois QA e execute `npm.cmd --prefix frontend run test:e2e`. Os cookies têm nomes por ambiente e o armazenamento do frontend é isolado por origem/porta. Não troque URLs de backend manualmente nem misture `localhost` e `127.0.0.1` durante o mesmo fluxo.

Passaram nesta execução: 59 testes frontend, sete testes de configuração sem banco, TypeScript, ESLint, Ruff, Mypy, Django check/migrações, seed e repetição em DEV/QA, fluxos HTTP transacionais incluindo todos os perfis administrativos/MFA e KDS, saúde HTTP real, login/logout real e snapshot inicial de WebSocket direto. Um mesmo cookie jar manteve os dois logins independentes; sair do DEV preservou o login QA. Um token real da Mesa Demo DEV foi rejeitado pelo backend QA com HTTP 404, sem imprimir o token. Foram verificadas ausência de itens fora de escopo, de dispositivos não revogados em sessões encerradas e de marcadores artificiais na auditoria.

Não foi executada a suíte destrutiva PostgreSQL, por não haver um laboratório descartável provisionado com credencial administrativa autorizada nesta tarefa. Não foi feita campanha de pentest. A interface React e o proxy completo continuam pendentes do terminal Windows sem a falha de subprocesso do Vite. Isso impede declarar homologação completa do ambiente, apesar dos bancos e fluxos backend já operacionais.

Evidências locais sem segredos: `.local/environments/seed-run-20261104T131626Z/`, incluindo identidade inicial das conexões, estado Git, logs dos seeds iniciais e repetições finais, hashes por tabela, contagens reais, verificações HTTP e WebSockets. O build novo falhou no auxiliar Windows e não substituiu um artefato anterior por um resultado fictício.

Nenhum banco foi recriado ou apagado; nenhuma senha PostgreSQL foi redefinida. Não houve commit, push ou deploy. Os relatórios e scripts das auditorias anteriores foram preservados.
