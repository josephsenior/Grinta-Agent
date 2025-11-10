import React, { useRef } from "react";
import { Sparkles, ArrowRight, Github, CheckCircle } from "lucide-react";
import { useScrollReveal } from "#/hooks/use-scroll-reveal";
import { useMagneticHover } from "#/hooks/use-mouse-position";
import { soundEffects } from "#/utils/sound-effects";

export function FinalCTA() {
  const { ref, isVisible } = useScrollReveal({
    threshold: 0.2,
    triggerOnce: true,
  });
  const primaryButtonRef = useRef<HTMLAnchorElement>(null);
  const secondaryButtonRef = useRef<HTMLAnchorElement>(null);

  const primaryMagnetic = useMagneticHover(primaryButtonRef, 0.3);
  const secondaryMagnetic = useMagneticHover(secondaryButtonRef, 0.25);

  return (
    <section ref={ref} className="py-20 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <div
          className={`relative overflow-hidden rounded-3xl ${isVisible ? "bento-card delay-0" : "opacity-0"}`}
        >
          {/* Enhanced gradient background */}
          <div className="absolute inset-0 bg-gradient-to-br from-brand-500 via-brand-600 to-purple-600 opacity-95" />

          {/* Animated background elements */}
          <div
            className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl animate-pulse"
            style={{ animationDelay: "0s" }}
          />
          <div
            className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-accent-500/20 rounded-full blur-3xl animate-pulse"
            style={{ animationDelay: "1s" }}
          />
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-brand-400/15 rounded-full blur-2xl animate-pulse"
            style={{ animationDelay: "2s" }}
          />

          {/* Content */}
          <div className="relative z-10 p-12 md:p-16">
            <div className="text-center">
              {/* Icon with enhanced glow */}
              <div className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center morphing-icon shadow-2xl shadow-white/20 interactive-scale">
                <Sparkles className="w-10 h-10 text-white floating-icon" />
              </div>

              {/* Heading - Benefit-driven */}
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 text-glow">
                Stop Writing Boilerplate.{" "}
                <span className="text-gradient-animated bg-gradient-to-r from-white via-accent-100 to-white bg-clip-text text-transparent">
                  Start Shipping Features.
                </span>
              </h2>
              <p className="text-xl text-white/90 max-w-2xl mx-auto mb-10 leading-relaxed">
                Join 50,000+ developers who eliminated 80% of repetitive coding.
                From idea to deployed app in minutes, not weeks.
              </p>

              {/* CTAs with magnetic hover */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
                <a
                  ref={primaryButtonRef}
                  href="/conversations/new"
                  onMouseEnter={() => soundEffects.hover()}
                  onClick={() => soundEffects.success()}
                  className="magnetic-button button-shine inline-flex items-center px-10 py-5 bg-white text-brand-600 font-bold rounded-xl hover:bg-gray-50 transition-all duration-300 shadow-2xl shadow-black/50 interactive-scale overflow-hidden gpu-accelerated group"
                  style={{
                    transform: `translate(${primaryMagnetic.offset.x}px, ${primaryMagnetic.offset.y}px)`,
                  }}
                >
                  Try Free - No Credit Card
                  <ArrowRight className="w-5 h-5 ml-3 group-hover:translate-x-2 transition-transform duration-300" />
                </a>
                <a
                  ref={secondaryButtonRef}
                  href="https://github.com/All-Hands-AI/Forge"
                  target="_blank"
                  rel="noopener noreferrer"
                  onMouseEnter={() => soundEffects.hover()}
                  onClick={() => soundEffects.click()}
                  className="magnetic-button inline-flex items-center px-10 py-5 bg-white/10 backdrop-blur-md text-white font-semibold rounded-xl hover:bg-white/20 transition-all duration-300 border-2 border-white/30 hover:border-white/50 shadow-xl interactive-scale gpu-accelerated group"
                  style={{
                    transform: `translate(${secondaryMagnetic.offset.x}px, ${secondaryMagnetic.offset.y}px)`,
                  }}
                >
                  <Github className="w-5 h-5 mr-3 group-hover:rotate-12 transition-transform duration-300" />
                  Star on GitHub
                </a>
              </div>

              {/* Trust indicators with enhanced styling */}
              <div className="pt-8 border-t border-white/20">
                <div className="flex flex-wrap justify-center gap-6 text-white/90 text-sm">
                  <div className="flex items-center gap-2 glass-modern px-4 py-2 rounded-full interactive-scale">
                    <CheckCircle className="w-5 h-5 text-white" />
                    <span>Free & Open Source</span>
                  </div>
                  <div className="flex items-center gap-2 glass-modern px-4 py-2 rounded-full interactive-scale">
                    <CheckCircle className="w-5 h-5 text-white" />
                    <span>No Credit Card Required</span>
                  </div>
                  <div className="flex items-center gap-2 glass-modern px-4 py-2 rounded-full interactive-scale">
                    <CheckCircle className="w-5 h-5 text-white" />
                    <span>2 Minute Setup</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default FinalCTA;
