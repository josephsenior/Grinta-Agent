import React from "react";
import { useTranslation } from "react-i18next";

export default function Terms(): React.ReactElement {
  const { t } = useTranslation();
  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <div className="card-modern space-y-8">
        <div className="text-center">
          <h1
            data-testid="page-title"
            className="text-4xl font-bold text-foreground mb-4"
          >
            {t("TOS$TERMS", { defaultValue: "Terms" })}
          </h1>
          <div className="w-24 h-1 bg-gradient-to-r from-brand-500 to-accent-500 mx-auto rounded-full mb-6" />
          <p className="text-foreground-secondary text-sm">
            <em>
              {t("TOS$LAST_UPDATED", {
                defaultValue: "Last updated: September 6, 2025",
              })}
            </em>
          </p>
        </div>

        <div className="prose prose-invert max-w-none">
          <p className="text-foreground-secondary leading-relaxed text-lg">
            {t("TOS$PLACEHOLDER", {
              defaultValue:
                "These placeholder Terms outline basic usage concepts and will be replaced with a formal legal document.",
            })}
          </p>

          <div className="mt-8 space-y-6">
            <div className="border-l-4 border-brand-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("TOS$SECTION_1", { defaultValue: "1. Use of the Service" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("TOS$USE_SERVICE", {
                  defaultValue:
                    "You agree to use the platform responsibly and comply with all applicable laws.",
                })}
              </p>
            </div>

            <div className="border-l-4 border-success-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("TOS$SECTION_2", { defaultValue: "2. Ownership" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("TOS$OWNERSHIP", {
                  defaultValue:
                    "Generated code belongs to you unless otherwise specified by integrated third-party licenses.",
                })}
              </p>
            </div>

            <div className="border-l-4 border-accent-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("TOS$SECTION_3", { defaultValue: "3. Acceptable Use" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("TOS$ACCEPTABLE_USE", {
                  defaultValue:
                    "No malicious, abusive, or unauthorized intrusion activities are permitted.",
                })}
              </p>
            </div>

            <div className="border-l-4 border-warning-500 pl-6">
              <h2 className="text-2xl font-bold text-foreground mb-3">
                {t("TOS$SECTION_4", { defaultValue: "4. Disclaimer" })}
              </h2>
              <p className="text-foreground-secondary leading-relaxed">
                {t("TOS$DISCLAIMER", {
                  defaultValue:
                    'The service is provided "as is" without warranties of any kind.',
                })}
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
