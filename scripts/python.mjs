import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
if (!existsSync(python)) throw new Error('Python environment missing. Create .venv and install requirements-dev.txt first.');
const child = spawn(python, process.argv.slice(2), { stdio: 'inherit' });
child.on('error', error => { console.error(error.message); process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 1; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
