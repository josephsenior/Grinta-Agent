import React from "react";
import { useTranslation } from "react-i18next";
import { Button } from "#/components/ui/button";

interface AnalyticsConsentFormModalProps {
  onClose: () => void;
}

export function AnalyticsConsentFormModal({ onClose }: AnalyticsConsentFormModalProps) {
  const { t } = useTranslation();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-[var(--bg-primary)] p-6 shadow-xl">
        <h2 className="mb-4 text-xl font-bold">{t("analytics.title", "Analytics Consent")}</h2>
        <p className="mb-6 text-[var(--text-secondary)]">
          {t("analytics.description", "We use analytics to improve our service. Do you consent to sharing anonymized usage data?")}
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            {t("common.decline", "Decline")}
          </Button>
          <Button onClick={onClose}>
            {t("common.accept", "Accept")}
          </Button>
        </div>
      </div>
    </div>
  );
}
