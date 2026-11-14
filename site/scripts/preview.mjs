import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.xml': 'application/xml', '.txt': 'text/plain' };
const server = createServer(async (request, response) => {
  const headers = { 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY', 'Cache-Control': 'no-store' };
  if (!['GET', 'HEAD'].includes(request.method ?? '')) { response.writeHead(405, { ...headers, Allow: 'GET, HEAD' }); response.end(); return; }
  try {
    const decoded = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    if (decoded === '/produto-demo.html') headers['X-Frame-Options'] = 'SAMEORIGIN';
    let file = path.resolve(root, `.${decoded}`);
    if (!file.startsWith(root + path.sep) && file !== path.resolve(root)) throw new Error('Invalid path');
    let found = true;
    try { if ((await stat(file)).isDirectory()) file = path.join(file, 'index.html'); await stat(file); }
    catch { file = path.join(root, '404.html'); found = false; }
    const body = await readFile(file);
    response.writeHead(found ? 200 : 404, { ...headers, 'Content-Type': types[path.extname(file)] ?? 'application/octet-stream' });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch { response.writeHead(400, headers); response.end('Endereço inválido.'); }
});
server.listen(4321, '127.0.0.1', () => console.log('TapServe site: http://127.0.0.1:4321'));
