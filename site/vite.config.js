import { defineConfig } from 'vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

const root = path.dirname(fileURLToPath(import.meta.url));
const catalogue = JSON.parse(readFileSync(path.join(root, 'src/data/product-catalog.json'), 'utf8'));
for (const product of catalogue.products.filter(product => product.has_image)) {
  const image = readFileSync(path.join(root, `public/assets/catalog/${product.id}.webp`));
  if (image.toString('ascii', 0, 4) !== 'RIFF' || image.toString('ascii', 8, 12) !== 'WEBP') throw new Error(`Foto original inválida: ${product.name}`);
  if (product.photos.length || product.has_video) throw new Error(`Exporte as mídias adicionais antes de apresentar ${product.name} na demo.`);
}

export default defineConfig({
  resolve: { dedupe: ['react', 'react-dom'] },
  plugins: [{
    name: 'isolated-product-demo',
    enforce: 'pre',
    resolveId(source, importer) {
      if (importer?.replaceAll('\\', '/').includes('/frontend/src/') && /(?:^|\/)lib\/api(?:\.ts)?$/.test(source)) return path.join(root, 'src/demo/api.ts');
    },
    transform(code, id) {
      if (id.replaceAll('\\', '/').endsWith('/frontend/src/components/Interface.tsx')) {
        const original = 'src={`/api/v1/public/products/${id}/image/${version ? `?v=${encodeURIComponent(version)}` : \'\'}`}';
        if (!code.includes(original)) this.error('O componente ProductImage mudou; revise o mapeamento de fotos da demonstração.');
        return code.replace(original, 'src={`/assets/catalog/${id}.webp`}');
      }
    },
  }],
  server: { host: '127.0.0.1', port: 4321, strictPort: true, hmr: false },
  build: { sourcemap: false, manifest: true, rollupOptions: { input: { main: path.join(root, 'index.html'), demo: path.join(root, 'produto-demo.html') } } },
});
