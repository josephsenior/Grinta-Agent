import { ArrowRight, Sparkles, Code2 } from "lucide-react";
import { Link } from "react-router-dom";
import { RefObject } from "react";
import { heroContent } from "#/content/landing";

interface HeroContentProps {
  contentRef: RefObject<HTMLDivElement | null>;
  titleRef: RefObject<HTMLHeadingElement | null>;
  subtitleRef: RefObject<HTMLParagraphElement | null>;
  ctaRef: RefObject<HTMLDivElement | null>;
}

export function HeroContent({
  contentRef,
  titleRef,
  subtitleRef,
  ctaRef,
}: HeroContentProps) {
  return (
    <div
      ref={contentRef}
      className="text-center lg:text-left space-y-8 min-w-0"
    >
      <div className="badge inline-flex items-center gap-2 px-4 py-2 bg-brand-violet/10 border border-brand-violet/20 rounded-full text-sm text-brand-violetLight">
        <Sparkles size={16} className="animate-pulse" />
        <span>{heroContent.badge}</span>
      </div>

      <h1
        ref={titleRef}
        className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight w-full"
      >
        {heroContent.heading}
      </h1>

      <p
        ref={subtitleRef}
        className="text-lg sm:text-xl text-text-secondary w-full"
      >
        {heroContent.subheading}
      </p>

      <div
        ref={ctaRef}
        className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start"
      >
        <Link
          to="/auth/register"
          className="group px-8 py-4 bg-brand-violet hover:bg-brand-violet-dark text-white font-semibold rounded-xl transition-all duration-300 shadow-glow hover:shadow-glow-lg flex items-center justify-center gap-2 whitespace-nowrap"
        >
          <span>
            {heroContent.trustSignals[1]?.replace(
              "$1/day free tier",
              "Start Free",
            ) || "Start Building Free"}
          </span>
          <ArrowRight
            size={20}
            className="group-hover:translate-x-1 transition-transform flex-shrink-0"
          />
        </Link>
        <Link
          to="/dashboard"
          className="px-8 py-4 glass-effect font-semibold rounded-xl transition-all duration-300 flex items-center justify-center gap-2 whitespace-nowrap"
          style={{ color: "var(--text-primary)" }}
          onMouseEnter={(e) => {
            const target = e.currentTarget;
            target.style.backgroundColor = "var(--bg-elevated)";
          }}
          onMouseLeave={(e) => {
            const target = e.currentTarget;
            target.style.backgroundColor = "var(--glass-bg)";
          }}
        >
          <Code2 size={20} className="flex-shrink-0" />
          <span>View Demo</span>
        </Link>
      </div>

      <div className="flex items-center justify-center lg:justify-start gap-8 text-sm text-text-tertiary flex-wrap w-full">
        {heroContent.trustSignals.map((signal, index) => (
          <div key={index} className="trust-signal flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="w-full">{signal}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6 pt-8 border-t border-border-subtle w-full">
        {heroContent.proofStats.map((stat, index) => (
          <div
            key={index}
            className="stat-item text-center lg:text-left w-full"
          >
            <div
              className="text-2xl font-bold w-full"
              style={{ color: "var(--text-primary)" }}
            >
              {stat.value}
            </div>
            <div className="text-xs text-text-tertiary mt-1 w-full">
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
