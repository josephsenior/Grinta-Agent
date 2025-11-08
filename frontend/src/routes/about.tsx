import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

export default function About(): React.ReactElement {
  const { t } = useTranslation();
  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <div className="card-modern space-y-8">
        <div className="text-center">
          <h1
            data-testid="page-title"
            className="text-4xl font-bold text-foreground mb-4"
          >
            {t("ABOUT")}
          </h1>
          <div className="w-24 h-1 bg-gradient-to-r from-brand-500 to-accent-500 mx-auto rounded-full"></div>
        </div>
        
        <div className="prose prose-invert max-w-none">
          <p className="text-foreground-secondary leading-relaxed text-lg">
            {t(I18nKey.HOME$Forge_DESCRIPTION)}
          </p>
          
          <div className="mt-8">
            <h2 className="text-2xl font-bold text-foreground mb-4">{t("MISSION")}</h2>
            <p className="text-foreground-secondary leading-relaxed">
              {t("MISSION$DESCRIPTION", {
                defaultValue:
                  "Empower teams with an always-on engineer that writes, reviews, tests, and iterates safely within governed constraints.",
              })}
            </p>
          </div>
          
          <div className="mt-8">
            <h2 className="text-2xl font-bold text-foreground mb-6">{t("CORE_CAPABILITIES")}</h2>
            <ul className="space-y-4">
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 bg-brand-500 rounded-full mt-2 flex-shrink-0"></div>
                <span className="text-foreground-secondary">
                  {t("AUTOMATED_CODING", {
                    defaultValue: "Automated coding & refactoring",
                  })}
                </span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 bg-success-500 rounded-full mt-2 flex-shrink-0"></div>
                <span className="text-foreground-secondary">
                  {t("TEST_GENERATION", {
                    defaultValue: "Test generation & maintenance",
                  })}
                </span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 bg-accent-500 rounded-full mt-2 flex-shrink-0"></div>
                <span className="text-foreground-secondary">
                  {t("FAILURE_TAXONOMY", {
                    defaultValue: "Failure taxonomy driven remediation",
                  })}
                </span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 bg-warning-500 rounded-full mt-2 flex-shrink-0"></div>
                <span className="text-foreground-secondary">
                  {t("GOVERNANCE", {
                    defaultValue: "Governance-aware resource management",
                  })}
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}
