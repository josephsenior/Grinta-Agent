/**
 * Helper utility for dynamic imports with proper error handling
 * 
 * This prevents nested dynamic imports from causing unhandled promise rejections
 * and provides a centralized error handling pattern.
 */

import { logger } from "#/utils/logger";

/**
 * Load multiple modules in parallel with error handling
 * 
 * @param imports Array of dynamic import promises
 * @returns Promise that resolves to array of loaded modules
 * @throws Error if any import fails
 * 
 * @example
 * ```ts
 * const [mod1, mod2] = await loadModulesWithErrorHandling([
 *   import('./module1'),
 *   import('./module2')
 * ]);
 * ```
 */
export async function loadModulesWithErrorHandling<T extends readonly unknown[]>(
  imports: readonly [...{ [K in keyof T]: Promise<T[K]> }]
): Promise<T> {
  try {
    return await Promise.all(imports) as T;
  } catch (error) {
    logger.error("Failed to load required modules:", error);
    throw new Error(
      `Module loading failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}

/**
 * Load a single module with error handling
 * 
 * @param importFn Dynamic import function
 * @param moduleName Optional module name for better error messages
 * @returns Promise that resolves to the loaded module
 * @throws Error if import fails
 * 
 * @example
 * ```ts
 * const socket = await loadModuleWithErrorHandling(
 *   () => import('socket.io-client'),
 *   'socket.io-client'
 * );
 * ```
 */
export async function loadModuleWithErrorHandling<T>(
  importFn: () => Promise<T>,
  moduleName?: string
): Promise<T> {
  try {
    return await importFn();
  } catch (error) {
    const name = moduleName || "unknown module";
    logger.error(`Failed to load ${name}:`, error);
    throw new Error(
      `Failed to load ${name}: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}
