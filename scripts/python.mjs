// Prefer the repository virtualenv; IDS_PYTHON supports other managed environments.
import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('../', import.meta.url));
const venv = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.IDS_PYTHON || (existsSync(venv) ? venv : 'python');
const child = spawn(python, process.argv.slice(2), { cwd: root, stdio: 'inherit', env: process.env });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('error', (error) => { console.error(error.message); process.exit(1); });
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
