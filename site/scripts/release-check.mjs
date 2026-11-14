import { readFile } from 'node:fs/promises';
const state = JSON.parse(await readFile(new URL('../../docs/site/RELEASE_APPROVALS.json', import.meta.url), 'utf8'));
const pending = Object.entries(state).filter(([, value]) => !value.approved || !value.reviewer || !value.date || !value.evidence);
if (pending.length) { console.error(`PUBLICAÇÃO BLOQUEADA: ${pending.map(([name]) => name).join(', ')}. Consulte docs/site/RELEASE_APPROVALS.json e as minutas internas.`); process.exitCode = 1; }
else console.log('Aprovações documentadas. Publicação ainda exige autorização explícita do proprietário.');
