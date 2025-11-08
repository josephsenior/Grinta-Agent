declare module 'vitest/config' {
  /** Minimal shape for the config helper used in build files */
  export function defineConfig(config: unknown): unknown;
  export default defineConfig;
}

declare module 'vitest' {
  // Keep runtime helpers permissive but avoid `any` for mocks
  export type Mock = unknown;
  export const describe: (name: string, fn: () => void) => void;
  export const it: (name: string, fn: () => void) => void;
  // `expect` is complex; keep as unknown to avoid over-constraining tests here
  export const expect: unknown;
  export const beforeEach: (fn: () => void) => void;
  export const afterEach: (fn: () => void) => void;
  export const vi: any;
}
