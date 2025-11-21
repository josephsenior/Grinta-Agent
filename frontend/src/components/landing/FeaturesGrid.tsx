import { useEffect, useRef } from "react";
import { Zap, Shield, Layers, GitBranch, Globe, Lock } from "lucide-react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { featureHighlights } from "#/content/landing";

// Register ScrollTrigger
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const featureIcons: Record<string, typeof Zap> = {
  "CodeAct, merge-grade edits": Zap,
  "Ultimate Editor": Layers,
  "ACE learning loops": GitBranch,
  "Hybrid memory": Globe,
  "Guardrails & cost controls": Shield,
  "Observability from day one": Lock,
};

const features = featureHighlights.map((feature) => ({
  icon: featureIcons[feature.title] || Zap,
  title: feature.title,
  description: feature.description,
}));

export default function FeaturesGrid() {
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);

  // GSAP scroll animations
  useEffect(() => {
    if (!sectionRef.current || typeof window === "undefined") {
      return (): void => {
        // No cleanup needed
      };
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set([headingRef.current, cardsRef.current?.children], {
        opacity: 1,
        y: 0,
        scale: 1,
      });
      return (): void => {
        // No cleanup needed for reduced motion
      };
    }

    // Heading animation
    if (headingRef.current) {
      gsap.from(headingRef.current.children, {
        opacity: 0,
        y: 30,
        duration: 0.8,
        stagger: 0.1,
        ease: "power3.out",
        scrollTrigger: {
          trigger: headingRef.current,
          start: "top 85%",
          toggleActions: "play none none none",
        },
      });
    }

    // Cards stagger animation
    if (cardsRef.current) {
      const cards = Array.from(cardsRef.current.children);

      // Set initial state
      gsap.set(cards, {
        opacity: 0,
        y: 60,
        scale: 0.9,
      });

      // Animate on scroll
      gsap.to(cards, {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.8,
        stagger: 0.15,
        ease: "back.out(1.2)",
        scrollTrigger: {
          trigger: cardsRef.current,
          start: "top 75%",
          toggleActions: "play none none none",
        },
      });

      // Enhanced hover effects with GSAP
      cards.forEach((card) => {
        const cardElement = card as HTMLElement;

        cardElement.addEventListener("mouseenter", () => {
          gsap.to(cardElement, {
            y: -10,
            scale: 1.02,
            duration: 0.3,
            ease: "power2.out",
          });
        });

        cardElement.addEventListener("mouseleave", () => {
          gsap.to(cardElement, {
            y: 0,
            scale: 1,
            duration: 0.3,
            ease: "power2.out",
          });
        });
      });
    }

    return (): void => {
      ScrollTrigger.getAll().forEach((trigger) => {
        if (
          trigger.vars.trigger === sectionRef.current ||
          trigger.vars.trigger === headingRef.current ||
          trigger.vars.trigger === cardsRef.current
        ) {
          trigger.kill();
        }
      });
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      id="features"
      className="relative w-full min-w-0 py-20 lg:py-32"
    >
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-brand-violet/5 to-transparent" />

      <div className="relative w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div ref={headingRef} className="text-center mb-16 lg:mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-violet/10 border border-brand-violet/20 rounded-full text-sm text-brand-violetLight mb-6">
            <span>Features</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-6 w-full">
            Everything You Need,
            <br />
            <span className="text-gradient">Right Out of the Box</span>
          </h2>
          <p className="text-lg text-text-secondary w-full">
            Powerful features designed to accelerate your development workflow
            and scale with your business.
          </p>
        </div>

        <div
          ref={cardsRef}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8 min-w-0"
        >
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group glass-effect rounded-2xl p-8 transition-all duration-300 hover-lift min-w-0"
                onMouseEnter={(e) => {
                  const target = e.currentTarget;
                  target.style.backgroundColor = "var(--bg-elevated)";
                }}
                onMouseLeave={(e) => {
                  const target = e.currentTarget;
                  target.style.backgroundColor = "var(--glass-bg)";
                }}
              >
                <div className="w-12 h-12 rounded-xl bg-brand-violet/20 flex items-center justify-center mb-6 group-hover:bg-brand-violet/30 transition-colors duration-300">
                  <Icon size={24} className="text-brand-violetLight" />
                </div>
                <h3
                  className="text-xl font-semibold mb-3 w-full"
                  style={{ color: "var(--text-primary)" }}
                >
                  {feature.title}
                </h3>
                <p className="text-text-secondary leading-relaxed w-full">
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
