import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const cwd = process.cwd();
const emptyModuleURL = pathToFileURL(path.resolve(cwd, 'scripts', 'empty-vitest-stub.mjs')).href;

export async function resolve(specifier, context, defaultResolve) {
  try {
    if (typeof specifier === 'string' && (specifier.includes('@vitest') || specifier === 'vitest')) {
      console.error('LOADER: intercept resolve for', specifier);
      return { url: emptyModuleURL };
    }
  } catch (e) {
    // ignore
  }
  return defaultResolve(specifier, context, defaultResolve);
}

export async function load(url, context, defaultLoad) {
  if (url === emptyModuleURL) {
    console.error('LOADER: providing empty stub for', url);
    return { format: 'module', source: 'export default {}' };
  }
  return defaultLoad(url, context, defaultLoad);
}
