/**
 * Framework selection utility for shadcn/ui MCP server
 *
 * This module handles switching between React and Svelte implementations
 * based on environment variables or command line arguments.
 *
 * Usage:
 * - Set FRAMEWORK environment variable to 'react' or 'svelte' or 'vue'
 * - Or use --framework command line argument
 * - Defaults to 'react' if not specified
 */
import { logInfo, logWarning } from './logger.js';
// Default framework
const DEFAULT_FRAMEWORK = 'react';
/**
 * Get the current framework from environment or command line arguments
 * @returns The selected framework ('react' or 'svelte' or 'vue')
 */
export function getFramework() {
    // Check command line arguments first
    const args = process.argv.slice(2);
    const frameworkIndex = args.findIndex((arg) => arg === '--framework' || arg === '-f');
    if (frameworkIndex !== -1 && args[frameworkIndex + 1]) {
        const framework = args[frameworkIndex + 1].toLowerCase();
        if (framework === 'react' || framework === 'svelte' || framework === 'vue') {
            logInfo(`Framework set to '${framework}' via command line argument`);
            return framework;
        }
        else {
            logWarning(`Invalid framework '${framework}' specified. Using default '${DEFAULT_FRAMEWORK}'`);
        }
    }
    // Check environment variable
    const envFramework = process.env.FRAMEWORK?.toLowerCase();
    if (envFramework === 'react' || envFramework === 'svelte' || envFramework === 'vue') {
        logInfo(`Framework set to '${envFramework}' via environment variable`);
        return envFramework;
    }
    // Return default
    logInfo(`Using default framework: '${DEFAULT_FRAMEWORK}'`);
    return DEFAULT_FRAMEWORK;
}
/**
 * Get the axios implementation based on the current framework
 * @returns The appropriate axios implementation
 */
export async function getAxiosImplementation() {
    const framework = getFramework();
    if (framework === 'svelte') {
        // Dynamic import for Svelte implementation
        return import('./axios-svelte.js').then((module) => module.axios);
    }
    else if (framework === 'vue') {
        // Dynamic import for Vue implementation
        return import('./axios-vue.js').then((module) => module.axios);
    }
    else {
        // Dynamic import for React implementation (default)
        return import('./axios.js').then((module) => module.axios);
    }
}
/**
 * Get framework-specific information for help text
 * @returns Framework information object
 */
export function getFrameworkInfo() {
    const framework = getFramework();
    return {
        current: framework,
        repository: framework === 'svelte'
            ? 'huntabyte/shadcn-svelte'
            : framework === 'vue'
                ? 'unovue/shadcn-vue'
                : 'shadcn-ui/ui',
        fileExtension: framework === 'svelte' ? '.svelte' : framework === 'vue' ? '.vue' : '.tsx',
        description: framework === 'svelte'
            ? 'Svelte components from shadcn-svelte'
            : framework === 'vue'
                ? 'Vue components from shadcn-vue'
                : 'React components from shadcn/ui v4',
    };
}
/**
 * Validate framework selection and provide helpful feedback
 */
export function validateFrameworkSelection() {
    const framework = getFramework();
    const info = getFrameworkInfo();
    logInfo(`MCP Server configured for ${framework.toUpperCase()} framework`);
    logInfo(`Repository: ${info.repository}`);
    logInfo(`File extension: ${info.fileExtension}`);
    logInfo(`Description: ${info.description}`);
    // Provide helpful information about switching frameworks
    if (framework === 'react') {
        logInfo('To switch frameworks: set FRAMEWORK=svelte|vue or use --framework svelte|vue');
    }
    else if (framework === 'svelte') {
        logInfo('To switch frameworks: set FRAMEWORK=react|vue or use --framework react|vue');
    }
    else if (framework === 'vue') {
        logInfo('To switch frameworks: set FRAMEWORK=react|svelte or use --framework react|svelte');
    }
    else {
        logInfo('To switch frameworks: set FRAMEWORK=react|svelte or use --framework react|svelte');
    }
}
