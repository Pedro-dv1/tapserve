# Execução do site TapServe V3

Início: 13/11/2026. Trabalho local, sem publicação, sem acesso ou escrita em bancos.

## Fontes e escopo

AGENTS.md e os quatro documentos em `assets_source/` foram lidos integralmente. Prioridade: decisões do usuário → Super Prompt V3 → arquitetura V2 → inventários V3. O app operacional e suas alterações preexistentes serão preservados. Site independente em `site/`, React + TypeScript + Vite (stack já estabelecida), com HTML pré-renderizado por rota. Não haverá novas dependências de runtime além de React/React DOM já usados no projeto.

Alcance: páginas, shell, conteúdo, assets, motor local de simulação, motion, metadados, build estático, testes e documentação. Não alterar callers, testes, fixtures, configuração, exportações ou dados do app operacional.

## Fases em sequência

- [x] 1. Auditoria: instruções/documentos, inventário, stack, conflitos e ferramentas.
- [x] 2. Direção de arte: 19 imagens geradas e inspecionadas; originais preservados; composições e manifesto de 70 IDs. Capturas e vistas sem fonte fiel explicitamente pendentes.
- [x] 3. Fundação: React/TypeScript/Vite independente, HTML por rota, shell e SEO de prévia; typecheck/build aprovados.
- [x] 4. Todas as 14 rotas + 404 implementadas, incluindo estados de revisão jurídica; lint e verificação estática aprovados.
- [x] 5. Motor compartilhado da demo e mini demo: catálogo, regras, carrinho, revisão, confirmação, estados, chamados, reset; testes de lógica aprovados.
- [x] 6. Motion CSS, IntersectionObserver e ponteiro; preferência reduzida e controle global. Aproximação NFC não implementada.
- [x] 7. Auditoria do código/fontes oficiais, cinco minutas internas e publicação bloqueada.
- [x] 8. QA técnico e revisão executados; testes de navegador, inspeção responsiva e Lighthouse bloqueados por ferramenta, registrados em QA.md.
- [x] 9. Relatório, manifesto, pendências, checklist do proprietário e instruções locais entregues.

Cada fase será conferida antes de avançar; materiais não verificáveis serão registrados como pendências sem bloquear trabalho independente.

## Decisões e conflitos registrados antes da implementação

1. **Plaquinha:** `assets_source/card/Plaquinha.png` mostra placa preta vertical, base transparente de acrílico, marca branca/âmbar, “APROXIME SEU CELULAR”, “MESA 08” e nenhum QR. Isso diverge do card branco horizontal descrito nos complementos. A imagem original é soberana segundo V3 §0.3. Preservar o modelo existente; não redesenhar, recolorir nem adicionar QR. Fotos compostas precisam de revisão de fidelidade. Arte vetorial plana/dimensões físicas não fornecidas.
2. **V02/M01–M03:** requisitos antigos de aproximação NFC substituídos pela decisão posterior. Não produzir nem implementar timeline parcial. Backlog futuro apenas.
3. **Demo:** fallback de vídeo P0 previsto na arquitetura foi superado: experiência clicável obrigatória, sem rede, cookies, storage ou pedidos reais.
4. **Valores:** referências comerciais não aprovadas. Simulador informativo explicitamente identificado, sem checkout, desconto ou promessa de contratação. Implantação e placas sob definição.
5. **Jurídico:** identidade do fornecedor, contratos, provedores e procedimentos não confirmados. Rotas legais terão aviso de revisão/noindex; minutas internas fora de `public/`. Build de publicação bloqueado até revisão verificável; nenhuma publicação nesta tarefa.
6. **Cookies:** sem rastreamento, embeds ou armazenamento persistente no site. Não criar `/cookies` ou banner sem necessidade comprovada; SaaS tem inventário separado.
7. **Ferramentas:** Node/npm/Python e dependências frontend disponíveis. Navegador CUA sem superfícies; tentativa `createBrowserTab('iab')` retornou “Browser is not available: iab”. Verificação visual via testes locais será tentada; não considerar QA visual aprovado por build.
8. **Skill de segurança:** índice disponível, mas arquivos `data/asvs/V1.2.md`, V2.1, V2.2 e V2.3 ausentes na instalação. Lacuna registrada; aplicar as instruções verificáveis de `engineer-code/references/security-gates.md`, validação e isolamento. Não alegar certificação ASVS.

## Direção de arte

Preto #111111, branco #FFFFFF, superfície #F5F5F3, âmbar #E5A62B. Inter local quando disponível, fallback system-ui. Fotografia editorial quente, madeira escura, vidro/metal reais, sem lettering gerado. Tipografia ampla, composição assimétrica, capítulos escuros alternados com leitura clara. Desktop até 1320px, tablet em duas colunas, mobile vertical a partir de 320px. Imagens próprias geradas, sem concorrentes; interfaces locais sempre rotuladas como simulação até haver screenshots reais autorizados.

## Segurança da implementação

Sem API/credenciais do produto; CSP com `connect-src 'none'` no build; valores monetários em centavos; opcionais e quantidades limitados e validados. React escapa texto; nenhum HTML do visitante é interpretado. Links externos fixos e parâmetros codificados. Preview somente em loopback. Nenhum registro de contatos ou telemetria.

## Conferências e ajustes finais

Fases verificadas por leitura, inspeção dos arquivos gerados e checks de código antes da continuação dependente. A produção independente de assets e pesquisa documental prosseguiu enquanto o site era construído. Não houve pausa aguardando dados comerciais/jurídicos desconhecidos.

- Fonte Manrope: download oficial tentado, bloqueado por conexão recusada no ambiente; nenhuma URL de fonte ausente ficou na interface. Fallback local `Manrope, Inter, system-ui` sem fonte remota.
- Capturas reais: autenticação/admissão exigiria escrita no ambiente QA; não realizada. Nenhuma credencial foi revelada.
- Social: browser bloqueado; O01–O05 compostos com Pillow e pixels originais da placa, conforme autorização de composição em código no V3.
- QA browser: Chromium esperado ausente; Chrome instalado tentado com sandbox ativo, retornou `spawn EPERM`. Nenhuma proteção foi enfraquecida para contornar o bloqueio.
- Revisão: corrigidos caminho do servidor estático, referência de fonte ausente, foco das tabs da demo, normalização da rota com barra final, leitura em mobile e propagação natural da rolagem da mini demo.
- `.gitignore`: apenas acrescentada exceção `!/docs/site/` para entregar estes documentos; regras/alterações anteriores preservadas.
- Graphify: `graphify update .` concluído (AST, sem LLM/API), com 2555 nós / 9421 arestas / 136 comunidades na primeira conferência. Nova demo localizada por `graphify query 'demoReducer'`.

O checklist indica execução das fases possíveis, não aprovação de lançamento. Pendências de captura, fotografia, QA visual, oferta e jurídico continuam abertas nos documentos específicos.
