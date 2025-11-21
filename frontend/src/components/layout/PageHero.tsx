import React from "react";
import { cn } from "#/utils/utils";

interface HeroStat {
  label: string;
  value: string;
  helper?: string;
}

interface PageHeroProps {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "center" | "left";
  stats?: HeroStat[];
  actions?: React.ReactNode;
}

export function PageHero({
  eyebrow,
  title,
  description,
  align = "center",
  stats,
  actions,
}: PageHeroProps) {
  const alignment =
    align === "left" ? "text-left items-start" : "text-center items-center";

  return (
    <section className="relative overflow-hidden py-16 px-6">
      <div className="absolute inset-0">
        <div className="absolute inset-y-0 left-1/2 w-1/2 bg-gradient-to-r from-brand-500/10 via-accent-500/5 to-transparent blur-3xl" />
        <div className="absolute -top-24 right-6 h-60 w-60 rounded-full bg-brand-500/20 blur-[130px]" />
      </div>
      <div
        className={cn(
          "relative max-w-6xl mx-auto flex flex-col gap-6",
          alignment,
        )}
      >
        <div className="space-y-4 max-w-3xl min-w-[400px]">
          {eyebrow && (
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-brand-500/40 bg-white/10 text-xs font-semibold uppercase tracking-[0.25em] text-white/90 whitespace-normal">
              {eyebrow}
            </span>
          )}
          <h1 className="text-3xl md:text-5xl font-semibold text-white leading-tight whitespace-normal">
            {title}
          </h1>
          {description && (
            <p className="text-lg text-white/75 leading-relaxed whitespace-normal">
              {description}
            </p>
          )}
        </div>

        {actions && <div className="flex flex-wrap gap-3">{actions}</div>}

        {stats && stats.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-transparent to-transparent p-4 text-center backdrop-blur-sm"
              >
                <div className="text-2xl font-semibold text-white">
                  {stat.value}
                </div>
                <div className="text-xs uppercase tracking-[0.3em] text-white/60 mt-1">
                  {stat.label}
                </div>
                {stat.helper && (
                  <p className="text-[11px] text-white/50 mt-2">
                    {stat.helper}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
