import { defineConfig } from 'vitest/config';
import path from 'path';

// Use the current working directory for resolving project paths. Avoids
// relying on `import.meta.url` which can trigger errors when the TS project
// is configured to emit CommonJS.
const projectRoot = process.cwd();

export default defineConfig({
  root: 'frontend',
  resolve: {
    alias: {
      '#': path.resolve(projectRoot, 'frontend/src'),
      '#/': `${path.resolve(projectRoot, 'frontend/src')}/`,
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './vitest.setup.ts',
  },
});
