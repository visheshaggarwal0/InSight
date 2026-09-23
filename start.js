const { spawn, execSync } = require('child_process');
const path = require('path');

const isWin = process.platform === 'win32';

console.log('\x1b[36m%s\x1b[0m', '=====================================================');
console.log('\x1b[36m%s\x1b[0m', '   InSight — Telemetry & Review Intelligence         ');
console.log('\x1b[36m%s\x1b[0m', '   Starting FastAPI Backend & Vite Frontend...       ');
console.log('\x1b[36m%s\x1b[0m', '=====================================================\n');

// Clean tree-kill helper for Windows and POSIX
const killTree = (pid) => {
  if (!pid) return;
  try {
    if (isWin) {
      execSync(`taskkill /pid ${pid} /T /F`, { stdio: 'ignore' });
    } else {
      process.kill(-pid, 'SIGTERM');
    }
  } catch {
    // Process already exited
  }
};

// 1. Start FastAPI Backend (direct executable, no shell wrapper to prevent DEP0190)
console.log('\x1b[32m%s\x1b[0m', '[1/2] Launching FastAPI backend on http://127.0.0.1:8000 ...');
const pythonCmd = isWin ? 'python' : 'python3';
const backend = spawn(pythonCmd, [
  '-m', 'uvicorn',
  'app.main:app',
  '--app-dir', 'backend',
  '--reload-dir', 'backend',
  '--host', '127.0.0.1',
  '--port', '8000',
  '--reload'
], {
  cwd: __dirname,
  stdio: 'inherit',
  shell: false
});

// 2. Start Vite Frontend (staggered slightly so backend startup logs don't collide)
let frontend = null;
const timer = setTimeout(() => {
  console.log('\n\x1b[34m%s\x1b[0m', '[2/2] Launching Vite frontend on http://localhost:5173 ...');
  // Pass command string to shell: true on Windows to avoid Node 22/24 DEP0190 warning
  frontend = isWin
    ? spawn('npm run dev', { cwd: path.join(__dirname, 'frontend'), stdio: 'inherit', shell: true })
    : spawn('npm', ['run', 'dev'], { cwd: path.join(__dirname, 'frontend'), stdio: 'inherit', shell: false });

  frontend.on('error', (err) => {
    console.error('\x1b[31m%s\x1b[0m', '[Frontend Error]:', err.message);
  });
}, 700);

// Clean shutdown on Ctrl+C
const shutdown = () => {
  clearTimeout(timer);
  console.log('\n\x1b[33m%s\x1b[0m', '[System] Shutting down InSight servers...');
  if (backend && backend.pid) killTree(backend.pid);
  if (frontend && frontend.pid) killTree(frontend.pid);
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

backend.on('error', (err) => {
  console.error('\x1b[31m%s\x1b[0m', '[Backend Error]:', err.message);
});
