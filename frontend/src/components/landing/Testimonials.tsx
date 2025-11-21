import { useState, useEffect, useRef } from "react";
import { ChevronLeft, ChevronRight, Star, Quote } from "lucide-react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { testimonials } from "#/content/landing";

// Register ScrollTrigger
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const testimonialsData = testimonials.map((testimonial, index) => ({
  id: index + 1,
  name: testimonial.name,
  title: `${testimonial.role} at ${testimonial.company}`,
  avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(testimonial.name)}&background=8b5cf6&color=fff&size=200`,
  content: testimonial.quote,
  rating: 5,
}));

export default function Testimonials() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const prevIndexRef = useRef(0);

  // GSAP scroll animations for section entrance
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
      gsap.set([headingRef.current, cardRef.current], {
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

    return (): void => {
      ScrollTrigger.getAll().forEach((trigger) => {
        if (
          trigger.vars.trigger === sectionRef.current ||
          trigger.vars.trigger === headingRef.current ||
          trigger.vars.trigger === cardRef.current
        ) {
          trigger.kill();
        }
      });
    };
  }, []);

  // GSAP carousel transition animations
  useEffect(() => {
    if (!contentRef.current || typeof window === "undefined") {
      return (): void => {
        // No cleanup needed
      };
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      return (): void => {
        // No cleanup needed for reduced motion
      };
    }

    const content = contentRef.current;
    const direction = currentIndex > prevIndexRef.current ? 1 : -1;

    // Exit animation
    gsap.to(content, {
      opacity: 0,
      x: direction * 30,
      duration: 0.3,
      ease: "power2.in",
      onComplete: () => {
        // Enter animation
        gsap.fromTo(
          content,
          {
            opacity: 0,
            x: direction * -30,
          },
          {
            opacity: 1,
            x: 0,
            duration: 0.5,
            ease: "power3.out",
          },
        );
      },
    });

    prevIndexRef.current = currentIndex;

    return (): void => {
      // No cleanup needed
    };
  }, [currentIndex]);

  // Auto-play carousel
  useEffect(() => {
    if (!isAutoPlaying) {
      return (): void => {
        // No cleanup needed
      };
    }

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % testimonialsData.length);
    }, 5000);

    return (): void => {
      clearInterval(interval);
    };
  }, [isAutoPlaying]);

  const handlePrevious = () => {
    setIsAutoPlaying(false);
    setCurrentIndex(
      (prev) => (prev - 1 + testimonialsData.length) % testimonialsData.length,
    );
  };

  const handleNext = () => {
    setIsAutoPlaying(false);
    setCurrentIndex((prev) => (prev + 1) % testimonialsData.length);
  };

  const currentTestimonial = testimonialsData[currentIndex];

  return (
    <section
      ref={sectionRef}
      id="testimonials"
      className="relative w-full min-w-0 py-20 lg:py-32 overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-brand-violet/5 to-transparent" />

      <div className="relative w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div ref={headingRef} className="text-center mb-16 lg:mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-violet/10 border border-brand-violet/20 rounded-full text-sm text-brand-violetLight mb-6">
            <span>Testimonials</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-6 w-full">
            Loved by
            <br />
            <span className="text-gradient">Developers Worldwide</span>
          </h2>
          <p className="text-lg text-text-secondary w-full">
            Join thousands of teams who have accelerated their development with
            Forge.
          </p>
        </div>

        <div className="w-full">
          <div
            ref={cardRef}
            className="relative glass-effect rounded-3xl p-8 lg:p-12 overflow-hidden w-full"
          >
            <div className="absolute top-8 left-8 text-brand-violet/20">
              <Quote size={64} />
            </div>

            <div ref={contentRef} className="relative w-full">
              <div className="flex items-center justify-center mb-8 w-full">
                <img
                  src={currentTestimonial.avatar}
                  alt={currentTestimonial.name}
                  className="w-20 h-20 rounded-full border-4 border-brand-violet/30 object-cover"
                />
              </div>

              <div className="flex items-center justify-center mb-6 w-full">
                {[...Array(currentTestimonial.rating)].map((_, i) => (
                  <Star
                    key={i}
                    size={20}
                    className="text-yellow-500 fill-yellow-500"
                  />
                ))}
              </div>

              <blockquote className="text-xl lg:text-2xl text-center text-text-primary mb-8 leading-relaxed w-full block">
                &quot;{currentTestimonial.content}&quot;
              </blockquote>

              <div className="text-center w-full">
                <div
                  className="font-semibold mb-1 w-full block"
                  style={{ color: "var(--text-primary)" }}
                >
                  {currentTestimonial.name}
                </div>
                <div className="text-text-tertiary text-sm w-full block">
                  {currentTestimonial.title}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center mt-8 gap-4">
            <button
              type="button"
              onClick={handlePrevious}
              className="p-3 glass-effect rounded-lg transition-all duration-200"
              onMouseEnter={(e) => {
                const target = e.currentTarget;
                target.style.backgroundColor = "var(--bg-elevated)";
              }}
              onMouseLeave={(e) => {
                const target = e.currentTarget;
                target.style.backgroundColor = "var(--glass-bg)";
              }}
              aria-label="Previous testimonial"
            >
              <ChevronLeft size={24} className="text-text-secondary" />
            </button>

            <div className="flex gap-2">
              {testimonialsData.map((_, index) => (
                <button
                  type="button"
                  key={index}
                  onClick={() => {
                    setIsAutoPlaying(false);
                    setCurrentIndex(index);
                  }}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    index === currentIndex ? "bg-brand-violet w-8" : "w-2"
                  }`}
                  style={{
                    backgroundColor:
                      index === currentIndex ? undefined : "var(--bg-tertiary)",
                  }}
                  aria-label={`Go to testimonial ${index + 1}`}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={handleNext}
              className="p-3 glass-effect rounded-lg transition-all duration-200"
              onMouseEnter={(e) => {
                const target = e.currentTarget;
                target.style.backgroundColor = "var(--bg-elevated)";
              }}
              onMouseLeave={(e) => {
                const target = e.currentTarget;
                target.style.backgroundColor = "var(--glass-bg)";
              }}
              aria-label="Next testimonial"
            >
              <ChevronRight size={24} className="text-text-secondary" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
