import { Forge } from "./forge-axios";

/**
 * Feature flag information for UI display
 */
export interface FeatureFlagInfo {
  enabled: boolean;
  coming_soon: boolean;
  tier: string;
  description: string;
}

/**
 * Feature flags response from API
 */
export interface FeatureFlagsResponse {
  security_risk_assessment: FeatureFlagInfo;
  custom_runtime_images: FeatureFlagInfo;
}

/**
 * Fetch feature flags from the backend
 * @returns Promise resolving to feature flags information
 */
export async function getFeatureFlags(): Promise<FeatureFlagsResponse> {
  const response = await Forge.get<FeatureFlagsResponse>("/api/v1/features");
  return response.data;
}
