declare namespace React {
  interface FC<P = Record<string, never>> {
    (props: P): any;
  }
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

declare module 'react' {
  export type FC<P = Record<string, never>> = React.FC<P>;
  export const useState: <T = any>(
    initial?: T
  ) => [T, (value: T | ((prev: T) => T)) => void];
  export const useEffect: (
    effect: (...args: any[]) => void | (() => void),
    deps?: any[]
  ) => void;
  const ReactDefault: {
    FC: React.FC;
  };
  export default ReactDefault;
}

declare module '@testing-library/react' {
  export const render: (...args: any[]) => any;
  export const screen: Record<string, (...args: any[]) => any>;
}

declare module 'axios' {
  const axios: any;
  export default axios;
}

declare module '@octokit/rest' {
  export class Octokit {
    constructor(options?: any);
    repos: Record<string, (...args: any[]) => any>;
    pulls: Record<string, (...args: any[]) => any>;
  }
}

declare module 'react-select' {
  const ReactSelect: React.FC<any>;
  export default ReactSelect;
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

interface ImportMetaEnv {
  readonly VITE_GITHUB_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare const expect: (...args: any[]) => any;

