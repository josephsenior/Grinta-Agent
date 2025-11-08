import React from "react";
import { useTranslation } from "react-i18next";

export default function Contact(): React.ReactElement {
  const { t } = useTranslation();
  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <div className="card-modern space-y-8">
        <div className="text-center">
          <h1 data-testid="page-title" className="text-4xl font-bold text-foreground mb-4">
            {t("CONTACT")}
          </h1>
          <div className="w-24 h-1 bg-gradient-to-r from-brand-500 to-accent-500 mx-auto rounded-full mb-6"></div>
          <p className="text-foreground-secondary leading-relaxed text-lg">
            {t("CONTACT$HELP_TEXT", {
              defaultValue:
                "We'd love to hear from you. This lightweight page will be replaced with a dynamic form.",
            })}
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card-modern text-center p-6">
            <div className="w-12 h-12 bg-brand-500/10 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-foreground mb-2">
              {t("GENERAL_INQUIRIES", { defaultValue: "General Inquiries" })}
            </h3>
            <p className="text-foreground-secondary mb-4">
              {t("EMAIL", { defaultValue: "Email:" })}
            </p>
            <a
              href="mailto:hello@Forge.pro"
              className="text-brand-500 hover:text-brand-400 transition-colors duration-200 font-medium"
            >
              hello@Forge.pro
            </a>
          </div>
          
          <div className="card-modern text-center p-6">
            <div className="w-12 h-12 bg-success-500/10 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192L5.636 18.364M12 2.25a9.75 9.75 0 100 19.5 9.75 9.75 0 000-19.5z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-foreground mb-2">
              {t("SUPPORT", { defaultValue: "Support" })}
            </h3>
            <p className="text-foreground-secondary mb-4">
              {t("EMAIL", { defaultValue: "Email:" })}
            </p>
            <a
              href="mailto:support@Forge.pro"
              className="text-brand-500 hover:text-brand-400 transition-colors duration-200 font-medium"
            >
              support@Forge.pro
            </a>
          </div>
          
          <div className="card-modern text-center p-6">
            <div className="w-12 h-12 bg-warning-500/10 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-foreground mb-2">
              {t("SECURITY", { defaultValue: "Security" })}
            </h3>
            <p className="text-foreground-secondary mb-4">
              {t("EMAIL", { defaultValue: "Email:" })}
            </p>
            <a
              href="mailto:security@Forge.pro"
              className="text-brand-500 hover:text-brand-400 transition-colors duration-200 font-medium"
            >
              security@Forge.pro
            </a>
          </div>
        </div>
        
        <div className="text-center mt-8">
          <p className="text-foreground-secondary text-sm">
            {t("CONTACT$RESPONSE_TIMES", {
              defaultValue:
                "Response times vary by request type; critical security issues are prioritized.",
            })}
          </p>
        </div>
      </div>
    </main>
  );
}
