import { useEffect, useRef } from "react";
import { Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { CheckIcon } from "./CheckIcon";
import type { Plan } from "./types";

// Register ScrollTrigger
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const plans: Plan[] = [
  {
    name: "Free",
    price: "0",
    description: "Perfect for experimentation and small projects",
    features: [
      "$1/day free tier credit",
      "Basic agent capabilities",
      "Community support",
      "Core MCP servers",
      "Basic observability",
      "99.9% uptime",
    ],
    cta: "Start Free",
    popular: false,
  },
  {
    name: "Professional",
    price: "49",
    description: "For growing teams and production apps",
    features: [
      "$10/day credit cap",
      "All Free features",
      "Priority support",
      "Advanced analytics",
      "Custom integrations",
      "99.99% uptime SLA",
      "Team collaboration",
      "Advanced security",
    ],
    cta: "Start Free Trial",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "For large organizations with complex needs",
    features: [
      "Everything in Pro",
      "Unlimited usage",
      "Dedicated support",
      "Custom integrations",
      "SLA guarantee",
      "Advanced compliance",
      "SSO & SAML",
      "Custom contract",
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

export default function Pricing() {
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

    // Pricing cards stagger animation
    if (cardsRef.current) {
      const cards = Array.from(cardsRef.current.children);

      // Set initial state
      gsap.set(cards, {
        opacity: 0,
        y: 60,
        scale: 0.95,
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

      // Popular badge animation
      cards.forEach((card) => {
        const badge = card.querySelector(".popular-badge");
        if (badge) {
          gsap.from(badge, {
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

        // Price animation
        const price = card.querySelector(".price-value");
        if (price) {
          gsap.from(price, {
            opacity: 0,
            scale: 0.8,
            duration: 0.5,
            ease: "power2.out",
            scrollTrigger: {
              trigger: card,
              start: "top 80%",
              toggleActions: "play none none none",
            },
          });
        }

        // Features list stagger
        const features = card.querySelectorAll(".feature-item");
        if (features.length > 0) {
          gsap.from(features, {
            opacity: 0,
            x: -20,
            duration: 0.4,
            stagger: 0.05,
            ease: "power2.out",
            scrollTrigger: {
              trigger: card,
              start: "top 80%",
              toggleActions: "play none none none",
            },
          });
        }

        // Enhanced hover effects
        const cardElement = card as HTMLElement;
        cardElement.addEventListener("mouseenter", () => {
          gsap.to(cardElement, {
            y: -8,
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
      id="pricing"
      className="relative w-full min-w-0 py-20 lg:py-32"
    >
      <div className="absolute inset-0">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-brand-violet/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div ref={headingRef} className="text-center mb-16 lg:mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-violet/10 border border-brand-violet/20 rounded-full text-sm text-brand-violetLight mb-6">
            <span>Pricing</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-6 w-full">
            Simple, Transparent
            <br />
            <span className="text-gradient">Pricing for Everyone</span>
          </h2>
          <p className="text-lg text-text-secondary w-full">
            Start free, scale as you grow. No hidden fees, no surprises.
          </p>
        </div>

        <div
          ref={cardsRef}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto min-w-0"
        >
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative glass-effect rounded-2xl p-8 transition-all duration-300 hover-lift min-w-0 ${
                plan.popular ? "border-2 border-brand-violet shadow-glow" : ""
              }`}
            >
              {plan.popular && (
                <div className="popular-badge absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-brand-violet rounded-full text-xs font-semibold text-white flex items-center gap-1">
                  <Zap size={12} />
                  <span>Most Popular</span>
                </div>
              )}

              <div className="mb-8">
                <h3
                  className="text-2xl font-bold mb-2 w-full"
                  style={{ color: "var(--text-primary)" }}
                >
                  {plan.name}
                </h3>
                <p className="text-text-tertiary text-sm w-full">
                  {plan.description}
                </p>
              </div>

              <div className="mb-8">
                <div className="flex items-baseline">
                  {plan.price === "Custom" ? (
                    <span
                      className="price-value text-4xl font-bold"
                      style={{ color: "var(--text-primary)" }}
                    >
                      Custom
                    </span>
                  ) : (
                    <>
                      <span
                        className="price-value text-5xl font-bold"
                        style={{ color: "var(--text-primary)" }}
                      >
                        ${plan.price}
                      </span>
                      <span className="text-text-tertiary ml-2">/month</span>
                    </>
                  )}
                </div>
              </div>

              <Link
                to={plan.price === "Custom" ? "/contact" : "/auth/register"}
                className={`block w-full py-3 rounded-lg font-semibold transition-all duration-300 mb-8 text-center whitespace-nowrap ${
                  plan.popular
                    ? "bg-brand-violet hover:bg-brand-violet-dark text-white shadow-glow hover:shadow-glow-lg"
                    : "border border-border-subtle"
                }`}
                style={
                  plan.popular
                    ? undefined
                    : {
                        backgroundColor: "var(--bg-tertiary)",
                        color: "var(--text-primary)",
                      }
                }
                onMouseEnter={
                  plan.popular
                    ? undefined
                    : (e) => {
                        const target = e.currentTarget;
                        target.style.backgroundColor = "var(--bg-elevated)";
                      }
                }
                onMouseLeave={
                  plan.popular
                    ? undefined
                    : (e) => {
                        const target = e.currentTarget;
                        target.style.backgroundColor = "var(--bg-tertiary)";
                      }
                }
              >
                {plan.cta}
              </Link>

              <div className="space-y-4">
                {plan.features.map((feature) => (
                  <div
                    key={feature}
                    className="feature-item flex items-start gap-3"
                  >
                    <div className="mt-0.5">
                      <CheckIcon className="w-4 h-4 text-brand-violetLight" />
                    </div>
                    <span className="text-text-secondary text-sm w-full">
                      {feature}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <p className="text-text-tertiary text-sm">
            All plans include free tier. No credit card required.
          </p>
        </div>
      </div>
    </section>
  );
}
