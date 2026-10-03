import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
export function startBackend() {
  const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
  if (!existsSync(python)) throw new Error('Python environment missing. Run python3 -m venv .venv and install requirements-dev.txt first.');
  return spawn(python, ['-m', 'backend'], { stdio: 'inherit' });
}
if (process.argv[1]?.endsWith('backend.mjs')) {
  const child = startBackend();
  child.on('exit', (code) => { process.exitCode = code ?? 1; });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
}
