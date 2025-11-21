import React, { useState } from "react";
import { ChevronDown, Mail } from "lucide-react";

import { faqItems } from "#/content/landing";

export function BetaFAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="relative py-24 px-6 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-background-secondary via-background to-background" />
      <div className="relative max-w-6xl mx-auto grid gap-12 lg:grid-cols-[1.1fr_1.3fr]">
        <div className="bg-background-primary/70 border border-white/10 rounded-3xl p-10 shadow-[0_20px_80px_-40px_rgba(0,0,0,0.45)] backdrop-blur">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 text-xs uppercase tracking-wider text-foreground/80">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Beta FAQ • Always-on support
          </div>
          <h2 className="mt-6 text-3xl md:text-4xl font-semibold leading-tight text-white">
            Everything you need to run a dependable AI engineering partner.
          </h2>
          <p className="mt-4 text-lg text-foreground-secondary">
            Answers for security teams, founders, and engineering leaders
            evaluating the private beta.
          </p>
          <div className="mt-10 space-y-6 text-sm text-foreground-secondary">
            <p>
              Forge runs entirely inside your network, connects to your own
              model keys, and exposes full observability hooks so nothing is a
              black box.
            </p>
            <div className="flex flex-wrap gap-4">
              <a
                href="mailto:support@all-hands.dev"
                className="inline-flex items-center gap-2 text-brand-400 font-semibold"
              >
                <Mail className="h-4 w-4" />
                Talk to an engineer
              </a>
              <div className="px-4 py-2 rounded-full border border-white/10 text-xs uppercase tracking-widest text-foreground-tertiary">
                Median reply • 15m
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {faqItems.map((item: any, index: number) => (
            <div
              key={item.question}
              className="bg-background-primary/80 border border-white/10 rounded-2xl hover:border-brand-500/40 transition-colors"
            >
              <button
                type="button"
                onClick={() => toggleFAQ(index)}
                className="w-full px-6 py-5 flex items-center justify-between text-left"
                aria-expanded={openIndex === index}
              >
                <span className="text-lg font-medium text-white pr-6">
                  {item.question}
                </span>
                <ChevronDown
                  className={`w-5 h-5 text-foreground-secondary transition-transform duration-300 ${
                    openIndex === index ? "-rotate-180" : ""
                  }`}
                />
              </button>
              <div
                className={`overflow-hidden transition-all duration-300 ${
                  openIndex === index ? "max-h-60" : "max-h-0"
                }`}
              >
                <div className="px-6 pb-6 text-foreground-secondary leading-relaxed">
                  {item.answer}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default BetaFAQ;
