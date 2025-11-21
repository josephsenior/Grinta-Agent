import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { RuntimeLoadingScreen } from "./runtime-loading-screen";
import { InlineLLMSetup } from "./inline-llm-setup";
import { useSettings } from "#/hooks/query/use-settings";
import { useBackgroundRuntimeInit } from "#/hooks/use-background-runtime-init";

interface BetaWrapperProps {
  children: React.ReactNode;
}

/**
 * Beta Wrapper - Handles parallel startup flow:
 * 1. Shows LLM setup if no API key configured
 * 2. Starts runtime initialization in background
 * 3. Shows loading screen while runtime initializes
 * 4. Renders children when ready
 */
export function BetaWrapper({ children }: BetaWrapperProps) {
  const { t } = useTranslation();
  const { data: settings, isLoading: settingsLoading } = useSettings();
  const runtimeStatus = useBackgroundRuntimeInit();
  const [setupComplete, setSetupComplete] = useState(false);

  // Check if LLM is configured
  const hasLLMConfig = Boolean(
    settings?.LLM_MODEL && settings?.LLM_API_KEY_SET,
  );

  // Show loading while settings are being fetched
  if (settingsLoading) {
    return <RuntimeLoadingScreen />;
  }

  // Show LLM setup if not configured
  if (!hasLLMConfig && !setupComplete) {
    return <InlineLLMSetup onComplete={() => setSetupComplete(true)} />;
  }

  // Show runtime loading screen while runtime initializes
  if (
    runtimeStatus.isInitializing ||
    (!runtimeStatus.isReady && !runtimeStatus.error)
  ) {
    return <RuntimeLoadingScreen />;
  }

  // Show error if runtime initialization failed
  if (runtimeStatus.error) {
    return (
      <div className="fixed inset-0 bg-background-primary flex items-center justify-center">
        <div className="max-w-md p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-foreground mb-2">
            {t("beta.initializationFailed", "Initialization Failed")}
          </h2>
          <p className="text-sm text-foreground-secondary mb-4">
            {runtimeStatus.error}
          </p>
          <button
            type="button"
            onClick={() => {
              window.location.reload();
            }}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
          >
            {t("common.retry", "Retry")}
          </button>
        </div>
      </div>
    );
  }

  // Render children when everything is ready
  return children as React.ReactElement;
}
