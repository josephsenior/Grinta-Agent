import { useEffect, useRef } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { finalCta } from "#/content/landing";
import { CheckIcon } from "./CheckIcon";

// Register ScrollTrigger
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export default function FinalCTA() {
  const sectionRef = useRef<HTMLElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // GSAP scroll animations
  useEffect(() => {
    if (!sectionRef.current || typeof window === "undefined") {
      return () => {
        // No cleanup needed
      };
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set([cardRef.current, contentRef.current?.children], {
        opacity: 1,
        y: 0,
        scale: 1,
      });
      return () => {
        // No cleanup needed for reduced motion
      };
    }

    // Card entrance animation
    if (cardRef.current) {
      gsap.from(cardRef.current, {
        opacity: 0,
        y: 60,
        scale: 0.95,
        duration: 0.8,
        ease: "back.out(1.2)",
        scrollTrigger: {
          trigger: cardRef.current,
          start: "top 80%",
          toggleActions: "play none none none",
        },
      });
    }

    // Content stagger animation
    if (contentRef.current) {
      gsap.from(contentRef.current.children, {
        opacity: 0,
        y: 30,
        duration: 0.6,
        stagger: 0.1,
        ease: "power3.out",
        scrollTrigger: {
          trigger: cardRef.current,
          start: "top 80%",
          toggleActions: "play none none none",
        },
      });
    }

    // Trust signals animation
    const trustSignals = contentRef.current?.querySelectorAll(".trust-signal");
    if (trustSignals && trustSignals.length > 0) {
      gsap.from(trustSignals, {
        opacity: 0,
        x: -20,
        duration: 0.4,
        stagger: 0.1,
        ease: "power2.out",
        scrollTrigger: {
          trigger: cardRef.current,
          start: "top 80%",
          toggleActions: "play none none none",
        },
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach((trigger) => {
        if (
          trigger.vars.trigger === sectionRef.current ||
          trigger.vars.trigger === cardRef.current
        ) {
          trigger.kill();
        }
      });
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative w-full min-w-0 py-20 lg:py-32 overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-b from-brand-violet/10 via-brand-violet/5 to-transparent" />
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(139, 92, 246, 0.15) 1px, transparent 0)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative w-full min-w-0 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          ref={cardRef}
          className="glass-effect rounded-3xl p-12 lg:p-16 text-center relative overflow-hidden min-w-0"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-violet/20 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/20 rounded-full blur-3xl" />

          <div ref={contentRef} className="relative z-10">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-violet/20 border border-brand-violet/30 rounded-full text-sm text-brand-violetLight mb-8">
              <Sparkles size={16} className="animate-pulse" />
              <span>Private Beta</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-6 w-full">
              {finalCta.heading}
            </h2>

            <p className="text-lg text-text-secondary w-full mb-10">
              {finalCta.body}
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/auth/register"
                className="group px-8 py-4 bg-brand-violet hover:bg-brand-violet-dark text-white font-semibold rounded-xl transition-all duration-300 shadow-glow hover:shadow-glow-lg flex items-center gap-2 whitespace-nowrap"
              >
                <span>{finalCta.primaryCta}</span>
                <ArrowRight
                  size={20}
                  className="group-hover:translate-x-1 transition-transform flex-shrink-0"
                />
              </Link>
              <Link
                to="/pricing"
                className="px-8 py-4 glass-effect font-semibold rounded-xl transition-all duration-300 whitespace-nowrap"
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
                {finalCta.secondaryCta}
              </Link>
            </div>

            <div className="mt-10 flex items-center justify-center gap-8 text-sm text-text-tertiary flex-wrap">
              <div className="trust-signal flex items-center gap-2">
                <CheckIcon />
                <span className="w-full">$1/day free tier</span>
              </div>
              <div className="trust-signal flex items-center gap-2">
                <CheckIcon />
                <span className="w-full">No credit card</span>
              </div>
              <div className="trust-signal flex items-center gap-2">
                <CheckIcon />
                <span className="w-full">Cancel anytime</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
