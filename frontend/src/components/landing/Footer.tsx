import React from "react";
import { Sparkles, Github, Twitter, Linkedin } from "lucide-react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

export default function Footer(): React.ReactElement {
  const { t } = useTranslation();

  return (
    <footer className="relative py-16 px-6 border-t border-border/50">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center space-x-3 mb-6">
              <div className="relative">
                <Sparkles className="w-8 h-8 text-violet-500" />
                <div className="absolute inset-0 bg-brand-500/20 rounded-full blur-md" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-brand-500 to-accent-500 bg-clip-text text-transparent">
                {t(I18nKey.APP$TITLE, { defaultValue: "Forge Pro" })}
              </span>
            </div>
            <p className="text-foreground-secondary leading-relaxed">
              {t("LANDING$OPEN_REPO", {
                defaultValue:
                  "Building the future of development with AI-powered tools and elegant design.",
              })}
            </p>
          </div>

          {/* Links */}
          <div>
            <h3 className="font-semibold text-white mb-6">
              {t("FOOTER$PRODUCT", { defaultValue: t("PRODUCT") })}
            </h3>
            <ul className="space-y-3">
              <li>
                <a
                  href="/about"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("ABOUT", {
                    defaultValue: t(I18nKey.LANDING$START_HELP, {
                      defaultValue: "About",
                    }),
                  })}
                </a>
              </li>
              <li>
                <a
                  href="/contact"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("CONTACT", { defaultValue: "Contact" })}
                </a>
              </li>
              <li>
                <a
                  href="/terms"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("TOS$TERMS", { defaultValue: "Terms" })}
                </a>
              </li>
              <li>
                <a
                  href="/privacy"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("COMMON$PRIVACY_POLICY", { defaultValue: "Privacy" })}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-white mb-6">
              {t("FOOTER$COMPANY", { defaultValue: t("COMPANY") })}
            </h3>
            <ul className="space-y-3">
              <li>
                <a
                  href="/about"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("ABOUT", { defaultValue: "About" })}
                </a>
              </li>
              <li>
                <a
                  href="/contact"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("SUPPORT", { defaultValue: "Support" })}
                </a>
              </li>
              <li>
                <a
                  href="/privacy"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("COMMON$PRIVACY_POLICY", { defaultValue: "Privacy" })}
                </a>
              </li>
              <li>
                <a
                  href="/terms"
                  className="text-foreground-secondary hover:text-violet-500 transition-colors duration-300"
                >
                  {t("TOS$TERMS", { defaultValue: "Terms" })}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-white mb-6">
              {t("FOOTER$CONNECT", { defaultValue: t("CONNECT") })}
            </h3>
            <div className="flex space-x-4">
              <button
                type="button"
                aria-label={t("COMMON$OPEN_GITHUB", {
                  defaultValue: "Open GitHub",
                })}
                className="p-3 rounded-lg bg-background-tertiary/50 hover:bg-violet-500/10 transition-all duration-300 group shadow-lg hover:shadow-brand-500/20"
              >
                <Github className="w-5 h-5 text-foreground-secondary group-hover:text-violet-500 transition-colors duration-300" />
              </button>
              <button
                type="button"
                aria-label={t("COMMON$OPEN_TWITTER", {
                  defaultValue: "Open Twitter",
                })}
                className="p-3 rounded-lg bg-background-tertiary/50 hover:bg-accent-emerald/10 transition-all duration-300 group shadow-lg hover:shadow-accent-emerald/20"
              >
                <Twitter className="w-5 h-5 text-foreground-secondary group-hover:text-accent-emerald transition-colors duration-300" />
              </button>
              <button
                type="button"
                aria-label={t("COMMON$OPEN_LINKEDIN", {
                  defaultValue: "Open LinkedIn",
                })}
                className="p-3 rounded-lg bg-background-tertiary/50 hover:bg-accent-sapphire/10 transition-all duration-300 group shadow-lg hover:shadow-accent-sapphire/20"
              >
                <Linkedin className="w-5 h-5 text-foreground-secondary group-hover:text-accent-sapphire transition-colors duration-300" />
              </button>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between mt-12 pt-8 border-t border-border/50">
          <div className="text-foreground-secondary mb-4 md:mb-0">
            {t("COPYRIGHT", {
              defaultValue: t(I18nKey.COMMON$FOR_EXAMPLE, {
                defaultValue: "© 2025 Forge Pro. All rights reserved.",
              }),
            })}
          </div>
          <div className="flex items-center space-x-6 text-sm">
            <a
              href="/privacy"
              className="text-foreground-secondary hover:text-brand-400 transition-colors duration-300"
            >
              {t("COMMON$PRIVACY_POLICY")}
            </a>
            <a
              href="/terms"
              className="text-foreground-secondary hover:text-brand-400 transition-colors duration-300"
            >
              {t("TOS$TERMS")}
            </a>
            <a
              href="/contact"
              className="text-foreground-secondary hover:text-brand-400 transition-colors duration-300"
            >
              {t("CONTACT")}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
