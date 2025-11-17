import React from "react";
import { Bot, Zap, Shield } from "lucide-react";
import { useScrollReveal } from "#/hooks/use-scroll-reveal";
import { simpleFeatureCards } from "#/content/landing";

export function SimpleFeatures() {
  const { ref, isVisible } = useScrollReveal({
    threshold: 0.2,
    triggerOnce: true,
  });

  const iconCycle = [Bot, Zap, Shield];
  const features = simpleFeatureCards.map((feature, index) => ({
    ...feature,
    icon: iconCycle[index % iconCycle.length],
  }));

  return (
    <section ref={ref} className="py-20 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <div
          className={`text-center mb-16 ${isVisible ? "stagger-item delay-0" : "opacity-0"}`}
        >
          <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-4">
            Everything You Need to{" "}
            <span className="bg-gradient-to-r from-brand-500 to-accent-500 bg-clip-text text-transparent gradient-shimmer">
              Dominate Development
            </span>
          </h2>
          <p className="text-lg text-foreground-secondary max-w-2xl mx-auto">
            Enterprise-grade features that eliminate 80% of repetitive coding
            and let you focus on what matters
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <div
                key={index}
                className={`
                  group glass-modern gradient-border-animated spotlight-effect
                  p-8 rounded-2xl card-hover-lift gpu-accelerated
                  ${isVisible ? `bento-card delay-${index * 100}` : "opacity-0"}
                `}
              >
                <div
                  className={`w-16 h-16 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6 morphing-icon shadow-lg shadow-brand-500/30 group-hover:scale-110 group-hover:rotate-6 transition-all duration-500`}
                  style={{ animationDelay: `${index * 0.5}s` }}
                >
                  <Icon
                    className="w-8 h-8 text-white floating-icon"
                    style={{ animationDelay: `${index * 0.3}s` }}
                  />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3 group-hover:text-violet-500 transition-colors duration-300">
                  {feature.title}
                </h3>
                <p className="text-foreground-secondary leading-relaxed">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default SimpleFeatures;
