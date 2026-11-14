// Independent Node IPC probes; only freshly created pipes and child processes.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, realpathSync, writeFileSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const root = realpathSync(fileURLToPath(new URL('..', import.meta.url)));
const { values } = parseArgs({ options: { output: { type: 'string' } } });
assert.ok(values.output, '--output is required');
const output = path.resolve(values.output);
assert.ok(!path.relative(root, output).startsWith('..') && !path.isAbsolute(path.relative(root, output)) && !existsSync(output), 'Use a NEW report inside this workspace');
mkdirSync(path.dirname(output), { recursive: true });
const parent = path.relative(root, realpathSync(path.dirname(output)));
assert.ok(!parent.startsWith('..') && !path.isAbsolute(parent));

const report = { pid: process.pid, parent_pid: process.ppid, executable: process.execPath,
  node: process.version, libuv: process.versions.uv, cwd: realpathSync('.'), subprocesses: {} };
for (const stdio of ['inherit', 'ignore', 'pipe']) {
  report.subprocesses[stdio] = await new Promise(resolve => {
    let child;
    try { child = spawn(process.execPath, ['--version'], { stdio, windowsHide: true }); }
    catch (error) { resolve({ passed: false, error: error.code, syscall: error.syscall }); return; }
    let result = '';
    child.stdout?.on('data', data => { result += data; });
    const timer = setTimeout(() => { child.kill(); }, 5000);
    child.on('error', error => { clearTimeout(timer); resolve({ passed: false, error: error.code, syscall: error.syscall }); });
    child.on('close', code => { clearTimeout(timer); resolve({ passed: code === 0 && (stdio !== 'pipe' || result.trim() === process.version), exit_code: code }); });
  });
}
report.own_named_pipe = await new Promise(resolve => {
  const name = process.platform === 'win32' ? `\\\\.\\pipe\\tapserve_node_probe_${randomUUID()}` : undefined;
  if (!name) { resolve({ passed: false, reason: 'Windows-specific pipe probe' }); return; }
  let client;
  const server = net.createServer(socket => { socket.on('error', () => {}); socket.on('data', data => socket.end(data)); });
  const finish = result => { clearTimeout(timer); client?.destroy(); server.close(); resolve(result); };
  const timer = setTimeout(() => finish({ passed: false, reason: 'own_pipe_timeout' }), 5000);
  server.on('error', error => finish({ passed: false, error: error.code, syscall: error.syscall }));
  server.listen(name, () => {
    client = net.connect(name);
    client.on('error', error => finish({ passed: false, error: error.code, syscall: error.syscall }));
    client.on('connect', () => client.write('ping'));
    client.on('data', data => finish({ passed: data.toString() === 'ping' }));
  });
});
report.build_gate_passed = report.subprocesses.pipe.passed;
writeFileSync(output, JSON.stringify(report, null, 2), { flag: 'wx' });
console.log(JSON.stringify(report, null, 2));
process.exitCode = report.build_gate_passed ? 0 : 2;
