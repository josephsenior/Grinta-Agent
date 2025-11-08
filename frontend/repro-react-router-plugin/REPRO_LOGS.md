Repro run logs

Environment: Windows, Node v22.x (the environment used to run these commands in the workspace)

Commands run

1. Install (first attempt with Vite 5 caused ERESOLVE; final install used Vite 4 + --legacy-peer-deps):

npm install --legacy-peer-deps --no-audit --no-fund

Output (summary):

added 184 packages in 21s

2. react-router CLI (attempt with an unsupported flag):

npx react-router dev --loglevel verbose

Output:

ArgError: unknown or unexpected option: --loglevel
at arg (...node_modules\arg\index.js:132:13)
at run2 (...@react-router/dev\dist\cli\index.js:2336:37)
at Object.<anonymous> (...\dist\cli\index.js:2415:1)

3. react-router CLI (plain invocation):

npx react-router dev

Output (error observed):

failed to load config from C:\Users\youse\Bureau\Joseph\Forge\frontend\repro-react-router-plugin\vite.config.ts
SyntaxError: The requested module 'react-router' does not provide an export named 'createRequestHandler'
at ModuleJobSync.runSync (node:internal/modules/esm/module_job:384:37)
at ModuleLoader.importSyncForRequire (node:internal/modules/esm/module_job:329:47)
at Object.loadESMFromCJS [as .mjs] (...\node_modules\@react-router\dev\dist\vite.js:1246:19)

4. Quick package inspection (partial):

npm ls react-router react-router-dom @react-router/dev --depth 0

repro-react-router-plugin@0.0.0
├── @react-router/dev@0.0.0-nightly-fdd3ab3a6-20250809
└── react-router-dom@6.30.1

Diagnosis / notes

- The installed `@react-router/dev` nightly expects runtime helpers exported from a matching `react-router` package (v7 dev/nightly). In this environment we don't have a compatible `react-router` published, so when the CLI tries to load the Vite config it hits the missing export `createRequestHandler` and crashes early.
- Because the CLI fails while importing the Vite config (before plugin-detection checks), we cannot yet observe the "React Router Vite plugin not found" message in this fresh repro without providing a compatible `react-router` implementation.

Next steps you can ask me to take:

- Create a tiny local mock `react-router` module inside `node_modules/` that exports the symbols the CLI expects so the CLI can load the config and continue to the plugin-detection stage. This is the fastest way to reproduce the detection error directly.
- Or I can craft a small standalone repro repo that vendors a compatible `react-router` build (if a published prerelease exists), but that requires published packages.
- Or you can use the logs above in the issue draft; they already demonstrate a crash path the CLI should handle more gracefully.

The repro files (vite.config.ts, src/, package.json) are in this folder. See README.md for run instructions.

Local reproduce run (reproduce.log)

```
React Router Vite plugin not found in Vite config

Process exited with code 1
```

Added artifacts

- `scripts/run-reproduce.cjs` — local runner that writes `reproduce.log`.
- `package.json` scripts: `reproduce` and `reproduce:log`.
- `.github/workflows/repro-react-router-plugin.yml` — manual workflow (workflow_dispatch) that installs deps, runs `reproduce:log`, and uploads `reproduce.log` as an artifact for maintainers to inspect.
