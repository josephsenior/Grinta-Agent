import React from "react";
import { TrendingUp, Users, Zap, Award } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "#/components/ui/card";

export default function StatsSection(): React.ReactElement {
  const { t } = useTranslation();

  const stats = [
    {
      icon: Users,
      value: t("LANDING$STATS_PROJECTS_VALUE", { defaultValue: "10K+" }),
      label: t("LANDING$STATS_PROJECTS_LABEL", {
        defaultValue: "Projects Completed",
      }),
      description: t("LANDING$STATS_PROJECTS_DESC", {
        defaultValue: "Successfully delivered by Forge Pro",
      }),
    },
    {
      icon: Zap,
      value: t("LANDING$STATS_LOC_VALUE", { defaultValue: "500K+" }),
      label: t("LANDING$STATS_LOC_LABEL", { defaultValue: "Lines of Code" }),
      description: t("LANDING$STATS_LOC_DESC", {
        defaultValue: "Written and optimized by Forge Pro",
      }),
    },
    {
      icon: TrendingUp,
      value: t("LANDING$STATS_AVAILABLE_VALUE", { defaultValue: "24/7" }),
      label: t("LANDING$STATS_AVAILABLE_LABEL", {
        defaultValue: "Always Available",
      }),
      description: t("LANDING$STATS_AVAILABLE_DESC", {
        defaultValue: "Forge Pro never sleeps or takes breaks",
      }),
    },
    {
      icon: Award,
      value: t("LANDING$STATS_QUALITY_VALUE", { defaultValue: "100%" }),
      label: t("LANDING$STATS_QUALITY_LABEL", { defaultValue: "Code Quality" }),
      description: t("LANDING$STATS_QUALITY_DESC", {
        defaultValue: "Production-ready every time",
      }),
    },
  ];

  return (
    <section className="py-16 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <div className="stats-grid">
          {stats.map((stat) => (
            <Card
              key={String(stat.label)}
              className="stats-card group text-center transition-all duration-300 hover:shadow-lg"
            >
              <CardContent className="p-6 space-y-4">
                <div className="flex justify-center">
                  <div className="w-12 h-12 rounded-lg bg-brand-500/10 flex items-center justify-center ring-1 ring-brand-500/20 group-hover:ring-brand-500/40 transition-all">
                    <stat.icon className="w-6 h-6 text-violet-500" />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-3xl font-bold text-gradient-brand">
                    {stat.value}
                  </div>
                  <h3 className="text-base font-bold">{stat.label}</h3>
                  <p className="text-sm">{stat.description}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
