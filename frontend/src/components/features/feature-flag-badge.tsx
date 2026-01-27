import React from "react";
import { Sparkles, Lock } from "lucide-react";
import { Badge } from "#/components/ui/badge";
import { FeatureFlagInfo } from "#/api/features";
import { cn } from "#/utils/utils";

interface FeatureFlagBadgeProps {
  feature: FeatureFlagInfo;
  className?: string;
  showIcon?: boolean;
}

/**
 * Badge component for displaying feature flag status
 * Shows "Coming Soon" for disabled features and "Pro" for premium features
 */
export function FeatureFlagBadge({
  feature,
  className,
  showIcon = true,
}: FeatureFlagBadgeProps) {
  if (feature.enabled) {
    return null; // Don't show badge if feature is enabled
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        "inline-flex items-center gap-1.5 border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400",
        className,
      )}
    >
      {showIcon && feature.coming_soon && (
        <Sparkles className="h-3 w-3" aria-hidden="true" />
      )}
      {showIcon && feature.tier === "pro" && !feature.coming_soon && (
        <Lock className="h-3 w-3" aria-hidden="true" />
      )}
      <span>
        {feature.coming_soon ? "Coming Soon" : `${feature.tier.toUpperCase()}`}
      </span>
    </Badge>
  );
}

interface FeatureComingSoonProps {
  featureName: string;
  description?: string;
  className?: string;
}

/**
 * Component for displaying a "Coming Soon" message for disabled features
 */
export function FeatureComingSoon({
  featureName,
  description,
  className,
}: FeatureComingSoonProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center dark:border-gray-700 dark:bg-gray-900",
        className,
      )}
    >
      <Sparkles className="mb-4 h-12 w-12 text-amber-500" />
      <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
        {featureName} - Coming Soon
      </h3>
      {description && (
        <p className="mb-4 max-w-md text-sm text-gray-600 dark:text-gray-400">
          {description}
        </p>
      )}
      <p className="text-sm text-gray-500 dark:text-gray-500">
        This feature is part of the Pro tier and will be available soon.
      </p>
      <a
        href="https://forge.ai/pricing"
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
      >
        Learn more about Pro features →
      </a>
    </div>
  );
}
