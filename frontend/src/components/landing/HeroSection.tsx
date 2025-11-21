import { useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useHeroAnimations } from "./HeroSection/hooks/use-hero-animations";
import { HeroContent } from "./HeroSection/components/hero-content";
import { CodePreview } from "./HeroSection/components/code-preview";

// Register GSAP plugins
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export default function HeroSection() {
  const heroRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const codeRef = useRef<HTMLDivElement>(null);

  useHeroAnimations({
    heroRef,
    contentRef,
    titleRef,
    subtitleRef,
    ctaRef,
    codeRef,
  });

  return (
    <section
      ref={heroRef}
      className="relative min-h-screen w-full min-w-0 flex items-center justify-center overflow-hidden pt-20"
    >
      <div className="absolute inset-0 bg-gradient-to-b from-brand-violet/10 via-transparent to-transparent" />
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(139, 92, 246, 0.1) 1px, transparent 0)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center min-w-0">
          <HeroContent
            contentRef={contentRef}
            titleRef={titleRef}
            subtitleRef={subtitleRef}
            ctaRef={ctaRef}
          />
          <CodePreview codeRef={codeRef} />
        </div>
      </div>
    </section>
  );
}
