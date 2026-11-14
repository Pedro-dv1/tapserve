# Prompts e produção de imagens — TapServe V3

Data: 13/11/2026. Ferramenta efetivamente usada: `image_gen.imagegen`, integrada, sem CLI/API de fallback. Cada asset foi gerado separadamente. Masters preservados em `site/assets/originals/generated/`; WebP responsivos em `site/public/assets/photography/` e `site/public/assets/demo-cardapio/`.

## Direção e revisão

Fotografia editorial realista, madeira escura, carvão/off-white, luz quente sutil. Todas as cenas são ilustrações geradas, não restaurantes, clientes ou funcionários reais do TapServe. Não representam testemunhos nem clientes existentes. Telas de telefone/tablet ficam invisíveis; F07 tem monitor vazio e **não é uma captura de KDS**. Aplicar somente captura verdadeira autorizada para concluí-la; até lá manter rotulada ou não usar como prova do produto.

D01–D08 são itens fictícios para demonstração. D03/D04 foram regenerados após a ferramenta produzir pratos não solicitados no primeiro lote; somente as bebidas corretas foram mantidas nos derivados finais. F17 passou por edição integrada para remover lettering gerado da cafeteira. Não foram usadas fotografias de concorrentes.

Pillow foi usado exclusivamente para redimensionar/codificar WebP, sem gerar ou editar cenas. A arte da plaquinha não foi alterada por este trabalho. Os masters nativos têm resolução informada em `GENERATED_ASSETS.json`, sem alegar 2400px quando a ferramenta retornou menos. A variante F01 de 1920px é interpolada; preferir 1280px quando suficiente.

Derivados: fotografias 640/1280px; F01 também 1920px; itens demo 320/640px. `srcset` deve usar os arquivos com sufixos. Aprovação comercial/visual final e avaliação de direitos antes de publicar permanecem pendentes.

## Prompts finais

### D01 — D01-demo-burger

Arquivo: `site/public/assets/demo-cardapio/D01-demo-burger.webp`  
Master: `site/assets/originals/generated/D01-demo-burger.png`

```text
Use case: photorealistic-natural. Square professional food photography for a simulated Brazilian restaurant menu, consistent series. Dark walnut table, charcoal matte ceramic plate when appropriate, warm soft window light from upper left, rich natural textures, controlled shadows, shallow depth of field, real 50mm food photography, centered single portion with breathing room. No brands, lettering, packaging logos, watermark, hands, UI, CGI or oversaturated fake food. One appetizing artisanal beef hamburger with brioche bun, melted cheese, lettuce, tomato and onion, on a charcoal matte ceramic plate.
```

### D02 — D02-demo-fries

Arquivo: `site/public/assets/demo-cardapio/D02-demo-fries.webp`  
Master: `site/assets/originals/generated/D02-demo-fries.png`

```text
Use case: photorealistic-natural. Square professional food photography for a simulated Brazilian restaurant menu, consistent series. Dark walnut table, charcoal matte ceramic plate when appropriate, warm soft window light from upper left, rich natural textures, controlled shadows, shallow depth of field, real 50mm food photography, centered single portion with breathing room. No brands, lettering, packaging logos, watermark, hands, UI, CGI or oversaturated fake food. One generous portion of crisp golden french fries, subtle sea salt, in a small charcoal matte ceramic bowl.
```

### D03 — D03-demo-soda

Arquivo: `site/public/assets/demo-cardapio/D03-demo-soda.webp`  
Master: `site/assets/originals/generated/D03-demo-soda.png`

```text
Create a square product photograph of ONE GLASS OF COLA ONLY. The only object on the dark walnut table is a plain clear tumbler filled with dark brown cola soda, ice cubes, and condensation, centered in the frame. Warm soft window light from upper left, blurred dark restaurant background, premium photorealistic 50mm beverage photography. No food of any kind, no plate, no rice, no meat, no cutlery, no bottle, no logos, no text, no watermark. This image is the beverage thumbnail D03 in a demo menu. The glass is the entire subject, fully visible.
```

Revisão: Regenerated after first output included unrelated meal.

### D04 — D04-demo-water

Arquivo: `site/public/assets/demo-cardapio/D04-demo-water.webp`  
Master: `site/assets/originals/generated/D04-demo-water.png`

```text
Create a square product photograph of ONE GLASS OF WATER ONLY. The only object on the dark walnut table is a plain clear tumbler filled with transparent drinking water, a few tiny condensation droplets, centered in the frame. Warm soft window light from upper left, blurred dark restaurant background, premium photorealistic 50mm beverage photography. No food of any kind, no plate, no rice, no meat, no cutlery, no bottle, no logos, no text, no watermark. This image is the beverage thumbnail D04 in a demo menu. The glass is the entire subject, fully visible.
```

Revisão: Regenerated after first output included unrelated meal.

### D05 — D05-demo-brownie

Arquivo: `site/public/assets/demo-cardapio/D05-demo-brownie.webp`  
Master: `site/assets/originals/generated/D05-demo-brownie.png`

```text
Square product photograph of ONE chocolate brownie topped with ONE scoop of vanilla ice cream on a charcoal ceramic plate; rich fudgy texture. Only this item appears on the dark walnut table. Premium photorealistic 50mm food photography, warm soft window light from upper left, blurred dark restaurant background. Centered, entire portion visible, charcoal matte ceramic when appropriate. No other dishes, rice, beans, steak, branding, logos, text, watermark, people, hands, CGI.
```

### D06 — D06-demo-milkshake

Arquivo: `site/public/assets/demo-cardapio/D06-demo-milkshake.webp`  
Master: `site/assets/originals/generated/D06-demo-milkshake.png`

```text
Square product photograph of ONE tall plain glass of chocolate milkshake topped with modest whipped cream and chocolate shavings. NO food or plate. Only this item appears on the dark walnut table. Premium photorealistic 50mm food photography, warm soft window light from upper left, blurred dark restaurant background. Centered, entire portion visible, charcoal matte ceramic when appropriate. No other dishes, rice, beans, steak, branding, logos, text, watermark, people, hands, CGI.
```

### D07 — D07-demo-chicken

Arquivo: `site/public/assets/demo-cardapio/D07-demo-chicken.webp`  
Master: `site/assets/originals/generated/D07-demo-chicken.png`

```text
Square product photograph of ONE grilled chicken sandwich on a brioche bun with lettuce, tomato and light sauce, on a charcoal ceramic plate. Visible white grilled chicken breast filling. Only this item appears on the dark walnut table. Premium photorealistic 50mm food photography, warm soft window light from upper left, blurred dark restaurant background. Centered, entire portion visible, charcoal matte ceramic when appropriate. No other dishes, rice, beans, steak, branding, logos, text, watermark, people, hands, CGI.
```

### D08 — D08-demo-salad

Arquivo: `site/public/assets/demo-cardapio/D08-demo-salad.webp`  
Master: `site/assets/originals/generated/D08-demo-salad.png`

```text
Square product photograph of ONE bowl of fresh vegetarian salad with green leaves, cherry tomatoes, sliced cucumber, shredded carrot and chickpeas in charcoal ceramic bowl. Only this item appears on the dark walnut table. Premium photorealistic 50mm food photography, warm soft window light from upper left, blurred dark restaurant background. Centered, entire portion visible, charcoal matte ceramic when appropriate. No other dishes, rice, beans, steak, branding, logos, text, watermark, people, hands, CGI.
```

### F01 — F01-hero-restaurant-wide

Arquivo: `site/public/assets/photography/F01-hero-restaurant-wide.webp`  
Master: `site/assets/originals/generated/F01-hero-restaurant-wide.png`

```text
Use case: photorealistic-natural. Asset F01, website hero panorama, 16:9 landscape. Premium editorial advertising photography of a plausible contemporary Brazilian restaurant, no people in foreground. A beautiful dark natural walnut dining table fills the lower third, completely empty with generous clear surface for later product compositing. Background elegant restaurant with black metal details, off-white stoneware on distant tables, subtle warm amber light and soft daylight, sophisticated but welcoming. 35mm real camera lens, tactile wood grain and glass, controlled depth of field, high realism and refined exposure. Composition has calm negative space on left for web headline, restaurant atmosphere on right. Absolutely no brands, lettering, logos, signage, NFC plaques, QR codes, devices, watermark, UI, plastic CGI look, exaggerated gold lighting. Do not include the TapServe product; it will be inserted from its original artwork.
```

### F04 — F04-customer-using-menu

Arquivo: `site/public/assets/photography/F04-customer-using-menu.webp`  
Master: `site/assets/originals/generated/F04-customer-using-menu.png`

```text
Use case: photorealistic-natural. An adult restaurant guest in natural side profile at a dark walnut dining table, casually browsing a black smartphone held normally, phone screen turned away from camera and completely invisible. White ceramic plate and water glass, contemporary restaurant background, no identifiable real person. Natural anatomical hands. 4:3 horizontal framing. Premium editorial advertising photography, real 35–50mm lens, tactile wood glass metal, refined subtle amber and off-white palette with charcoal accents, realistic materials, controlled depth of field. Absolutely no brands, logos, words, watermark, UI text, QR codes, plaques, fake signage, CGI, exaggerated golden lighting.
```

### F05 — F05-food-and-phone

Arquivo: `site/public/assets/photography/F05-food-and-phone.webp`  
Master: `site/assets/originals/generated/F05-food-and-phone.png`

```text
Use case: photorealistic-natural. A 4:3 landscape editorial photograph of a plated artisanal hamburger and french fries on charcoal ceramic, on a dark walnut restaurant table. A black smartphone rests face down as a small secondary detail at the edge of the table, no visible screen or brand. Water glass, off-white linen napkin, appetizing natural food. Premium hospitality photography, real 35–50mm camera, tactile materials, natural soft window light mixed with restrained warm amber ambiance, controlled depth of field, believable contemporary Brazilian restaurant. No brands, lettering, logos, signage, QR codes, plaques, watermark, generated UI, CGI, people.
```

### F06 — F06-staff-on-floor

Arquivo: `site/public/assets/photography/F06-staff-on-floor.webp`  
Master: `site/assets/originals/generated/F06-staff-on-floor.png`

```text
Use case: photorealistic-natural. An adult server wearing a simple charcoal apron over an off-white shirt, naturally holding a small black tablet screen turned away from camera and completely invisible, standing in a plausible contemporary Brazilian restaurant dining room between dark wood tables. Professional candid atmosphere, no identifiable real person. 4:3 horizontal framing. Premium editorial advertising photography, real 35–50mm lens, tactile wood glass metal, refined subtle amber and off-white palette with charcoal accents, realistic materials, controlled depth of field. Absolutely no brands, logos, words, watermark, UI text, QR codes, plaques, fake signage, CGI, exaggerated golden lighting.
```

### F07 — F07-kitchen-kds-real

Arquivo: `site/public/assets/photography/F07-kitchen-kds-real.webp`  
Master: `site/assets/originals/generated/F07-kitchen-kds-real.png`

```text
Use case: photorealistic-natural. A clean modern professional restaurant kitchen with stainless steel pass, adult cook in dark apron partly visible at right, a wall-mounted black landscape monitor at left with completely blank dark charcoal screen, no pixels or UI, clear front three-quarter view suitable for later real screenshot insertion. Practical overhead lighting with warm neutral tones. 4:3 horizontal framing. No claim of real software content. Premium editorial advertising photography, real 35–50mm lens, tactile wood glass metal, refined subtle amber and off-white palette with charcoal accents, realistic materials, controlled depth of field. Absolutely no brands, logos, words, watermark, UI text, QR codes, plaques, fake signage, CGI, exaggerated golden lighting.
```

Revisão: Scene only; blank monitor. Actual KDS screenshot S13/S14 pending; never present as actual product capture.

### F13 — F13-venue-restaurant

Arquivo: `site/public/assets/photography/F13-venue-restaurant.webp`  
Master: `site/assets/originals/generated/F13-venue-restaurant.png`

```text
Use case: photorealistic-natural. A beautiful contemporary Brazilian restaurant dining room, dark walnut tables, curved wood chairs, neutral plaster walls, black metal pendant lamps, off-white tableware, soft window daylight and subtle warm evening ambiance, believable spacious arrangement. No people, no devices. 4:3 landscape. Premium editorial advertising photography, real 35–50mm lens, tactile wood glass metal, refined subtle amber and off-white palette with charcoal accents, realistic materials, controlled depth of field. Absolutely no brands, logos, words, watermark, UI text, QR codes, plaques, fake signage, CGI, exaggerated golden lighting.
```

### F14 — F14-venue-hamburger

Arquivo: `site/public/assets/photography/F14-venue-hamburger.webp`  
Master: `site/assets/originals/generated/F14-venue-hamburger.png`

```text
Use case: photorealistic-natural. A contemporary Brazilian artisanal burger restaurant interior, dark walnut tables and seating, black metal pendant lamps, open kitchen pass in background, warm brick and charcoal details, tasteful relaxed dining atmosphere. No people, no devices, no visible menu text. 4:3 horizontal landscape, premium editorial hospitality photography, real 35mm lens, tactile wood glass ceramic metal, controlled depth of field, consistent charcoal warm neutral campaign. Absolutely no brands, words, logos, watermark, UI, QR codes, NFC plaques, CGI, artificial gold cast.
```

### F15 — F15-venue-snack

Arquivo: `site/public/assets/photography/F15-venue-snack.webp`  
Master: `site/assets/originals/generated/F15-venue-snack.png`

```text
Use case: photorealistic-natural. A clean welcoming contemporary Brazilian neighborhood snack bar interior, compact dark wood tables and stools, off-white tiled counter, black metal details, natural daylight, fresh approachable and realistic rather than luxurious. No people, devices, menu boards or signs. 4:3 horizontal landscape, premium editorial hospitality photography, real 35mm lens, tactile wood glass ceramic metal, controlled depth of field, consistent charcoal warm neutral campaign. Absolutely no brands, words, logos, watermark, UI, QR codes, NFC plaques, CGI, artificial gold cast.
```

### F16 — F16-venue-bar

Arquivo: `site/public/assets/photography/F16-venue-bar.webp`  
Master: `site/assets/originals/generated/F16-venue-bar.png`

```text
Use case: photorealistic-natural. A sophisticated contemporary Brazilian bar interior at dusk, dark walnut bar counter and small dining tables, black metal and warm off-white accents, subtle amber pendant lighting, backlit glassware shelves, realistic inviting atmosphere. No visible bottle labels or signs, no people. 4:3 horizontal landscape, premium editorial hospitality photography, real 35mm lens, tactile wood glass ceramic metal, controlled depth of field, consistent charcoal warm neutral campaign. Absolutely no brands, words, logos, watermark, UI, QR codes, NFC plaques, CGI, artificial gold cast.
```

### F17 — F17-venue-cafe

Arquivo: `site/public/assets/photography/F17-venue-cafe.webp`  
Master: `site/assets/originals/generated/F17-venue-cafe-edited.png`

```text
Use case: photorealistic-natural. A contemporary welcoming Brazilian specialty cafe interior, dark wood tables, off-white plaster walls, black metal espresso machine with no logo, ceramics, filtered natural daylight, restrained warm ambiance. No people, no signs or menu text. 4:3 horizontal landscape, premium editorial hospitality photography, real 35mm lens, tactile wood glass ceramic metal, controlled depth of field, consistent charcoal warm neutral campaign. Absolutely no brands, words, logos, watermark, UI, QR codes, NFC plaques, CGI, artificial gold cast.
```

Edição final:

```text
Use case: precise-object-edit. Keep this cafe photograph unchanged in composition, lighting, camera, furniture, plants and objects. Remove only the tiny gold/light lettering/logo on the upper-left front panel of the black espresso machine. That panel must be plain uniform matte black with no letters, emblem or brand. Preserve everything else exactly. No new text, logos or watermark.
```

Revisão: Removed generated lettering from espresso machine using imagegen edit.

### F18 — F18-final-cta-restaurant

Arquivo: `site/public/assets/photography/F18-final-cta-restaurant.webp`  
Master: `site/assets/originals/generated/F18-final-cta-restaurant.png`

```text
Use case: photorealistic-natural. A wide 2.18:1 panoramic editorial photograph of a contemporary restaurant at blue hour, a long dark walnut dining table leading into a warmly lit off-white and charcoal interior, elegant glassware and low warm lamps, inviting calm atmosphere. Compose the left third in soft deep shadow for later website CTA text; no text in image. Different viewpoint from the hero. Premium hospitality photography, real 35–50mm camera, tactile materials, natural soft window light mixed with restrained warm amber ambiance, controlled depth of field, believable contemporary Brazilian restaurant. No brands, lettering, logos, signage, QR codes, plaques, watermark, generated UI, CGI, people.
```
