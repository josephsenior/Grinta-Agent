/**
 * Simple console logging wrapper
 * All logging goes to stderr to avoid interfering with JSON-RPC stdout communication
 * All methods use console.error under the hood
 */

/**
 * Simple error logging function
 */
export function logError(message: string, error?: any): void {
  const errorMessage = error instanceof Error ? error.message : String(error);
  console.error(`ERR: ${message} - ${errorMessage}`);
  if (error instanceof Error && error.stack) {
    console.error(`Stack: ${error.stack}`);
  }
}

/**
 * Simple warning logging function
 */
export function logWarning(message: string): void {
  console.error(`WARN: ${message}`);
}

/**
 * Simple info logging function
 */
export function logInfo(message: string): void {
  console.error(`INFO: ${message}`);
}
