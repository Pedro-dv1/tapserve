# TapServe

Sistema de atendimento para restaurantes, bares e estabelecimentos com pedidos por mesa. O cliente acessa o cardápio por QR Code, NFC ou link autorizado; a equipe acompanha os pedidos, a produção, as entregas e os chamados de atendimento.

O sistema separa empresas e unidades, com permissões individuais e interfaces próprias para clientes, atendentes e administradores.

## O que o sistema faz

- **Cliente:** consulta o cardápio, pesquisa produtos, visualiza imagens e vídeos, escolhe opções e adicionais, monta o carrinho, identifica participantes e acompanha os pedidos. Também pode chamar atendimento e solicitar a conta.
- **Atendente:** acompanha mesas, pedidos e chamados, lança pedidos manuais e realiza as etapas de entrega permitidas pelo seu acesso.
- **Produção:** organiza os itens por setor e acompanha as etapas de aceite, preparo e prontidão.
- **Administrador:** gerencia cardápios, categorias, produtos, opções, adicionais, funcionários, permissões, pontos de atendimento e configurações da unidade.
- **Plataforma:** possui uma área separada para administrar empresas e unidades, com credenciais próprias de operador.

As telas recebem atualizações por WebSocket. O backend utiliza eventos persistidos e notificações do PostgreSQL, com atualização periódica como alternativa quando necessário.

## Tecnologias

| Camada | Tecnologias utilizadas |
| --- | --- |
| Frontend | React 19, TypeScript e Vite 7 |
| Backend | Python 3.12, Django 5.2 e Django REST Framework |
| Tempo real | Django Channels, Daphne e notificações do PostgreSQL |
| Banco de dados | PostgreSQL |
| Imagens e arquivos | Pillow e armazenamento local em desenvolvimento |
| Verificação | Pytest, testes do Node.js, Playwright, ESLint, Ruff e Mypy |

As versões exatas estão em [`frontend/package-lock.json`](frontend/package-lock.json) e [`backend/requirements.lock`](backend/requirements.lock).

## O que instalar

Instale estes programas antes de configurar o projeto:

| Programa | Requisito |
| --- | --- |
| **Python** | Versão **3.12**. O instalador do projeto exige essa versão; a referência local é 3.12.10. Inclua o launcher `py` na instalação no Windows. |
| **Node.js e npm** | Node **22.12 ou superior**. Node 24 também é compatível com o instalador. O npm acompanha o Node.js. |
| **PostgreSQL** | Servidor instalado e em execução, com um banco e um usuário próprios do projeto. O ambiente local foi verificado com PostgreSQL 17.11. |
| **Git** | Para clonar o repositório e acompanhar as alterações. |

O cliente `psql`, normalmente disponível na instalação do PostgreSQL, facilita a criação do banco. Também é possível usar o pgAdmin.

**Opcionais:** Google Chrome para os testes de navegador e FFmpeg/ffprobe para inspeção adicional de vídeos. O processamento local de vídeos já possui validação sem ffprobe.

O desenvolvimento local não exige Docker, Redis, S3 nem credenciais de serviços externos. O PostgreSQL é necessário: a implementação utiliza recursos próprios dele e não possui um modo equivalente com SQLite.

## Instalação no Windows

Os comandos abaixo usam PowerShell e devem começar na **raiz do repositório**, onde ficam as pastas `backend`, `frontend` e `scripts`.

### 1. Conferir as instalações

```powershell
py -3.12 --version
node --version
npm.cmd --version
```

No PowerShell, os exemplos usam `npm.cmd` para evitar o bloqueio de execução do arquivo `npm.ps1`.

### 2. Instalar as dependências do projeto

```powershell
py -3.12 scripts/bootstrap.py
```

Esse comando:

- Cria o ambiente virtual em `backend/.venv`.
- Instala as dependências Python de `backend/requirements.lock`.
- Instala as dependências do frontend com `npm ci`.
- Cria `backend/.env` a partir do exemplo da raiz, se o arquivo ainda não existir.
- Gera a chave secreta do Django para uma configuração nova e acrescenta uma chave independente de criptografia de tokens quando ausente.
- Preserva um arquivo de configuração já existente.

É necessário acesso à internet durante a instalação das dependências. Não é preciso ativar o ambiente virtual para usar os comandos deste README.

### 3. Criar o banco de dados

Se você já possui um banco e um usuário para esta instalação, avance para a configuração do `.env`.

Caso contrário, abra o SQL Shell do PostgreSQL ou execute, com o `psql` disponível no PATH:

```powershell
psql -h 127.0.0.1 -U postgres
```

Dentro do `psql`, execute:

```sql
CREATE ROLE tapserve_user LOGIN;
\password tapserve_user
CREATE DATABASE tapserve OWNER tapserve_user;
\q
```

O comando `\password` pede a senha do usuário do banco de forma interativa. Você escolhe essa senha; ela é diferente das senhas e PINs usados pelos funcionários dentro do TapServe.

### 4. Configurar o ambiente

Edite **`backend/.env`**, criado pelo bootstrap, e preencha os dados do seu PostgreSQL. Por exemplo:

```dotenv
POSTGRES_DB=tapserve
POSTGRES_USER=tapserve_user
POSTGRES_PASSWORD=preencha_com_a_senha_do_seu_banco
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
PUBLIC_APP_ORIGIN=http://127.0.0.1:5173
STAFF_PIN_NETWORKS=127.0.0.1/32,::1/128
```

Substitua o valor de `POSTGRES_PASSWORD` pela senha definida na etapa anterior. Preserve os valores gerados para `DJANGO_SECRET_KEY` e `TAPSERVE_TOKEN_KEYS`.

`STAFF_PIN_NETWORKS` define as redes autorizadas a usar login por PIN. O exemplo acima permite o acesso local pelo próprio computador.

Cada instalação tem seu próprio banco, contas, arquivos e links de mesas. O repositório não inclui o banco nem o arquivo `.env` de outra instalação. As mídias de desenvolvimento ficam em `.local/media/`.

### 5. Aplicar as migrações

Ainda na raiz do repositório:

```powershell
.\backend\.venv\Scripts\python.exe backend\manage.py migrate --settings=config.settings.dev
```

Esse comando cria ou atualiza as tabelas, índices e demais estruturas utilizadas pelo sistema.

### 6. Criar os primeiros acessos

Escolha uma das alternativas a seguir.

#### Alternativa A: preparar uma demonstração local

```powershell
.\backend\.venv\Scripts\python.exe backend\manage.py seed_demo --username responsavel --settings=config.settings.dev
```

O comando solicita, nesta ordem:

1. Um PIN de 6 a 12 dígitos para o atendente da demonstração.
2. Uma senha forte para o responsável.
3. A confirmação dessa senha.
4. Um PIN individual de 6 a 12 dígitos para o responsável.

Ele prepara a empresa `tapserve-demo`, a unidade `demo`, o responsável informado em `--username`, um atendente com código `demo-waiter`, uma mesa e um cardápio básico para testar pedidos.

Use a senha escolhida para entrar como responsável e o PIN escolhido para entrar como atendente. O comando é exclusivo do perfil de desenvolvimento e preserva credenciais já cadastradas; executá-lo novamente não redefine senhas ou PINs existentes.

#### Alternativa B: configurar uma empresa e uma unidade próprias

```powershell
.\backend\.venv\Scripts\python.exe backend\manage.py setup_unit `
  --company minha-empresa `
  --company-name "Minha empresa" `
  --unit principal `
  --unit-name "Unidade principal" `
  --username responsavel `
  --name "Responsável" `
  --settings=config.settings.dev
```

O comando pede a senha, a confirmação e o PIN individual do responsável. A senha deve ter pelo menos 12 caracteres e atender às validações do Django.

Depois de entrar no painel, cadastre o cardápio, as categorias, os setores, os produtos, os pontos de atendimento e os demais funcionários. Esse comando não importa os dados da demonstração.

## Como rodar

Na raiz do repositório:

```powershell
py -3.12 scripts/dev.py
```

O launcher inicia o backend com Daphne e o frontend com Vite, configura o proxy e verifica a conexão com o banco. Mantenha o terminal aberto. Para encerrar os processos iniciados por ele, pressione **Ctrl+C**.

| Endereço | Finalidade |
| --- | --- |
| [http://127.0.0.1:5173](http://127.0.0.1:5173) | Verificação da conexão entre frontend, API e banco. |
| [http://127.0.0.1:5173/staff/login](http://127.0.0.1:5173/staff/login) | Login de responsáveis e equipe. |
| [http://127.0.0.1:8000/api/v1/health/](http://127.0.0.1:8000/api/v1/health/) | Saúde da API e do PostgreSQL. |
| [http://127.0.0.1:8000/api/v1/schema/](http://127.0.0.1:8000/api/v1/schema/) | Esquema OpenAPI, disponível em desenvolvimento. |

Na tela de login, informe os códigos da empresa e da unidade criadas. Para gestão, selecione **“Responsável: entrar com senha”**. Para o atendimento, use **“Entrar com PIN individual”** e o código individual do funcionário.

O launcher não encerra processos que já estejam ocupando as portas. Para escolher outras portas:

```powershell
py -3.12 scripts/dev.py --api-port 8001 --frontend-port 5174
```

Nesse caso, utilize os endereços com as novas portas. O launcher ajusta o proxy e as origens correspondentes.

## Como obter o link da mesa demo

O link de uma mesa contém um token gerado no banco da própria instalação. Por isso, não existe um link fixo que funcione em todos os computadores ou bancos.

Depois de preparar a demonstração e iniciar o sistema:

1. Entre como responsável em `/staff/login`.
2. Abra **Pontos de atendimento**.
3. Localize a mesa de demonstração e clique em **Editar**.
4. Abra **QR Code e NFC**.
5. Copie o link público ou use a opção de abrir o acesso.

Esse endereço autoriza o navegador do cliente a acessar a mesa e o cardápio correspondente. Também é possível baixar o QR Code nessa tela. Se o identificador da mesa for regenerado, obtenha o novo link no painel.

## Acessar pelo celular na mesma rede

Descubra o IPv4 do computador conectado ao Wi-Fi ou à rede local com `ipconfig`. Inicie o projeto informando esse endereço, por exemplo:

```powershell
py -3.12 scripts/dev.py --lan-ip 192.168.1.100
```

Substitua `192.168.1.100` pelo IP real do seu computador. O celular deve estar na mesma rede, e o firewall precisa permitir o acesso às portas utilizadas.

Abra `http://IP-DO-COMPUTADOR:5173` no celular. O launcher configura os hosts, as origens de CSRF/WebSocket e a origem dos links de mesa para esse endereço. Copie novamente o link da mesa pelo painel para usá-lo no celular.

Para permitir também o **login da equipe por PIN** na rede local, acrescente a rede confiável a `STAFF_PIN_NETWORKS` em `backend/.env`. Exemplo para uma rede `192.168.1.x`:

```dotenv
STAFF_PIN_NETWORKS=127.0.0.1/32,::1/128,192.168.1.0/24
```

Use o endereço de rede que corresponde ao seu ambiente. Esse ajuste não é necessário para o acesso do cliente ao cardápio por link/QR Code. A gravação NFC depende do suporte do navegador, do dispositivo e de um contexto seguro; o acesso por link ou QR Code continua disponível.

## Testes e verificações

Frontend, a partir da raiz:

```powershell
Push-Location frontend
npm.cmd test
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
Pop-Location
```

Backend:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy apps common config
Pop-Location
```

Os testes do backend exigem PostgreSQL acessível e permissão para criar um schema no banco configurado. O `conftest.py` cria um schema exclusivo para cada execução e o remove ao terminar.

Os testes de navegador usam Playwright com Google Chrome. Com os servidores locais rodando nas portas padrão:

```powershell
Push-Location frontend
npm.cmd run test:e2e
Pop-Location
```

O build do frontend gera `frontend/dist/`. Esse comando não publica o sistema nem inicia o backend.

## Estrutura do repositório

```text
tapserve/
├── backend/
│   ├── apps/
│   │   ├── access/          # Mesas, QR/NFC e acesso do cliente
│   │   ├── catalog/         # Cardápios, produtos, opções e mídia
│   │   ├── identity/        # Funcionários, autenticação e permissões
│   │   ├── orders/          # Pedidos, produção, chamados e tempo real
│   │   └── organizations/   # Empresas e unidades
│   ├── common/              # Infraestrutura compartilhada da API
│   ├── config/              # Rotas, ASGI e perfis de configuração
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # Componentes compartilhados
│   │   ├── design-system/   # Estilos das interfaces
│   │   ├── features/        # Áreas de cliente e equipe
│   │   └── lib/             # API, tempo real e hooks
│   └── tests/
├── scripts/                 # Instalação e execução local
├── assets/                  # Recursos visuais
├── docs/                    # Documentação complementar
└── .local/                  # Mídias e logs locais, fora do Git
```

## Problemas comuns

| Sintoma | O que conferir |
| --- | --- |
| Bootstrap pede Python 3.12 | Execute com `py -3.12`; outra versão instalada como `python` não substitui esse requisito. |
| PowerShell bloqueia `npm.ps1` | Use `npm.cmd`, como nos exemplos. |
| Erro de conexão com o banco | Verifique se o PostgreSQL está ativo e se host, porta, banco, usuário e senha em `backend/.env` estão corretos. |
| Tabelas ou relações não encontradas | Execute as migrações no banco configurado. |
| Porta ocupada | Encerre o processo correspondente ou escolha portas alternativas no launcher. |
| Login por PIN recusado na rede local | Confira o código individual, o PIN e `STAFF_PIN_NETWORKS`. |
| Link da mesa inválido | Obtenha o link da sua instalação no painel e confira se a mesa e seu acesso estão ativos. |
| Mesa sem cardápio disponível | Confira o vínculo do ponto ao cardápio e a disponibilidade dos produtos. |
| Servidores não iniciam ou encerram | Leia `.local/api-dev.log` e `.local/frontend-dev.log`. |

## Desenvolvimento e produção

Este guia cobre **desenvolvimento local**. O comando `scripts/dev.py` utiliza o perfil `config.settings.dev`.

O perfil `config.settings.prod` possui requisitos próprios, incluindo HTTPS, hosts e origens explícitos, conexão PostgreSQL com verificação de certificado e armazenamento privado de mídia em S3. A publicação exige configurar esses recursos; executar o build do frontend, sozinho, não configura uma implantação de produção.
