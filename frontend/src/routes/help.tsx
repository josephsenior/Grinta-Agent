import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  Keyboard,
  Mail,
  Github,
  ExternalLink,
  HelpCircle,
  MessageCircle,
  FileText,
  ArrowLeft,
} from "lucide-react";
import AnimatedBackground from "#/components/landing/AnimatedBackground";
import { PageHero } from "#/components/layout/PageHero";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { KeyboardShortcutsPanel } from "#/components/features/chat/keyboard-shortcuts-panel";
import { BRAND } from "#/config/brand";
import { AppLayout } from "#/components/layout/AppLayout";

export default function HelpPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showShortcuts, setShowShortcuts] = useState(false);

  const helpSections = [
    {
      title: "Getting Started",
      description: "Learn the basics of using Forge",
      icon: BookOpen,
      links: [
        {
          label: "Documentation",
          href: BRAND.urls.docs,
          external: true,
          icon: ExternalLink,
        },
        {
          label: "Quick Start Guide",
          href: `${BRAND.urls.docs}/getting-started`,
          external: true,
          icon: BookOpen,
        },
        {
          label: "Keyboard Shortcuts",
          onClick: () => setShowShortcuts(true),
          icon: Keyboard,
        },
      ],
    },
    {
      title: "Support",
      description: "Get help when you need it",
      icon: MessageCircle,
      links: [
        {
          label: "Contact Support",
          href: BRAND.urls.support,
          external: true,
          icon: Mail,
        },
        {
          label: "GitHub Issues",
          href: `${BRAND.urls.github}/issues`,
          external: true,
          icon: Github,
        },
        {
          label: "Community Forum",
          href: `${BRAND.urls.docs}/community`,
          external: true,
          icon: MessageCircle,
        },
      ],
    },
    {
      title: "Resources",
      description: "Additional resources and information",
      icon: FileText,
      links: [
        {
          label: "API Documentation",
          href: `${BRAND.urls.docs}/api`,
          external: true,
          icon: ExternalLink,
        },
        {
          label: "Terms of Service",
          href: "/terms",
          icon: FileText,
        },
        {
          label: "Privacy Policy",
          href: "/privacy",
          icon: FileText,
        },
      ],
    },
  ];

  return (
    <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
      <div aria-hidden className="pointer-events-none">
        <AnimatedBackground />
      </div>
      <AppLayout>
        <div className="rounded-3xl border border-white/10 bg-black/60 backdrop-blur-xl p-6 sm:p-8 lg:p-10">
          <PageHero
            eyebrow={t("COMMON$HELP", { defaultValue: "Help & Support" })}
            title={t("COMMON$NEED_HELP", {
              defaultValue: "How can we help you?",
            })}
            description={t("COMMON$HELP_DESCRIPTION", {
              defaultValue:
                "Find answers, documentation, and support resources.",
            })}
            align="left"
            actions={
              <Button
                variant="outline"
                onClick={() => navigate("/")}
                className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            }
          />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {helpSections.map((section) => {
              const Icon = section.icon;
              return (
                <Card key={section.title} className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                      <Icon className="h-5 w-5 text-foreground" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">
                        {section.title}
                      </h3>
                      <p className="text-sm text-white/60">
                        {section.description}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {section.links.map((link) => {
                      const LinkIcon = link.icon;
                      if ("onClick" in link && link.onClick) {
                        return (
                          <button
                            key={link.label}
                            onClick={link.onClick}
                            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl border border-white/10 bg-black/60 hover:bg-white/5 transition-colors text-left"
                          >
                            <LinkIcon className="h-4 w-4 text-white/60" />
                            <span className="text-sm text-white/80">
                              {link.label}
                            </span>
                          </button>
                        );
                      }
                      if ("href" in link) {
                        return (
                          <a
                            key={link.label}
                            href={link.href}
                            target={link.external ? "_blank" : undefined}
                            rel={link.external ? "noreferrer" : undefined}
                            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl border border-white/10 bg-black/60 hover:bg-white/5 transition-colors"
                          >
                            <LinkIcon className="h-4 w-4 text-white/60" />
                            <span className="text-sm text-white/80">
                              {link.label}
                            </span>
                            {link.external && (
                              <ExternalLink className="h-3 w-3 text-white/40 ml-auto" />
                            )}
                          </a>
                        );
                      }
                      return null;
                    })}
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Quick Actions */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <HelpCircle className="h-5 w-5 text-foreground" />
              <h3 className="text-lg font-semibold text-white">
                Quick Actions
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Button
                onClick={() => setShowShortcuts(true)}
                variant="outline"
                className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
              >
                <Keyboard className="mr-2 h-4 w-4" />
                View Keyboard Shortcuts
              </Button>
              <Button
                onClick={() => navigate("/settings")}
                variant="outline"
                className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
              >
                <FileText className="mr-2 h-4 w-4" />
                Go to Settings
              </Button>
            </div>
          </Card>
        </div>
      </AppLayout>
      <KeyboardShortcutsPanel
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
    </main>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
