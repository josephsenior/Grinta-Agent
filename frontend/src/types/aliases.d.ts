/// <reference types="@testing-library/jest-dom" />

// Provide a loose ambient module for the internal test-utils entry so
// editor TypeScript can resolve imports like `import { renderWithProviders } from "test-utils";`
declare module "test-utils" {
  import type { RenderResult, RenderOptions } from "@testing-library/react";
  import type { AppStore, RootState } from "../store";

  export type RenderWithProvidersResult = RenderResult & { store: AppStore };

  export function renderWithProviders(
    ui: import("react").ReactElement,
    options?: RenderOptions & {
      preloadedState?: Partial<RootState>;
      store?: AppStore;
    },
  ): RenderWithProvidersResult;

  export function setupStore(preloadedState?: Partial<RootState>): AppStore;

  export function createAxiosNotFoundErrorObject(): import("axios").AxiosError;

  export const setPlaywrightFlag: (v: boolean) => void;
  export const mockSettings404: () => boolean;

  export default {};
}

// Wildcard alias used across the repo (maps to ./src/* in tsconfig). Declare
// a permissive module so editor errors are removed; specific modules will
// still have real types from their source files when available.
declare module "#/*" {
  const value: any;
  export default value;
}
