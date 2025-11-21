import { useEffect, useRef } from "react";
import { Upload, Settings, Rocket } from "lucide-react";
import { Link } from "react-router-dom";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { howItWorksSteps } from "#/content/landing";

// Register ScrollTrigger
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const stepIcons = [Upload, Settings, Rocket];

const steps = howItWorksSteps.map((step, index) => ({
  ...step,
  icon: stepIcons[index] || Upload,
  number: `0${index + 1}`,
}));

export default function HowItWorks() {
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLDivElement>(null);
  const stepsRef = useRef<HTMLDivElement>(null);
  const lineRef = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);

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
      gsap.set(
        [headingRef.current, stepsRef.current?.children, ctaRef.current],
        {
          opacity: 1,
          y: 0,
          scale: 1,
        },
      );
      return () => {
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

    // Connecting line animation
    if (lineRef.current) {
      gsap.fromTo(
        lineRef.current,
        { scaleX: 0, transformOrigin: "left center" },
        {
          scaleX: 1,
          duration: 1.2,
          ease: "power2.out",
          scrollTrigger: {
            trigger: stepsRef.current,
            start: "top 75%",
            toggleActions: "play none none none",
          },
        },
      );
    }

    // Steps stagger animation
    if (stepsRef.current) {
      const stepCards = Array.from(stepsRef.current.children);

      // Set initial state
      gsap.set(stepCards, {
        opacity: 0,
        y: 60,
        scale: 0.9,
      });

      // Animate on scroll
      gsap.to(stepCards, {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.8,
        stagger: 0.2,
        ease: "back.out(1.2)",
        scrollTrigger: {
          trigger: stepsRef.current,
          start: "top 75%",
          toggleActions: "play none none none",
        },
      });

      // Icon animation on each step
      stepCards.forEach((card) => {
        const icon = card.querySelector("svg");
        if (icon) {
          gsap.from(icon, {
            scale: 0,
            rotation: -180,
            duration: 0.6,
            ease: "back.out(2)",
            scrollTrigger: {
              trigger: card,
              start: "top 80%",
              toggleActions: "play none none none",
            },
          });
        }

        // Number animation
        const number = card.querySelector("span");
        if (number) {
          gsap.from(number, {
            opacity: 0,
            scale: 0.5,
            duration: 0.5,
            ease: "power2.out",
            scrollTrigger: {
              trigger: card,
              start: "top 80%",
              toggleActions: "play none none none",
            },
          });
        }
      });
    }

    // CTA button animation
    if (ctaRef.current) {
      gsap.from(ctaRef.current, {
        opacity: 0,
        y: 30,
        duration: 0.6,
        ease: "power3.out",
        scrollTrigger: {
          trigger: ctaRef.current,
          start: "top 85%",
          toggleActions: "play none none none",
        },
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach((trigger) => {
        if (
          trigger.vars.trigger === sectionRef.current ||
          trigger.vars.trigger === headingRef.current ||
          trigger.vars.trigger === stepsRef.current ||
          trigger.vars.trigger === ctaRef.current
        ) {
          trigger.kill();
        }
      });
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className="relative w-full min-w-0 py-20 lg:py-32 overflow-hidden"
    >
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/4 w-96 h-96 bg-brand-violet/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div ref={headingRef} className="text-center mb-16 lg:mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-violet/10 border border-brand-violet/20 rounded-full text-sm text-brand-violetLight mb-6">
            <span>How It Works</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-6 w-full">
            Get Started in
            <br />
            <span className="text-gradient">Three Simple Steps</span>
          </h2>
          <p className="text-lg text-text-secondary w-full">
            From idea to production in minutes. Our streamlined workflow makes
            deployment effortless.
          </p>
        </div>

        <div className="relative">
          <div
            ref={lineRef}
            className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-brand-violet/30 to-transparent -translate-y-1/2"
          />

          <div
            ref={stepsRef}
            className="grid md:grid-cols-3 gap-8 lg:gap-12 min-w-0"
          >
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={step.number} className="relative min-w-0">
                  <div className="relative z-10 text-center">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-violet to-brand-violet-dark shadow-glow mb-6">
                      <Icon size={32} className="text-white" />
                    </div>

                    <div className="mb-4">
                      <span className="text-6xl font-bold text-transparent bg-gradient-to-br from-brand-violet/20 to-brand-violet/10 bg-clip-text">
                        {step.number}
                      </span>
                    </div>

                    <h3
                      className="text-2xl font-semibold mb-4 w-full"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {step.title}
                    </h3>
                    <p className="text-text-secondary leading-relaxed w-full">
                      {step.description}
                    </p>
                  </div>

                  {index < steps.length - 1 && (
                    <div className="hidden md:block absolute top-10 left-full w-12 lg:w-24 h-0.5 bg-gradient-to-r from-brand-violet/50 to-transparent" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div ref={ctaRef} className="mt-16 text-center">
          <Link
            to="/auth/register"
            className="group px-8 py-4 bg-brand-violet hover:bg-brand-violet-dark text-white font-semibold rounded-xl transition-all duration-300 shadow-glow hover:shadow-glow-lg inline-flex items-center gap-2 whitespace-nowrap"
          >
            <span>Start Your Free Trial</span>
            <Rocket
              size={20}
              className="group-hover:translate-x-1 transition-transform flex-shrink-0"
            />
          </Link>
        </div>
      </div>
    </section>
  );
}
