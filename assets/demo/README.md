# Local demonstration images

AI-generated illustrative food photos, requested for the local customer-table preview. These are not photographs of a real restaurant's products. Built-in image_gen was used; no external image source or paid third-party connector was invoked.

- burger.png: single artisanal cheeseburger on a white plate, brioche/beef/cheddar/lettuce/tomato/pickles.
- fries.png: golden french fries in a white ceramic bowl with ketchup.
- lemonade.png: fresh lime lemonade, ice and mint in a clear glass.

Shared prompt: photorealistic professional restaurant-menu photograph; square, tight three-quarter composition, warm beige tabletop, soft natural daylight, clean neutral background; no people, text, logos or collage. Each prompt specified its corresponding food above.

Exact generation prompts:

1. Photorealistic professional food photograph for a restaurant menu, square composition. One artisanal cheeseburger with a glossy toasted brioche bun, grilled beef patty, melted cheddar, crisp lettuce, tomato and pickles, on a small white plate on a warm light beige tabletop. Tight appetizing three-quarter view, burger fills most of the frame, soft natural daylight, realistic textures, clean neutral background. No people, no text, no logo, no collage.
2. Photorealistic professional food photograph for a restaurant menu, square composition. A generous portion of golden crispy french fries in a small white ceramic bowl on a warm light beige tabletop, tiny ramekin of ketchup nearby. Tight appetizing three-quarter view, fries fill most of the frame, soft natural daylight, realistic textures, clean neutral background. No people, no text, no logo, no collage.
3. Photorealistic professional food photograph for a restaurant menu, square composition. A tall clear glass of fresh lime lemonade with ice, lime slice and mint, condensation on the glass, on a warm light beige tabletop. Tight appetizing three-quarter view, drink fills most of the frame, soft natural daylight, realistic textures, clean neutral background. No people, no text, no logo, no collage.

Original generated PNGs are preserved here. Imported product media is WEBP, processed by the existing backend image validator and stored in backend/media/products with generated names. UI reads the real product-image API using customer access. Existing product photos and credentials are not overwritten.
