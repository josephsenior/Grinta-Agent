import React from "react";
import { TrendingUp, Users, Zap, Award } from "lucide-react";
import { Card, CardContent } from "#/components/ui/card";
import { statsHighlights } from "#/content/landing";

export default function StatsSection(): React.ReactElement {
  const iconCycle = [Users, Zap, TrendingUp, Award];
  const stats = statsHighlights.map((stat, index) => ({
    ...stat,
    icon: iconCycle[index % iconCycle.length],
  }));

  return (
    <section className="relative py-20 px-6">
      <div className="absolute inset-0 bg-gradient-to-b from-background via-background-secondary/40 to-background" />
      <div className="relative max-w-6xl mx-auto">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card
              key={String(stat.label)}
              className="stats-card group text-center transition-all duration-300 hover:shadow-xl border-white/10 bg-background-primary/70"
            >
              <CardContent className="p-6 space-y-4">
                <div className="flex justify-center">
                  <div className="w-12 h-12 rounded-lg bg-brand-500/10 flex items-center justify-center ring-1 ring-brand-500/20 group-hover:ring-brand-500/40 transition-all">
                    <stat.icon className="w-6 h-6 text-violet-400" />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-3xl font-semibold text-white">
                    {stat.value}
                  </div>
                  <h3 className="text-base font-semibold text-foreground-secondary">
                    {stat.label}
                  </h3>
                  <p className="text-sm text-foreground-tertiary">
                    {stat.description}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
