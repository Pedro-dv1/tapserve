import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { render, routes, notFoundRoute } from '../.ssr/render.js';

const template = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
const escape = value => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
for (const route of [...routes, notFoundRoute]) {
  const metadata = `<meta name="description" content="${escape(route.description)}" /><meta property="og:title" content="${escape(route.title)} | TapServe" /><meta property="og:description" content="${escape(route.description)}" /><meta property="og:type" content="website" /><meta property="og:locale" content="pt_BR" /><meta property="og:image" content="/assets/social/${route.og}" /><meta name="twitter:card" content="summary_large_image" />`;
  const html = template.replace(/<title>.*?<\/title>/, `<title>${escape(route.title)} | TapServe</title>`).replace('<!--route-meta-->', metadata).replace('<!--app-html-->', render(route.path));
  const directory = new URL(`../dist${route.path === '/' || route.path === '/404' ? '/' : `${route.path}/`}`, import.meta.url);
  await mkdir(directory, { recursive: true });
  await writeFile(new URL(route.path === '/404' ? '404.html' : 'index.html', directory), html);
}
await writeFile(new URL('../dist/robots.txt', import.meta.url), 'User-agent: *\nDisallow: /\n');
await writeFile(new URL('../dist/sitemap.xml', import.meta.url), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>\n');
console.log(`Pré-renderizadas ${routes.length} rotas + 404. Prévia noindex; sitemap vazio até domínio e publicação aprovados.`);
