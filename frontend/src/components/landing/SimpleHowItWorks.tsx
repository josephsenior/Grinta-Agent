import React from "react";
import { MessageSquare, Code, Rocket, ArrowRight } from "lucide-react";
import { useScrollReveal } from "#/hooks/use-scroll-reveal";
import { soundEffects } from "#/utils/sound-effects";
import { howItWorksSteps } from "#/content/landing";

export function SimpleHowItWorks() {
  const { ref, isVisible } = useScrollReveal({
    threshold: 0.2,
    triggerOnce: true,
  });

  const iconCycle = [MessageSquare, Code, Rocket];
  const gradientCycle = [
    "from-brand-500 to-accent-500",
    "from-accent-500 to-brand-600",
    "from-accent-emerald to-success-500",
  ];
  const steps = howItWorksSteps.map((step, index) => ({
    ...step,
    icon: iconCycle[index % iconCycle.length],
    bgGradient: gradientCycle[index % gradientCycle.length],
    title: `${index + 1}. ${step.title}`,
  }));

  return (
    <section ref={ref} className="py-20 px-6 relative">
      <div className="max-w-6xl mx-auto">
        <div
          className={`text-center mb-16 max-w-3xl min-w-[400px] mx-auto ${isVisible ? "stagger-item delay-0" : "opacity-0"}`}
        >
          <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-4 whitespace-normal">
            From Idea to Production{" "}
            <span className="bg-gradient-to-r from-brand-500 to-accent-500 bg-clip-text text-transparent gradient-shimmer whitespace-normal">
              in Minutes
            </span>
          </h2>
          <p className="text-lg text-foreground-secondary max-w-2xl min-w-[400px] mx-auto whitespace-normal">
            Three simple steps to ship production-ready code faster than ever
            before
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Connection lines with gradient */}
          <div className="hidden md:block absolute top-24 left-0 right-0 h-1 bg-gradient-to-r from-brand-500/30 via-accent-500/30 to-accent-emerald/30 opacity-50 blur-sm" />
          <div className="hidden md:block absolute top-24 left-0 right-0 h-0.5 bg-gradient-to-r from-brand-500 via-accent-500 to-accent-emerald opacity-60" />

          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div
                key={index}
                className={`relative ${isVisible ? `bento-card delay-${(index + 1) * 100}` : "opacity-0"}`}
              >
                <div className="flex flex-col items-center text-center">
                  {/* Icon with enhanced styling */}
                  <div
                    className={`relative z-10 w-24 h-24 rounded-2xl bg-gradient-to-br ${step.bgGradient} flex items-center justify-center mb-6 shadow-xl morphing-icon group cursor-pointer hover:scale-110 transition-all duration-500 gpu-accelerated`}
                    style={{ animationDelay: `${index * 0.5}s` }}
                  >
                    <Icon
                      className="w-12 h-12 text-white floating-icon"
                      style={{ animationDelay: `${index * 0.3}s` }}
                    />

                    {/* Glow effect */}
                    <div
                      className={`absolute inset-0 bg-gradient-to-br ${step.bgGradient} rounded-2xl blur-xl opacity-50 -z-10 group-hover:blur-2xl group-hover:opacity-75 transition-all duration-500`}
                    />
                  </div>

                  {/* Content */}
                  <h3 className="text-xl font-semibold text-foreground mb-3 hover:text-violet-500 transition-colors duration-300 whitespace-normal">
                    {step.title}
                  </h3>
                  <p className="text-foreground-secondary leading-relaxed whitespace-normal">
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div
          className={`text-center mt-16 ${isVisible ? "stagger-item delay-400" : "opacity-0"}`}
        >
          <a
            href="/conversations/new"
            onMouseEnter={() => soundEffects.hover()}
            onClick={() => soundEffects.success()}
            className="inline-flex items-center px-10 py-5 bg-gradient-to-r from-brand-500 to-brand-600 text-white font-semibold rounded-xl shadow-lg shadow-brand-500/30 hover:shadow-2xl hover:shadow-brand-500/40 transition-all duration-300 button-shine interactive-scale overflow-hidden gpu-accelerated group"
          >
            Start Your First Project
            <ArrowRight className="w-5 h-5 ml-3 group-hover:translate-x-2 transition-transform duration-300" />
          </a>
        </div>
      </div>
    </section>
  );
}

export default SimpleHowItWorks;
