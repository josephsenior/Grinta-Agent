import { defineConfig } from 'vitest/config';
import path from 'path';
import viteTsconfigPaths from 'vite-tsconfig-paths';
import react from '@vitejs/plugin-react';

export default defineConfig({
  resolve: {
    alias: {
      '#': path.resolve(__dirname, 'src'),
      '#/': `${path.resolve(__dirname, 'src')}/`,
    },
  },
  plugins: [
    react(),
    viteTsconfigPaths(),
    {
      name: 'svg-transform',
      transform(code, id) {
        if (id.endsWith('.svg') || id.includes('.svg?')) {
          // Return a simple React component for SVG imports in tests
          return {
            code: `
              import React from 'react';
              export default function SvgComponent(props) {
                return React.createElement('svg', { ...props, 'data-testid': 'mocked-svg' });
              }
              export const ReactComponent = SvgComponent;
            `,
            map: null,
          };
        }
        return null;
      },
    },
  ],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './vitest.setup.ts',
    include: [
      '__tests__/**/*.{test,spec}.?(c|m)[jt]s?(x)',
      'src/**/*.{test,spec}.?(c|m)[jt]s?(x)',
    ],
    exclude: ['**/node_modules/**', 'tests/**', 'playwright/**'],
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'coverage/**',
        'build/**',
        'dist/**',
        'public/**',
        '**/*.config.*',
        '**/*.d.ts',
        'scripts/**',
        'vitest.setup.ts',
        'vitest.config.ts',
        'src/i18n/**',
        'src/test-stubs/**',
        'src/mocks/**',
      ],
    },
  },
});
