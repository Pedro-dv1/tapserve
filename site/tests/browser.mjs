import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { routes } from '../src/data/routes.ts';
import { auditPages, auditInteractions } from './browser-audit.mjs';
import { auditMediaAndLoader } from './media-loader-audit.mjs';

const base = 'http://127.0.0.1:4321';
const output = fileURLToPath(new URL('../test-results', import.meta.url));
await mkdir(output, { recursive: true });
const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' };
if (process.env.TAPSERVE_MCP_SESSION) headers['Mcp-Session-Id'] = process.env.TAPSERVE_MCP_SESSION;
let id = 0;
async function rpc(method, params) {
  const response = await fetch('http://127.0.0.1:8931/mcp', { method: 'POST', headers, body: JSON.stringify({ jsonrpc: '2.0', id: ++id, method, params }) });
  if (response.headers.get('mcp-session-id')) headers['Mcp-Session-Id'] = response.headers.get('mcp-session-id');
  const raw = await response.text();
  const events = raw.split('\n').filter(line => line.startsWith('data: '));
  const data = JSON.parse(events.length ? events.at(-1).slice(6) : raw);
  if (data.error) throw new Error(JSON.stringify(data.error));
  return data.result;
}
async function run(fn, options) {
  const result = await rpc('tools/call', { name: 'browser_run_code_unsafe', arguments: { code: `async page => (${fn.toString()})(page, ${JSON.stringify(options)})` } });
  const text = result.content.filter(content => content.type === 'text').map(content => content.text).join('\n');
  if (result.isError) throw new Error(text);
  return JSON.parse(text.match(/### Result\n([\s\S]*?)\n### (?:Ran|Page|Open)/)?.[1] ?? text.replace(/^### Result\n/, ''));
}
const evidence = { date: new Date().toISOString(), transport: 'playwright-local MCP :8931; no local browser process', pages: [], interactions: null };
try {
  if (!headers['Mcp-Session-Id']) await rpc('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'tapserve-site-audit', version: '1' } });
  await rpc('tools/call', { name: 'browser_navigate', arguments: { url: base } });
  for (const width of [360, 390, 430, 768, 1024, 1280, 1440, 1920]) {
    evidence.pages.push(await run(auditPages, { base, output, paths: [...routes.map(route => route.path), '/inexistente/rota'], width }));
    console.log(`PASS: ${width}px × ${routes.length + 1} routes; screenshots, proportions, alignment, static network and console.`);
  }
  evidence.interactions = await run(auditInteractions, { base, output });
  console.log('PASS: real-component demo, exact totals, local calls, reset, keyboard, motion and isolation.');
  evidence.mediaAndLoader = await run(auditMediaAndLoader, { base, output });
  console.log('PASS: every product image, real loading, timeout/recovery and reduced motion.');
} catch (error) { evidence.error = error.message; throw error; }
finally { await writeFile(`${output}/browser.json`, JSON.stringify(evidence, null, 2)); }
