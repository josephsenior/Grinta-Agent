#!/usr/bin/env node
const { spawnSync } = require('child_process');
const path = require('path');

function run(cmd, args, opts = {}) {
  console.log(`> ${cmd} ${args.join(' ')}`);
  const res = spawnSync(cmd, args, { stdio: 'inherit', shell: false, ...opts });
  return res;
}

const root = path.resolve(__dirname, '..');
process.chdir(root);

// Run i18n step first
const make = run(process.platform === 'win32' ? 'node' : 'node', ['scripts/make-i18n-translations.cjs']);
if (make.status !== 0) {
  console.error('make-i18n failed');
  process.exit(make.status || 1);
}

// Try react-router dev first
const env = Object.create(process.env);
env.VITE_MOCK_API = 'false';

let cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
let tryReactRouter = run(cmd, ['cross-env', 'VITE_MOCK_API=false', 'react-router', 'dev'], { env });

if (tryReactRouter.status === 0) {
  process.exit(0);
}

console.warn('react-router dev failed — falling back to vite dev');
// Fallback to vite
let viteCmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
let tryVite = run(viteCmd, ['cross-env', 'VITE_MOCK_API=false', 'vite'], { env });
process.exit(tryVite.status || 0);
