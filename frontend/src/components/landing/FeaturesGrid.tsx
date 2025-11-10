import React, { useState, useRef } from "react";
import {
  Zap,
  Shield,
  Rocket,
  Code,
  Palette,
  Globe,
  ArrowRight,
  CheckCircle,
  Star,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { Progress } from "#/components/ui/progress";
import { useScrollReveal } from "#/hooks/use-scroll-reveal";

export default function FeaturesGrid(): React.ReactElement {
  const { t } = useTranslation();
  const [hoveredFeature, setHoveredFeature] = useState<number | null>(null);
  const [mousePosition, setMousePosition] = useState({ x: 50, y: 50 });
  const containerRef = useRef<HTMLDivElement>(null);

  const { ref: sectionRef, isVisible } = useScrollReveal({
    threshold: 0.1,
    triggerOnce: true,
  });

  const getColorClasses = (color: string) => {
    switch (color) {
      case "brand":
        return {
          bg: "bg-brand-500/10",
          ring: "ring-brand-500/20",
          text: "text-violet-500",
          shadow: "shadow-brand-500/20",
          button:
            "text-violet-500 hover:bg-violet-500/10 group-hover:bg-brand-500/15",
        };
      case "success":
        return {
          bg: "bg-success-500/10",
          ring: "ring-success-500/20",
          text: "text-success-500",
          shadow: "shadow-success-500/20",
          button:
            "text-success-500 hover:bg-success-500/10 group-hover:bg-success-500/15",
        };
      case "accent":
        return {
          bg: "bg-accent-500/10",
          ring: "ring-accent-500/20",
          text: "text-accent-500",
          shadow: "shadow-accent-500/20",
          button:
            "text-accent-500 hover:bg-accent-500/10 group-hover:bg-accent-500/15",
        };
      case "warning":
        return {
          bg: "bg-warning-500/10",
          ring: "ring-warning-500/20",
          text: "text-warning-500",
          shadow: "shadow-warning-500/20",
          button:
            "text-warning-500 hover:bg-warning-500/10 group-hover:bg-warning-500/15",
        };
      default:
        return {
          bg: "bg-brand-500/10",
          ring: "ring-brand-500/20",
          text: "text-violet-500",
          shadow: "shadow-brand-500/20",
          button:
            "text-violet-500 hover:bg-violet-500/10 group-hover:bg-brand-500/15",
        };
    }
  };

  const features = [
    {
      icon: Zap,
      title: t("LANDING$FEATURE_1_TITLE", {
        defaultValue: "Instant Code Generation",
      }),
      description: t("LANDING$FEATURE_1_DESC", {
        defaultValue:
          "Forge Pro writes production-ready code in seconds, from simple functions to complex applications.",
      }),
      stats: "10x faster",
      color: "brand",
      badge: "Popular",
      progress: 95,
      size: "large", // For bento layout
    },
    {
      icon: Shield,
      title: t("LANDING$FEATURE_2_TITLE", { defaultValue: "Built-in Testing" }),
      description: t("LANDING$FEATURE_2_DESC", {
        defaultValue:
          "Every piece of code comes with comprehensive tests and security best practices built-in.",
      }),
      stats: "100% coverage",
      color: "success",
      badge: "Secure",
      progress: 100,
      size: "medium",
    },
    {
      icon: Rocket,
      title: t("LANDING$FEATURE_3_TITLE", { defaultValue: "Auto Deployment" }),
      description: t("LANDING$FEATURE_3_DESC", {
        defaultValue:
          "Forge Pro handles the entire deployment pipeline, from build optimization to production release.",
      }),
      stats: "Zero downtime",
      color: "accent",
      badge: "Automated",
      progress: 88,
      size: "medium",
    },
    {
      icon: Code,
      title: t("LANDING$FEATURE_4_TITLE", {
        defaultValue: "Multi-Language Expert",
      }),
      description: t("LANDING$FEATURE_4_DESC", {
        defaultValue:
          "Fluent in all major programming languages and frameworks, adapting to your tech stack.",
      }),
      stats: "50+ languages",
      color: "warning",
      badge: "Expert",
      progress: 92,
      size: "small",
    },
    {
      icon: Palette,
      title: t("LANDING$FEATURE_5_TITLE", { defaultValue: "UI/UX Excellence" }),
      description: t("LANDING$FEATURE_5_DESC", {
        defaultValue:
          "Creates beautiful, responsive interfaces with modern design principles and accessibility.",
      }),
      stats: "Pixel perfect",
      color: "brand",
      badge: "Design",
      progress: 97,
      size: "small",
    },
    {
      icon: Globe,
      title: t("LANDING$FEATURE_6_TITLE", {
        defaultValue: "Continuous Learning",
      }),
      description: t("LANDING$FEATURE_6_DESC", {
        defaultValue:
          "Forge Pro constantly evolves, learning from the latest development trends and best practices.",
      }),
      stats: "Always updated",
      color: "accent",
      badge: "AI-Powered",
      progress: 85,
      size: "large",
    },
  ];

  // Track mouse for spotlight effect
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    setMousePosition({ x, y });
  };

  return (
    <section ref={sectionRef} className="py-20 px-6 relative">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div
          className={`text-center mb-16 max-w-3xl mx-auto ${isVisible ? "stagger-item delay-0" : "opacity-0"}`}
        >
          <div className="inline-flex items-center gap-3 mb-8">
            <Badge
              variant="secondary"
              className="glass-modern border-brand-500/30 text-violet-500 px-5 py-2.5 text-sm font-medium shadow-lg interactive-scale"
            >
              <Star className="w-4 h-4 mr-2 floating-icon" />
              Features
            </Badge>
            <Badge
              variant="outline"
              className="border-success-500/40 text-success-500 bg-success-500/10 backdrop-blur-sm px-5 py-2.5 shadow-lg interactive-scale"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              All Included
            </Badge>
          </div>

          <h2 className="text-4xl md:text-6xl font-bold mb-6 leading-tight tracking-tight">
            <span className="text-foreground block mb-2">
              Powerful Features
            </span>
            <span className="bg-gradient-to-r from-brand-500 via-accent-500 to-brand-600 bg-clip-text text-transparent gradient-shimmer block">
              Built for Developers
            </span>
          </h2>

          <p className="text-lg md:text-xl text-foreground-secondary max-w-3xl mx-auto mb-8 leading-relaxed">
            Everything you need to build, test, and deploy world-class software
          </p>

          <Button
            variant="outline"
            className="border-brand-500/40 text-violet-500 hover:bg-violet-500/10 px-8 py-3 text-base font-semibold backdrop-blur-sm hover:shadow-lg hover:border-brand-500/60 transition-all duration-300 interactive-scale button-shine overflow-hidden"
          >
            View All Features
            <ArrowRight className="w-5 h-5 ml-3" />
          </Button>
        </div>

        {/* Bento Box Grid Layout (asymmetric like bolt.new) */}
        <div
          ref={containerRef}
          onMouseMove={handleMouseMove}
          className="grid grid-cols-1 md:grid-cols-12 gap-6 auto-rows-fr"
          style={
            {
              "--mouse-x": `${mousePosition.x}%`,
              "--mouse-y": `${mousePosition.y}%`,
            } as React.CSSProperties
          }
        >
          {features.map((feature, index) => {
            const colors = getColorClasses(feature.color);

            // Bento box layout classes (asymmetric)
            const sizeClasses = {
              large: "md:col-span-8 md:row-span-1",
              medium: "md:col-span-6 md:row-span-1",
              small: "md:col-span-6 md:row-span-1",
            }[feature.size];

            return (
              <Card
                key={feature.title}
                className={`
                  ${sizeClasses}
                  glass-modern gradient-border-animated spotlight-effect 
                  card-hover-lift group relative overflow-hidden 
                  gpu-accelerated
                  ${isVisible ? `bento-card delay-${index * 100}` : "opacity-0"}
                `}
                onMouseEnter={() => setHoveredFeature(index)}
                onMouseLeave={() => setHoveredFeature(null)}
              >
                {/* Spotlight follows mouse */}
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                  style={{
                    background: `radial-gradient(600px circle at ${mousePosition.x}% ${mousePosition.y}%, rgba(139, 92, 246, 0.1), transparent 40%)`,
                  }}
                />

                <CardHeader className="space-y-4 relative z-10">
                  <div className="flex items-start justify-between">
                    <div
                      className={`w-14 h-14 rounded-xl ${colors.bg} flex items-center justify-center ring-1 ${colors.ring} group-hover:scale-110 transition-all duration-300 morphing-icon`}
                    >
                      <feature.icon
                        className={`w-7 h-7 ${colors.text} floating-icon`}
                        style={{ animationDelay: `${index * 0.2}s` }}
                      />
                    </div>
                    <Badge
                      variant="secondary"
                      className={`text-xs ${colors.bg} ${colors.text} border ${colors.ring} interactive-scale`}
                    >
                      {feature.badge}
                    </Badge>
                  </div>

                  <div>
                    <CardTitle className="text-xl mb-3 text-foreground font-bold group-hover:text-violet-500 transition-colors duration-300">
                      {feature.title}
                    </CardTitle>
                    <CardDescription className="text-sm leading-relaxed text-foreground-secondary">
                      {feature.description}
                    </CardDescription>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 relative z-10">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-foreground-secondary font-medium">
                      Performance
                    </span>
                    <span className={`font-bold ${colors.text}`}>
                      {feature.stats}
                    </span>
                  </div>

                  <div className="relative">
                    <Progress
                      value={feature.progress}
                      className="h-2.5 bg-background-tertiary"
                    />
                    {hoveredFeature === index && (
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer pointer-events-none" />
                    )}
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className={`w-full ${colors.button} font-medium transition-all duration-300 interactive-scale`}
                  >
                    Learn More
                    <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-2 transition-transform duration-300" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
