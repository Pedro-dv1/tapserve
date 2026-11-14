# TapServe — Brief de criação das imagens V3

Este guia serve para você criar as fotografias e camadas visuais **antes de disponibilizá-las ao Codex**. Não gera fotografias automaticamente. O inventário completo está em `TAPSERVE_ASSET_SHEET_V3.md`.

## Direção de arte unificada

- **Conceito:** fotografia publicitária premium de tecnologia aplicada a restaurantes, **realista**, sem aparência de stock barato ou CGI plástico.
- **Paleta:** ambiente de madeira escura/neutra, preto `#111111`, off-white `#F5F5F3`, luz quente inspirada no âmbar `#E5A62B`. Evitar iluminação dourada exagerada.
- **Câmera:** fotografia editorial com lentes equivalentes 35–50mm, textura de materiais real, profundidade de campo controlada e enquadramento limpo.
- **Ambiente:** restaurante contemporâneo plausível, com madeira, metais discretos, louças modernas e luz natural/ambiente. Se houver pessoas, gestos anatomicamente corretos.
- **Repetição:** manter o mesmo cenário, iluminação, dispositivo e card nas imagens F01–F04 e M01–M03 quando fizerem parte da cena principal. Gerar variações a partir de uma base consistente.
- **Nunca deixar IA escrever o nome TapServe ou fabricar o card.** Nas cenas com marca, criar espaço livre/área de cor neutra; aplicar **logo oficial e arte final do cartão** por composição posterior. Nos celulares, telas vazias/neutras ou máscara para aplicar as capturas reais Sxx.
- **Card físico obrigatório:** cartão branco, retangular horizontal e largo, **colado diretamente na mesa** (não vertical, não em suporte). Arte final, wordmark preto, círculo preto envolvendo a área NFC e o texto "Aproxime aqui" são inseridos a partir do original aprovado.
- **QR:** quando uma cena tiver QR, não confiar em QR inventado por IA. Adicionar QR real por SVG/gerador confiável, ou rotular como demonstrativo.
- **Direitos:** só imagens geradas por você, fotografadas com autorização ou licenciadas para uso comercial; fotos de concorrentes são referência, não material utilizável.
- **Exportação:** guardar master sem perdas PNG/TIFF/alta qualidade e derivados WebP; o Codex pode gerar cortes mobile sem perder o objeto-chave.

## Prompt-base para manter consistência

> Fotografia editorial publicitária premium e fotorrealista para uma empresa brasileira de tecnologia de restaurantes; ambiente contemporâneo elegante e plausível, mesa em madeira natural escura, detalhes preto e off-white, iluminação cinematográfica sutilmente quente, textura real de madeira, metal, papel e vidro, lente de câmera real 35–50 mm, composição precisa, proporções naturais, espaço negativo para interface e texto, alta nitidez no produto, sem marcas comerciais, sem logotipos gerados, sem palavras inventadas, sem watermark, sem texto de interface gerado, sem aparência de imagem de banco genérica. Manter direção de arte coerente com o restante da série.

O prompt-base deve ser combinado com a instrução específica de cada arquivo abaixo; **não substitui a arte original do card nem os prints verdadeiros**.

## Checklist por cena (29 itens)

### F01 — Restaurante principal do hero (P0)

- **Salvar como:** `assets/fotografias/F01-hero-restaurant-wide.webp`
- **Tamanho mestre:** 2400×1350 (16:9)
- **Produzir:** Foto wide premium: mesa em destaque no primeiro plano, restaurante contemporâneo ao fundo, espaço negativo para título.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F02 — Card colado na mesa (P0)

- **Salvar como:** `assets/fotografias/F02-card-fixed-on-table.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Close da arte ORIGINAL em um cartão horizontal branco colado diretamente à mesa; círculo preto NFC.
- **Orientação extra:** **Não gerar o lettering da etiqueta com IA:** aplicar a arte oficial do card sobre a superfície física. Se usar QR Code, sobrepor SVG verdadeiro conforme a variante aprovada.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F03 — Celular aproximando do NFC (P0)

- **Salvar como:** `assets/fotografias/F03-phone-near-card.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Mão com smartphone aproximando da área NFC física; câmera plausível, tela preparada para sobreposição real.
- **Orientação extra:** **Tela do telefone:** criar espaço neutro e aplicar o screenshot do TapServe na pós-produção. Evitar inventar componentes ou logotipos na tela.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F04 — Cliente usando o cardápio (P0)

- **Salvar como:** `assets/fotografias/F04-customer-using-menu.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Cliente adulto em restaurante usando smartphone de modo natural; a tela final recebe captura verdadeira do TapServe.
- **Orientação extra:** **Tela do telefone:** criar espaço neutro e aplicar o screenshot do TapServe na pós-produção. Evitar inventar componentes ou logotipos na tela.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F05 — Refeição e smartphone (P1)

- **Salvar como:** `assets/fotografias/F05-food-and-phone.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Foto editorial de comida no restaurante, celular como elemento secundário, sem logotipos fictícios.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F06 — Equipe no salão (P0)

- **Salvar como:** `assets/fotografias/F06-staff-on-floor.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Garçom/funcionário em restaurante com dispositivo de atendimento; contexto de operação realista.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F07 — Cozinha com KDS (P0)

- **Salvar como:** `assets/fotografias/F07-kitchen-kds-real.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Cozinha de restaurante com monitor; inserir a captura REAL S13/S14 na tela do monitor.
- **Orientação extra:** **Tela do KDS:** gerar a cena com monitor sem conteúdo identificável. Aplicar a captura real `S13` ou `S14` no monitor com perspectiva compatível.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F08 — Card em ângulo de 45° (P0)

- **Salvar como:** `assets/fotografias/F08-card-product-45deg.webp`
- **Tamanho mestre:** 1800×1350 (4:3)
- **Produzir:** Produto físico premium: adesivo/cartão branco HORIZONTAL fixado à mesa, material e arte oficial nítidos.
- **Orientação extra:** **Não gerar o lettering da etiqueta com IA:** aplicar a arte oficial do card sobre a superfície física. Se usar QR Code, sobrepor SVG verdadeiro conforme a variante aprovada.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F09 — Card visto de cima (P0)

- **Salvar como:** `assets/fotografias/F09-card-topdown.webp`
- **Tamanho mestre:** 1800×1350 (4:3)
- **Produzir:** Vista ortográfica de cima; wordmark e círculo NFC totalmente legíveis, geometria fiel ao card original.
- **Orientação extra:** **Não gerar o lettering da etiqueta com IA:** aplicar a arte oficial do card sobre a superfície física. Se usar QR Code, sobrepor SVG verdadeiro conforme a variante aprovada.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F10 — Macro da área NFC (P0)

- **Salvar como:** `assets/fotografias/F10-card-macro-nfc.webp`
- **Tamanho mestre:** 1800×1350 (4:3)
- **Produzir:** Macro fotográfica do círculo preto e indicação "Aproxime aqui", com fidelidade tipográfica.
- **Orientação extra:** **Não gerar o lettering da etiqueta com IA:** aplicar a arte oficial do card sobre a superfície física. Se usar QR Code, sobrepor SVG verdadeiro conforme a variante aprovada.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F11 — Detalhe do QR Code (P0)

- **Salvar como:** `assets/fotografias/F11-card-qr-closeup.webp`
- **Tamanho mestre:** 1800×1350 (4:3)
- **Produzir:** Variante física com QR Code verdadeiro para uma URL de demo aprovada ou identificado como ilustrativo.
- **Orientação extra:** **Não gerar o lettering da etiqueta com IA:** aplicar a arte oficial do card sobre a superfície física. Se usar QR Code, sobrepor SVG verdadeiro conforme a variante aprovada.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F12 — Card numa mesa montada (P1)

- **Salvar como:** `assets/fotografias/F12-card-lifestyle-table.webp`
- **Tamanho mestre:** 1800×1350 (4:3)
- **Produzir:** Card original fixado em mesa de restaurante com pratos e copos; contexto lifestyle sem suporte vertical.
- **Orientação extra:** **Não gerar o lettering da etiqueta com IA:** aplicar a arte oficial do card sobre a superfície física. Se usar QR Code, sobrepor SVG verdadeiro conforme a variante aprovada.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F13 — Ambiente restaurante (P1)

- **Salvar como:** `assets/fotografias/F13-venue-restaurant.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Fotografia editorial de salão de restaurante; coerente com campanha visual.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F14 — Ambiente hamburgueria (P1)

- **Salvar como:** `assets/fotografias/F14-venue-hamburger.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Fotografia editorial de hamburgueria contemporânea, de preferência mercado brasileiro.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F15 — Ambiente lanchonete (P1)

- **Salvar como:** `assets/fotografias/F15-venue-snack.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Fotografia realista de lanchonete limpa e acessível.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F16 — Ambiente bar (P1)

- **Salvar como:** `assets/fotografias/F16-venue-bar.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Fotografia de bar contemporâneo, iluminação quente e ambiente profissional.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F17 — Ambiente cafeteria (P1)

- **Salvar como:** `assets/fotografias/F17-venue-cafe.webp`
- **Tamanho mestre:** 1600×1200 (4:3)
- **Produzir:** Fotografia de cafeteria contemporânea, iluminação natural/quente.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### F18 — Foto de encerramento (P1)

- **Salvar como:** `assets/fotografias/F18-final-cta-restaurant.webp`
- **Tamanho mestre:** 2400×1100 (~2.18:1)
- **Produzir:** Fotografia horizontal distinta do hero com atmosfera premium e espaço para CTA final.
- **Orientação extra:** **Ambiente:** não adicionar marca TapServe fictícia; aplicar logo ou screenshot apenas quando realmente necessário.
- **Entradas que devem ser fiéis:** B01, arte física; Sxx conforme cena


### D01 — Hambúrguer (P0)

- **Salvar como:** `assets/demo-cardapio/D01-demo-burger.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Hambúrguer artesanal em fundo/cozinha da mesma campanha; foto apetitoso porém realista; sem marca.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D02 — Batata frita (P0)

- **Salvar como:** `assets/demo-cardapio/D02-demo-fries.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Porção de batatas fritas; iluminação e tratamento idênticos à imagem D01.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D03 — Refrigerante (P0)

- **Salvar como:** `assets/demo-cardapio/D03-demo-soda.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Copo de refrigerante genérico com gelo, sem logo de fabricante.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D04 — Água (P0)

- **Salvar como:** `assets/demo-cardapio/D04-demo-water.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Copo/garrafa de água sem marca, fundo neutro.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D05 — Brownie (P0)

- **Salvar como:** `assets/demo-cardapio/D05-demo-brownie.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Brownie de sobremesa, prato coerente com restaurante da demonstração.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D06 — Milk-shake (P0)

- **Salvar como:** `assets/demo-cardapio/D06-demo-milkshake.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Milk-shake fotografado de forma consistente com os demais produtos.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D07 — Sanduíche de frango (P0)

- **Salvar como:** `assets/demo-cardapio/D07-demo-chicken.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Sanduíche de frango genérico, sem marca.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### D08 — Salada (P0)

- **Salvar como:** `assets/demo-cardapio/D08-demo-salad.webp`
- **Tamanho mestre:** 1200×1200 (1:1)
- **Produzir:** Salada/alternativa vegetariana com fotografia consistente.
- **Orientação extra:** **Cardápio demonstrativo:** fotografar o alimento em formato quadrado, mantendo a mesma louça, iluminação e fundo do restante dos itens; sem marca no rótulo ou embalagem.
- **Entradas que devem ser fiéis:** Catálogo demo JSON


### M01 — Mesa sem dispositivos (P0)

- **Salvar como:** `assets/motion-camadas/M01-table-clean-plate.png`
- **Tamanho mestre:** 2400×1350 (16:9)
- **Produzir:** Fundo fotográfico do mesmo ambiente do hero, mesa visível e livre, para permitir animação em camadas.
- **Orientação extra:** **Base de animação:** criar mesa sem celular/mão/card embutidos. Objetos serão sobrepostos em camadas para permitir movimento.
- **Entradas que devem ser fiéis:** F01 e direção de arte


### M02 — Mão com celular recortada (P0)

- **Salvar como:** `assets/motion-camadas/M02-hand-phone-alpha.png`
- **Tamanho mestre:** 2000×2000 com alpha
- **Produzir:** Mão realista segurando smartphone em PNG com transparência, posição correta para aproximar do NFC; visor substituível por S01.
- **Orientação extra:** **Camada alfa:** mão+smartphone recortados em PNG transparente, enquadramento e perspectiva compatíveis com M01; a tela deve ser substituível.
- **Entradas que devem ser fiéis:** F03,S01


### M03 — Card oficial recortado (P0)

- **Salvar como:** `assets/motion-camadas/M03-nfc-card-alpha.png`
- **Tamanho mestre:** 1600×1000 com alpha
- **Produzir:** Card retangular horizontal reproduzido fielmente em PNG transparente, compatível com a perspectiva do M01.
- **Orientação extra:** **Camada alfa:** usar a arte verdadeira do cartão com bordas exatas e perspectiva compatível com M01; não improvisar texto ou NFC.
- **Entradas que devem ser fiéis:** Arte vetorial original do card,B01


## Verificação final antes de mandar ao Codex

- [ ] A marca é exatamente a original e não foi redesenhada por IA.
- [ ] O card está colado diretamente na mesa; versão e QR corretos.
- [ ] O telefone e os monitores mostram as capturas verdadeiras ou fundo neutro para aplicação posterior.
- [ ] A mesma luz, cenário e dispositivo são usados nos materiais de uma mesma sequência.
- [ ] Não existem mãos deformadas, textos errados, QR quebrados ou materiais irreais.
- [ ] Cada imagem tem seu ID, nome, formato e prioridade correspondentes ao manifesto.
- [ ] A demo utiliza imagens de alimento consistentes, sem logo de marca ou alegações de venda real.
- [ ] Os arquivos são seus ou têm licença comercial verificável.
