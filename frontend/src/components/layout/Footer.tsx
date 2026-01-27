import React from "react";
import { useTranslation } from "react-i18next";
import { ExternalLink, Github, Heart, Mail } from "lucide-react";
import { BRAND } from "#/config/brand";
import { I18nKey } from "#/i18n/declaration";
// Use public logo instead of bundled asset
const logo = "/forge-logo.png";

type FooterLink = {
  labelKey: I18nKey;
  href: string;
  icon?: React.ComponentType<{ className?: string }>;
  external?: boolean;
};

type FooterSection = {
  titleKey: I18nKey;
  links: FooterLink[];
};

const FOOTER_LINKS: FooterSection[] = [
  {
    titleKey: I18nKey.FOOTER$SECTION_PRODUCT,
    links: [
      {
        labelKey: I18nKey.FOOTER$LINK_DOCS,
        href: BRAND.urls.docs,
        icon: ExternalLink,
        external: true,
      },
    ],
  },
  {
    titleKey: I18nKey.FOOTER$SECTION_COMPANY,
    links: [
      {
        labelKey: I18nKey.FOOTER$LINK_SUPPORT,
        href: BRAND.urls.support,
        icon: Mail,
        external: true,
      },
    ],
  },
  {
    titleKey: I18nKey.FOOTER$SECTION_RESOURCES,
    links: [
      {
        labelKey: I18nKey.FOOTER$LINK_SUPPORT,
        href: BRAND.urls.support,
        icon: Mail,
        external: true,
      },
      {
        labelKey: I18nKey.FOOTER$LINK_LICENSE,
        href: "https://opensource.org/licenses/MIT",
        icon: ExternalLink,
        external: true,
      },
    ],
  },
];

export function Footer() {
  const { t } = useTranslation();
  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative z-10 mt-12 sm:mt-16 safe-area-bottom safe-area-left safe-area-right">
      <div className="w-full px-4 sm:px-6 lg:px-8 pb-6">
        <div className="relative overflow-hidden rounded-[32px] border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 shadow-[0_40px_120px_rgba(0,0,0,0.45)] backdrop-blur-xl mx-auto max-w-7xl">
          {/* Gradient overlays */}
          <div aria-hidden className="pointer-events-none absolute inset-0">
            <div className="absolute inset-y-0 left-1/2 w-1/2 rounded-r-[32px] bg-gradient-to-r from-brand-500/10 via-accent-500/5 to-transparent blur-3xl" />
            <div className="absolute -bottom-20 left-10 h-48 w-48 rounded-full bg-brand-500/20 blur-[110px]" />
            <div className="absolute -top-20 right-10 h-52 w-52 rounded-full bg-accent-emerald/20 blur-[120px]" />
          </div>

          <div className="relative space-y-12 px-8 py-16">
            {/* Main Footer Content */}
            <div className="grid gap-10 md:grid-cols-[2fr,3fr]">
              <div className="space-y-5">
                <div className="flex items-center gap-3">
                  <img
                    src={logo}
                    alt="Forge"
                    className="h-12 w-12 drop-shadow-[0_0_8px_rgba(139,92,246,0.3)]"
                  />
                  <div>
                    <p className="text-lg font-semibold text-white">
                      {BRAND.name}
                    </p>
                    <p className="text-xs text-white/60">{BRAND.tagline}</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-white/70">
                  {BRAND.description}
                </p>
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[11px] uppercase tracking-[0.4em] text-white/60">
                  {t(I18nKey.FOOTER$BUILT_WITH)}{" "}
                  <Heart className="h-3.5 w-3.5 text-accent-500" />{" "}
                  {BRAND.attribution.framework}
                </div>
                <a
                  href={BRAND.urls.github}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/80 transition hover:border-white/20 hover:bg-white/10 hover:text-white"
                >
                  <Github className="h-4 w-4" />
                  {t(I18nKey.FOOTER$STAR_REPO)}
                </a>
              </div>

              <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                {FOOTER_LINKS.map(({ titleKey, links }) => (
                  <div key={titleKey}>
                    <p className="text-xs uppercase tracking-[0.35em] text-white/60">
                      {t(titleKey)}
                    </p>
                    <ul className="mt-4 space-y-3">
                      {links.map(({ labelKey, href, icon: Icon, external }) => (
                        <li key={labelKey}>
                          <a
                            href={href}
                            target={external ? "_blank" : undefined}
                            rel={external ? "noreferrer" : undefined}
                            className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-white/70 transition hover:bg-white/5 hover:text-white"
                          >
                            {Icon && <Icon className="h-4 w-4 text-white/50" />}
                            {t(labelKey)}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom Bar */}
            <div className="flex flex-col items-center justify-between gap-4 rounded-2xl border border-white/10 bg-black/50 px-6 py-4 text-xs text-white/60 sm:flex-row">
              <span>
                {t(I18nKey.FOOTER$COPYRIGHT, {
                  year: currentYear,
                  brand: BRAND.name,
                })}
              </span>
              <div className="flex items-center gap-4">
                <a
                  href={BRAND.urls.support}
                  className="rounded-lg px-3 py-1.5 transition hover:bg-white/5 hover:text-white"
                >
                  {t(I18nKey.FOOTER$LINK_SUPPORT)}
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
