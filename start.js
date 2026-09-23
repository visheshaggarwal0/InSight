const { spawn } = require('child_process');
const path = require('path');

console.log('\x1b[36m%s\x1b[0m', '=====================================================');
console.log('\x1b[36m%s\x1b[0m', '   InSight — Telemetry & Review Intelligence         ');
console.log('\x1b[36m%s\x1b[0m', '   Starting FastAPI Backend & Vite Frontend...       ');
console.log('\x1b[36m%s\x1b[0m', '=====================================================\n');

// Determine command names based on OS
const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';
const pythonCmd = isWin ? 'python' : 'python3';

// 1. Start FastAPI Backend
console.log('\x1b[32m%s\x1b[0m', '[System] Launching FastAPI backend on http://127.0.0.1:8000 ...');
const backend = spawn(pythonCmd, ['-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8000', '--reload'], {
  cwd: __dirname,
  stdio: 'inherit',
  shell: isWin
});

// 2. Start Vite Frontend
console.log('\x1b[34m%s\x1b[0m', '[System] Launching Vite frontend on http://localhost:5173 ...');
const frontend = spawn(npmCmd, ['run', 'dev'], {
  cwd: path.join(__dirname, 'frontend'),
  stdio: 'inherit',
  shell: isWin
});

// Clean shutdown on Ctrl+C
const shutdown = () => {
  console.log('\n\x1b[33m%s\x1b[0m', '[System] Shutting down InSight servers...');
  backend.kill();
  frontend.kill();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

backend.on('error', (err) => {
  console.error('\x1b[31m%s\x1b[0m', '[Backend Error]:', err.message);
});

frontend.on('error', (err) => {
  console.error('\x1b[31m%s\x1b[0m', '[Frontend Error]:', err.message);
});
