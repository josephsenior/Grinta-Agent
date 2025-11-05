/**
 * API Configuration for Forge
 * 
 * This module manages API versioning and base URLs for the frontend.
 * 
 * Version Strategy:
 * - During beta: Use non-versioned endpoints for backward compatibility
 * - After launch: Migrate to /api/v1/ prefix
 * - Future: Support multiple versions (/api/v2/, etc.)
 */

/**
 * Available API versions
 */
export enum APIVersion {
  V1 = "v1",
  // V2 = "v2",  // Add when v2 is ready
}

/**
 * Current stable API version
 */
export const CURRENT_API_VERSION = APIVersion.V1;

/**
 * Enable versioned endpoints
 * 
 * Set to true to use /api/v1/ prefix
 * Set to false to use /api/ prefix (beta backward compatibility)
 */
export const USE_VERSIONED_ENDPOINTS = false;  // Set to true after beta

/**
 * Get the API base URL with optional versioning
 * 
 * @param version API version to use (default: current version)
 * @param forceVersion Force versioned endpoint even if USE_VERSIONED_ENDPOINTS is false
 * @returns API base URL (e.g., "/api" or "/api/v1")
 */
export function getAPIBase(
  version: APIVersion = CURRENT_API_VERSION,
  forceVersion = false
): string {
  if (USE_VERSIONED_ENDPOINTS || forceVersion) {
    return `/api/${version}`;
  }
  return "/api";
}

/**
 * Get versioned endpoint path
 * 
 * @param path Endpoint path (e.g., "/settings")
 * @param version API version (default: current)
 * @returns Full versioned path (e.g., "/api/v1/settings")
 */
export function getVersionedPath(
  path: string,
  version: APIVersion = CURRENT_API_VERSION
): string {
  const base = getAPIBase(version);
  // Remove leading slash from path if present
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}/${cleanPath}`;
}

/**
 * API endpoint builder with version support
 * 
 * Usage:
 *   const url = buildAPIUrl("/settings");  // → "/api/settings" (beta)
 *   const url = buildAPIUrl("/settings", { version: APIVersion.V2 });  // → "/api/v2/settings"
 */
export function buildAPIUrl(
  path: string,
  options?: {
    version?: APIVersion;
    forceVersion?: boolean;
    params?: Record<string, string | number | boolean>;
  }
): string {
  const version = options?.version ?? CURRENT_API_VERSION;
  const forceVersion = options?.forceVersion ?? false;
  
  const base = getAPIBase(version, forceVersion);
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  let url = `${base}${cleanPath}`;
  
  // Add query parameters if provided
  if (options?.params) {
    const params = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      params.append(key, String(value));
    });
    url += `?${params.toString()}`;
  }
  
  return url;
}

/**
 * Migration helper: Check if endpoint supports a specific version
 * 
 * This is useful during gradual migration from v1 to v2.
 * You can feature-flag new endpoints to use v2 while keeping old ones on v1.
 */
export function supportsVersion(version: APIVersion): boolean {
  const supportedVersions = [APIVersion.V1];  // Add V2, V3 as you add them
  return supportedVersions.includes(version);
}

