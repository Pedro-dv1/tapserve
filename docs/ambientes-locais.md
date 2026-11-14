# Ambientes locais TapServe — DEV e QA

## Estado atual — 04/11/2026

Os dois bancos foram autenticados, receberam as 58 migrações existentes e estão populados. O seed foi executado duas vezes em cada banco, com zero acréscimos e hashes de todas as tabelas públicas preservados na segunda execução. As senhas PostgreSQL fornecidas pelo operador não foram alteradas.

**Backend e dados validados; interface/proxy ainda pendentes neste contexto do Windows.** A execução atual do Vite falha com `spawn EPERM` no auxiliar `net use`. Não há homologação completa da interface ou do laboratório de pentest. Contagens, contas, cenários, primeiro acesso e evidências reais estão em [seeds-dev-qa.md](seeds-dev-qa.md).

| Recurso | DEV | QA persistente |
| --- | --- | --- |
| Banco | `tapserve_dev` | `tapserve_qa` |
| Role/proprietário | `tapserve_dev_user` | `tapserve_qa_user` |
| Backend | `127.0.0.1:8004` | `127.0.0.1:8003` |
| Frontend | `http://127.0.0.1:5177` | `http://127.0.0.1:5176` |
| Settings | `config.settings.dev` | `config.settings.qa` |
| Backend env | `backend/.env.development.local` | `backend/.env.qa.local` |
| Frontend env | `frontend/.env.development.local` | `frontend/.env.qa.local` |
| DEBUG | habilitado | desabilitado |

A instância identificada é PostgreSQL 17.11, serviço `postgresql-x64-17`, em `127.0.0.1:5432`. Outros bancos e o cluster antigo da auditoria não foram alterados. O isolamento é lógico, na mesma instância: CPU, memória, disco e administração são compartilhados. O CONNECT cruzado e os grants PUBLIC foram restringidos nos dois bancos; conexões DEV→QA e QA→DEV foram realmente negadas. As roles têm LOGIN, não têm privilégios administrativos/CREATEDB e não possuem memberships. A configuração preexistente `listen_addresses='*'` do serviço compartilhado não foi modificada.

## Configuração

Foi mantido `django-environ`. `TAPSERVE_ENV=dev|qa` seleciona o arquivo dedicado e exige settings, banco, role, host/porta e origens correspondentes. A seleção explícita não herda o banco legado de `backend/.env`. Os quatro arquivos locais são ignorados pelo Git. Preserve suas chaves: SECRET_KEY e Fernet são independentes entre ambientes e protegem sessões, tokens, MFA e o cofre demonstrativo.

As variáveis são `POSTGRES_DB/USER/PASSWORD/HOST/PORT`, `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `TAPSERVE_TOKEN_KEYS`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_APP_ORIGIN`, `BACKEND_PORT`, `FRONTEND_PORT`, `STAFF_PIN_NETWORKS` e `TRUSTED_PROXY_NETWORKS`. `CORS_ALLOWED_ORIGINS` fica vazio: usa-se proxy de mesma origem, sem habilitar CORS. No frontend ficam somente `VITE_TAPSERVE_ENV`, `VITE_BACKEND_URL` e `VITE_FRONTEND_PORT`, sem segredos.

HTTP `/api` e WebSocket `/ws` passam pela origem do frontend ao backend selecionado. O Vite mantém o Origin original do socket e recusa misturas de portas/modos. O cliente deriva a URL WS de `location.host`. Mídia, temporários e logs ficam em `.local/environments/<dev|qa>/media`, `tmp` e `logs`.

Os cookies de sessão, CSRF, dispositivo e navegador têm nomes `tapserve-<dev|qa>-session`, `-csrf`, `-device` e `-browser`, são host-only, HttpOnly, SameSite=Lax e caminho `/`. Secure fica desabilitado somente no HTTP local, conforme o perfil DEV existente. Autenticação, MFA, autorização e CSRF permanecem ativos.

Cookies não são separados por porta; cada backend lê seus próprios nomes, com banco e segredos distintos. O `sessionStorage` já é isolado pela origem, incluindo porta, e os rascunhos operacionais incluem identidade/unidade/ocupação. Para pentest com código hostil, use perfis de navegador separados ou hosts locais distintos, revisando hosts/origens. Use consistentemente `127.0.0.1`.

Referências: [settings Django](https://docs.djangoproject.com/en/5.2/ref/settings/), [cookies no navegador](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies), [privilégios PostgreSQL](https://www.postgresql.org/docs/17/ddl-priv.html).

## Operação no Windows 11

Na raiz, em terminais normais separados:

```powershell
.\backend\.venv\Scripts\python.exe scripts/dev.py --env dev
.\backend\.venv\Scripts\python.exe scripts/dev.py --env qa
```

O launcher verifica conexão/isolamento, portas, saúde pelo proxy e módulo frontend. Ctrl+C encerra somente seus filhos. Não encerre processos pelo nome genérico para liberar portas. O caminho legado sem `--env` foi preservado por compatibilidade, mas não opera estes dois perfis.

Comandos de manutenção, sempre indicando o destino:

```powershell
$python = ".\backend\.venv\Scripts\python.exe"
& $python scripts/local_env.py check --env dev
& $python scripts/local_env.py check --env qa
& $python scripts/local_env.py migrate --env dev
& $python scripts/local_env.py migrate --env qa
& $python scripts/local_env.py seed --env dev
& $python scripts/local_env.py seed --env qa
& $python scripts/local_env.py verify --env dev
& $python scripts/local_env.py verify --env qa
```

`init` cria somente arquivos ausentes; não substitui credenciais. `harden --env ...` restringe apenas o banco selecionado após confirmar owner/role/memberships. Não promove roles ou altera senhas. `dry-run --env ...` executa o seed com rollback, sem manter registros ou escrever mídia/cofre/manifesto. `verify` testa views reais com rollback, incluindo MFA; não substitui rede/proxy/browser. Com ambos os frontends ativos, execute `scripts/local_env.py smoke` para HTTP/proxy/cookies/WS.

O primeiro acesso e a obtenção interativa de credenciais cifradas estão em [seeds-dev-qa.md](seeds-dev-qa.md). Não imprima segredos em relatórios nem execute recuperação de credenciais por um agente que capture stdout.

## QA persistente e laboratório descartável

O QA persistente não é apagado ao iniciar e não é destino de pytest destrutivo. As settings de testes recusam os nomes persistentes. O runner novo não seleciona o laboratório antigo nem sua porta.

Provisionar um banco descartável novo na mesma instância exige autenticação administrativa autorizada, solicitada sem eco:

```powershell
.\backend\.venv\Scripts\python.exe scripts/local_env.py create-test-db --env qa
.\backend\.venv\Scripts\python.exe scripts/local_env.py test --lab ".local/environments/tests/<uuid>/.env"
```

O primeiro comando cria somente `tapserve_test_<uuid>` e `tapserve_test_user_<uuid>`, com credenciais/chaves próprias, sem CREATEDB/superusuário e sem CONNECT PUBLIC. Salva um manifesto ignorado antes do provisionamento para permitir diagnóstico de criação parcial. A senha administrativa não é salva. O segundo exige o manifesto exato e valida caminho, role, banco, host e settings.

A fixture existente cria e remove somente seu schema exclusivo dentro desse banco descartável. Não há DROP DATABASE/TRUNCATE/reset do QA persistente nos comandos. O banco descartável é conservado para inspeção; remoção posterior requer identificação positiva e autorização específica. A suíte destrutiva e uma campanha de pentest ainda precisam desse laboratório, que não foi provisionado nesta execução.

## Diagnóstico e preservação

Conexão/role/owner/origens divergentes bloqueiam o comando antes do seed. Se faltar uma referência do manifesto, restaure o controle/backup correspondente em vez de resetar contas. Admissões e janelas de edição expiram normalmente; o seed não as prolonga. Confira `.local/environments/<env>/logs` sem copiar credenciais, tokens ou respostas MFA.

A falha atual do Vite é `spawn EPERM` em `optimizeSafeRealPathSync/windowsSafeRealPathSync`, ao iniciar `net use` sob o token restrito. Também houve falha de build novo nesta execução. Isso foi registrado separadamente dos testes backend aprovados; não houve alteração de ACL, dependências, autenticação ou asserts para mascarar o bloqueio. Execute no terminal normal do operador e registre o resultado real; não há garantia de que todo Windows apresente a mesma falha.

Evidências atuais: `.local/environments/seed-run-20261104T131626Z/`. O estado anterior à configuração permanece em `.local/environments/git-initial.json` e `postgres-initial.json`; não descreve mais os bancos já populados. Os relatórios em `docs/auditoria/` e `docs/auditoria-v2/` não foram reescritos. Não houve commit, push ou deploy.
