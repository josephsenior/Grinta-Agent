import React from "react";
import { useTranslation } from "react-i18next";
import { SEO } from "#/components/shared/SEO";

export default function Terms(): React.ReactElement {
  const { t } = useTranslation();
  return (
    <>
      <SEO
        title="Terms of Service"
        description="Read Forge's Terms of Service. Understand the terms and conditions for using our AI development platform."
        keywords="terms of service, legal, terms, conditions, Forge"
        noindex
      />
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
            <div className="bg-warning-500/10 border border-warning-500/20 rounded-lg p-4 mb-6">
              <p className="text-warning-400 text-sm font-medium mb-2">
                ⚠️ Beta Version - Legal Review Pending
              </p>
              <p className="text-foreground-secondary text-sm">
                These Terms of Service are currently in draft form and are
                subject to legal review. For beta testing purposes, please
                review the key terms below. A comprehensive legal document will
                be provided before the full production launch.
              </p>
            </div>

            <p className="text-foreground-secondary leading-relaxed text-lg">
              {t("TOS$PLACEHOLDER", {
                defaultValue:
                  "By using Forge, you agree to the following terms and conditions. These terms may be updated, and continued use constitutes acceptance of the updated terms.",
              })}
            </p>

            <div className="mt-8 space-y-6">
              <div className="border-l-4 border-brand-500 pl-6">
                <h2 className="text-2xl font-bold text-foreground mb-3">
                  {t("TOS$SECTION_1", {
                    defaultValue: "1. Use of the Service",
                  })}
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
    </>
  );
}
