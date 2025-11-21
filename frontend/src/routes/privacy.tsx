import React from "react";
import { useTranslation } from "react-i18next";
import { SEO } from "#/components/shared/SEO";

export default function Privacy(): React.ReactElement {
  const { t } = useTranslation();
  return (
    <>
      <SEO
        title="Privacy Policy"
        description="Read Forge's Privacy Policy. Learn how we collect, use, and protect your data on our AI development platform."
        keywords="privacy policy, data protection, GDPR, privacy, Forge"
        noindex
      />
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
            <div className="bg-warning-500/10 border border-warning-500/20 rounded-lg p-4 mb-6">
              <p className="text-warning-400 text-sm font-medium mb-2">
                ⚠️ Beta Version - Legal Review Pending
              </p>
              <p className="text-foreground-secondary text-sm">
                This Privacy Policy is currently in draft form and is subject to
                legal review for GDPR, CCPA, and other privacy regulation
                compliance. For beta testing purposes, please review the key
                privacy practices below. A comprehensive, legally-reviewed
                policy will be provided before the full production launch.
              </p>
            </div>

            <p className="text-foreground-secondary leading-relaxed text-lg">
              {t("PRIVACY$PLACEHOLDER", {
                defaultValue:
                  "Forge is committed to protecting your privacy. This policy describes how we collect, use, and protect your personal information. We will update this policy as needed to comply with applicable privacy laws.",
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
                  {t("PRIVACY$RETENTION", { defaultValue: "Data Retention" })}
                </h2>
                <p className="text-foreground-secondary leading-relaxed">
                  {t("PRIVACY$RETENTION_TEXT", {
                    defaultValue:
                      "Data is retained only as long as necessary for core functionality and compliance. User accounts and associated data are retained while the account is active. Inactive accounts may be deleted after 2 years of inactivity. You may request data deletion at any time.",
                  })}
                </p>
              </div>

              <div className="border-l-4 border-info-500 pl-6">
                <h2 className="text-2xl font-bold text-foreground mb-3">
                  {t("PRIVACY$YOUR_RIGHTS", { defaultValue: "Your Rights" })}
                </h2>
                <p className="text-foreground-secondary leading-relaxed">
                  {t("PRIVACY$YOUR_RIGHTS_TEXT", {
                    defaultValue:
                      "You have the right to access, correct, delete, or export your personal data. You may also object to processing or request data portability. To exercise these rights, please contact us at privacy@forge.ai. We will respond within 30 days as required by GDPR and CCPA.",
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
    </>
  );
}
