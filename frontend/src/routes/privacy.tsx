import React from "react";
import { useTranslation } from "react-i18next";

export default function Privacy(): React.ReactElement {
  const { t } = useTranslation();
  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <div className="card-modern space-y-8">
        <div className="text-center">
          <h1
            data-testid="page-title"
            className="text-4xl font-bold text-foreground mb-4"
          >
            {t("COMMON$PRIVACY_POLICY", { defaultValue: "Privacy Policy" })}
          </h1>
          <div className="w-24 h-1 bg-gradient-to-r from-brand-500 to-accent-500 mx-auto rounded-full mb-6" />
          <p className="text-foreground-secondary text-sm">
            <em>
              {t("PRIVACY$LAST_UPDATED", {
                defaultValue: "Last updated: September 6, 2025",
              })}
            </em>
          </p>
        </div>

        <div className="prose prose-invert max-w-none">
          <p className="text-foreground-secondary leading-relaxed text-lg">
            {t("PRIVACY$PLACEHOLDER", {
              defaultValue:
                "This placeholder Privacy Policy describes how data may be processed. A comprehensive policy will follow.",
            })}
          </p>

          <div className="mt-8 space-y-6">
            <div className="border-l-4 border-brand-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("PRIVACY$DATA_COLLECTION", {
                  defaultValue: "Data Collection",
                })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("PRIVACY$DATA_COLLECTION_TEXT", {
                  defaultValue:
                    "We may collect interaction metadata, logs for debugging, and optional user inputs for feature improvement.",
                })}
              </p>
            </div>

            <div className="border-l-4 border-success-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("PRIVACY$DATA_USAGE", { defaultValue: "Data Usage" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("PRIVACY$DATA_USAGE_TEXT", {
                  defaultValue:
                    "Operational metrics help improve reliability and governance adherence.",
                })}
              </p>
            </div>

            <div className="border-l-4 border-accent-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("PRIVACY$RETENTION", { defaultValue: "Retention" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("PRIVACY$RETENTION_TEXT", {
                  defaultValue:
                    "Data is retained only as long as necessary for core functionality and compliance.",
                })}
              </p>
            </div>

            <div className="border-l-4 border-warning-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("PRIVACY$SECURITY", { defaultValue: "Security" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("PRIVACY$SECURITY_TEXT", {
                  defaultValue:
                    "Best-effort safeguards are applied; no system is perfectly secure.",
                })}
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
