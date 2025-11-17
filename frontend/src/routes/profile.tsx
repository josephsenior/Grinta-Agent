import React from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  User,
  Settings,
  CreditCard,
  Key,
  Shield,
  Crown,
  Edit,
  ArrowLeft,
} from "lucide-react";
import AnimatedBackground from "#/components/landing/AnimatedBackground";
import { PageHero } from "#/components/layout/PageHero";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { useBalance } from "#/hooks/query/use-balance";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { useAuth } from "#/context/auth-context";
import { isAdmin } from "#/utils/auth/permissions";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { ChangePasswordForm } from "#/components/features/auth/change-password-form";

export default function ProfilePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: balance } = useBalance();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const { data: config } = useConfig();
  const { data: settings } = useSettings();

  const isSaas = config?.APP_MODE === "saas";
  const hasProAccess = subscriptionAccess?.status === "ACTIVE";
  // Use auth user email if available, fallback to settings
  const userEmail = user?.email ?? settings?.EMAIL;
  const username = user?.username;
  const isUserAdmin = isAdmin(user);

  const profileSections = [
    {
      title: "Account Information",
      icon: User,
      items: [
        {
          label: "Username",
          value: username || "Not set",
          action: username
            ? undefined
            : {
                label: "Edit",
                onClick: () => navigate("/settings/user"),
                icon: Edit,
              },
        },
        {
          label: "Email",
          value: userEmail || "Not set",
          action: {
            label: "Edit",
            onClick: () => navigate("/settings/user"),
            icon: Edit,
          },
        },
        {
          label: "Role",
          value: user?.role
            ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
            : "User",
          action: undefined,
        },
        {
          label: "Account Type",
          value: hasProAccess ? "Pro" : isSaas ? "Free" : "OSS",
          badge: hasProAccess ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-400/20 text-yellow-400 text-xs font-medium">
              <Crown className="h-3 w-3" />
              Pro
            </span>
          ) : null,
        },
      ],
    },
    ...(isSaas
      ? [
          {
            title: "Billing & Credits",
            icon: CreditCard,
            items: [
              {
                label: "Account Balance",
                value:
                  balance !== undefined
                    ? `$${Number(balance).toFixed(2)}`
                    : "Loading...",
                action: {
                  label: "Manage",
                  onClick: () => navigate("/settings/billing"),
                },
              },
            ],
          },
        ]
      : []),
    {
      title: "Security & Privacy",
      icon: Shield,
      items: [
        {
          label: "API Keys",
          value: "Manage your API keys",
          action: {
            label: "View",
            onClick: () => navigate("/settings/api-keys"),
          },
        },
        {
          label: "Privacy Settings",
          value: "Control your privacy preferences",
          action: {
            label: "Configure",
            onClick: () => navigate("/settings/app"),
          },
        },
      ],
    },
  ];

  return (
    <AuthGuard>
      <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
        <div aria-hidden className="pointer-events-none">
          <AnimatedBackground />
        </div>
        <AppLayout>
          <div className="rounded-3xl border border-white/10 bg-black/60 backdrop-blur-xl p-6 sm:p-8 lg:p-10">
            <PageHero
              eyebrow={t("COMMON$PROFILE", { defaultValue: "Profile" })}
              title={t("COMMON$YOUR_PROFILE", { defaultValue: "Your Profile" })}
              description={t("COMMON$PROFILE_DESCRIPTION", {
                defaultValue: "Manage your account settings and preferences.",
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

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Profile Card */}
              <Card className="lg:col-span-1 p-6">
                <div className="flex flex-col items-center text-center">
                  <div className="relative mb-4">
                    <div className="w-24 h-24 rounded-full bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
                      {userEmail ? (
                        <span className="text-3xl font-bold text-white">
                          {userEmail[0].toUpperCase()}
                        </span>
                      ) : (
                        <User className="h-12 w-12 text-white" />
                      )}
                    </div>
                    {hasProAccess && (
                      <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-yellow-400 border-4 border-black flex items-center justify-center shadow-lg">
                        <Crown className="h-4 w-4 text-black" />
                      </div>
                    )}
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-1">
                    {username || userEmail || "Account"}
                  </h3>
                  {isUserAdmin && (
                    <p className="text-sm text-brand-400 font-medium mb-2">
                      Admin
                    </p>
                  )}
                  {hasProAccess ? (
                    <p className="text-sm text-yellow-400 font-medium flex items-center gap-1 mb-2">
                      <Crown className="h-3 w-3" />
                      Pro Member
                    </p>
                  ) : isSaas ? (
                    <p className="text-sm text-white/60 mb-2">Free Tier</p>
                  ) : null}
                  {isSaas && balance !== undefined && (
                    <p className="text-sm text-white/60 mb-4">
                      Balance: ${Number(balance).toFixed(2)}
                    </p>
                  )}
                  <Button
                    onClick={() => navigate("/settings/user")}
                    variant="outline"
                    className="w-full border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Edit Profile
                  </Button>
                </div>
              </Card>

              {/* Profile Sections */}
              <div className="lg:col-span-2 space-y-6">
                {profileSections.map((section) => {
                  const Icon = section.icon;
                  return (
                    <Card key={section.title} className="p-6">
                      <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                          <Icon className="h-5 w-5 text-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold text-white">
                          {section.title}
                        </h3>
                      </div>
                      <div className="space-y-4">
                        {section.items.map((item, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between py-3 border-b border-white/10 last:border-0"
                          >
                            <div className="flex-1">
                              <p className="text-sm font-medium text-white/80 mb-1">
                                {item.label}
                              </p>
                              <div className="flex items-center gap-2">
                                <p className="text-sm text-white/60">
                                  {item.value}
                                </p>
                                {"badge" in item && item.badge}
                              </div>
                            </div>
                            {item.action && (
                              <Button
                                onClick={item.action.onClick}
                                variant="outline"
                                size="sm"
                                className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-4 py-2"
                              >
                                {"icon" in item.action && item.action.icon && (
                                  <item.action.icon className="mr-1.5 h-3.5 w-3.5" />
                                )}
                                {item.action.label}
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    </Card>
                  );
                })}

                {/* Change Password */}
                <ChangePasswordForm />

                {/* Quick Actions */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">
                    Quick Actions
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Button
                      onClick={() => navigate("/settings")}
                      variant="outline"
                      className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                    >
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </Button>
                    {isSaas && (
                      <Button
                        onClick={() => navigate("/settings/billing")}
                        variant="outline"
                        className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                      >
                        <CreditCard className="mr-2 h-4 w-4" />
                        Billing
                      </Button>
                    )}
                    <Button
                      onClick={() => navigate("/settings/api-keys")}
                      variant="outline"
                      className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                    >
                      <Key className="mr-2 h-4 w-4" />
                      API Keys
                    </Button>
                    <Button
                      onClick={() => navigate("/help")}
                      variant="outline"
                      className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                    >
                      <Shield className="mr-2 h-4 w-4" />
                      Help & Support
                    </Button>
                  </div>
                </Card>
              </div>
            </div>
          </div>
        </AppLayout>
      </main>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
