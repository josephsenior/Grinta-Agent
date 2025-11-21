import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { BrandButton } from "../brand-button";
import { logger } from "#/utils/logger";

export function InstallSlackAppAnchor() {
  const { t } = useTranslation();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleInstall = async () => {
    setLoading(true);
    setError(null);

    try {
      // TODO: Get actual user_id from auth context
      const userId = "current-user";
      const redirectUrl = window.location.href;

      const response = await fetch(
        `/api/slack/install?user_id=${encodeURIComponent(userId)}&redirect_url=${encodeURIComponent(redirectUrl)}`,
      );

      if (!response.ok) {
        throw new Error("Failed to get Slack install URL");
      }

      const data = await response.json();
      window.open(data.url, "_blank", "noreferrer noopener");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to install Slack app",
      );
      logger.error("Slack install error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="install-slack-app-button" className="py-9">
      <BrandButton
        type="button"
        variant="primary"
        className="w-55"
        onClick={handleInstall}
        isDisabled={loading}
      >
        {loading ? t(I18nKey.HOME$LOADING) : t(I18nKey.SLACK$INSTALL_APP)}
      </BrandButton>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
