import React from "react";
import { useTranslation } from "react-i18next";
import { Mail, Shield, MessageCircle } from "lucide-react";
import { PageHero } from "#/components/layout/PageHero";

export default function Contact(): React.ReactElement {
  const { t } = useTranslation();
  const generalEmail = t("contact.emails.general", {
    defaultValue: "hello@Forge.pro",
  });
  const supportEmail = t("contact.emails.support", {
    defaultValue: "support@Forge.pro",
  });
  const securityEmail = t("contact.emails.security", {
    defaultValue: "security@Forge.pro",
  });
  const contactCards = [
    {
      title: t("GENERAL_INQUIRIES", { defaultValue: "General" }),
      description: t("CONTACT$GENERAL_DESC", {
        defaultValue: "Questions about the beta, roadmap, or partnerships.",
      }),
      email: generalEmail,
      icon: Mail,
      badge: "Product",
    },
    {
      title: t("SUPPORT", { defaultValue: "Support" }),
      description: t("CONTACT$SUPPORT_DESC", {
        defaultValue: "Workspace help, billing, or technical issues.",
      }),
      email: supportEmail,
      icon: MessageCircle,
      badge: "Response • 2h",
    },
    {
      title: t("SECURITY", { defaultValue: "Security" }),
      description: t("CONTACT$SECURITY_DESC", {
        defaultValue: "Responsible disclosure and compliance reviews.",
      }),
      email: securityEmail,
      icon: Shield,
      badge: "24/7",
    },
  ];
  return (
    <main className="relative min-h-screen bg-black pb-20">
      <PageHero
        eyebrow="Contact"
        title={t("CONTACT", { defaultValue: "Talk to the Forge team" })}
        description={t("CONTACT$HELP_TEXT", {
          defaultValue:
            "Direct access to engineers, support, and security for every beta workspace.",
        })}
        align="left"
        stats={[
          { label: "Median reply", value: "15m", helper: "During beta" },
          { label: "Coverage", value: "24/7", helper: "Security + support" },
          { label: "Channels", value: "Email", helper: "Sync or async" },
        ]}
      />

      <div className="px-6">
        <div className="max-w-5xl mx-auto grid gap-6 md:grid-cols-3">
          {contactCards.map(
            ({ title, description, email, icon: Icon, badge }) => (
              <div
                key={title}
                className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl"
              >
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-brand-500" />
                  </div>
                  <span className="text-xs uppercase tracking-[0.4em] text-foreground-tertiary">
                    {badge}
                  </span>
                </div>
                <h3 className="mt-6 text-xl font-semibold text-white">
                  {title}
                </h3>
                <p className="mt-2 text-sm text-foreground-secondary">
                  {description}
                </p>
                <a
                  href={`mailto:${email}`}
                  className="mt-6 inline-flex items-center gap-2 text-sm text-white/90 hover:text-white"
                >
                  {email}
                  <Mail className="w-4 h-4" />
                </a>
              </div>
            ),
          )}
        </div>
        <p className="text-center text-sm text-foreground-tertiary mt-10">
          {t("CONTACT$RESPONSE_TIMES", {
            defaultValue:
              "Critical security disclosures are prioritized immediately.",
          })}
        </p>
      </div>
    </main>
  );
}
