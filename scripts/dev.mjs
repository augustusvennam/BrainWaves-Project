import { spawn } from 'node:child_process';
import { startBackend } from './backend.mjs';
const backend = startBackend();
const frontend = spawn(process.execPath, ['node_modules/vite/bin/vite.js'], { stdio: 'inherit' });
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  backend.kill('SIGTERM');
  frontend.kill('SIGTERM');
  process.exitCode = code;
}
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => stop());
for (const child of [backend, frontend]) {
  child.on('error', (error) => { console.error(error.message); stop(1); });
  child.on('exit', (code) => stop(code ?? 1));
}
