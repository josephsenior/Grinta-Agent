import React from "react";
import { Link } from "react-router-dom";
import { Check, ArrowRight, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { useScrollReveal } from "#/hooks/use-scroll-reveal";
import { cn } from "#/utils/utils";
import { PRICING_TIERS_PREVIEW } from "#/constants/pricing";

/**
 * Pricing Preview Component
 * Shows 3 pricing tiers as a preview on the landing page
 * Matches design system specifications
 */
export function PricingPreview() {
  const { ref, isVisible } = useScrollReveal({
    threshold: 0.2,
    triggerOnce: true,
  });

  const tiers = PRICING_TIERS_PREVIEW.map((tier) => ({
    ...tier,
    price: `$${tier.price}`,
  }));

  const getColorClasses = (color: "gray" | "violet" | "emerald") => {
    switch (color) {
      case "violet":
        return {
          border: "border-[rgba(139,92,246,0.1)]",
          bg: "bg-[rgba(139,92,246,0.05)]",
          text: "text-[#8b5cf6]",
          button: "bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed]",
        };
      case "emerald":
        return {
          border: "border-[rgba(16,185,129,0.1)]",
          bg: "bg-[rgba(16,185,129,0.05)]",
          text: "text-[#10B981]",
          button: "bg-gradient-to-r from-[#10B981] to-[#059669]",
        };
      default:
        return {
          border: "border-[#1a1a1a]",
          bg: "bg-[#000000]",
          text: "text-[#FFFFFF]",
          button: "bg-[#000000] border border-[#1a1a1a]",
        };
    }
  };

  return (
    <section ref={ref} className="py-20 px-6 relative">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div
          className={cn(
            "text-center mb-12 max-w-3xl min-w-[400px] mx-auto",
            isVisible ? "stagger-item delay-0" : "opacity-0",
          )}
        >
          <h2 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-4 whitespace-normal">
            Simple, Transparent Pricing
          </h2>
          <p className="text-lg text-[#94A3B8] max-w-2xl min-w-[400px] mx-auto whitespace-normal">
            Choose the plan that fits your needs. All plans include BYOK option.
          </p>
        </div>

        {/* Pricing Cards - 3 columns */}
        <div className="grid md:grid-cols-3 gap-6">
          {tiers.map((tier, index) => {
            const colors = getColorClasses(tier.color);
            return (
              <Card
                key={tier.name}
                className={cn(
                  "bg-[#000000] border rounded-xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.15)] transition-all duration-300",
                  tier.popular
                    ? "border-[rgba(139,92,246,0.3)] shadow-[0_8px_40px_rgba(139,92,246,0.2)] scale-105"
                    : colors.border,
                  isVisible
                    ? `stagger-item delay-${(index + 1) * 100}`
                    : "opacity-0",
                  "hover:shadow-[0_8px_40px_rgba(0,0,0,0.2)]",
                )}
              >
                {tier.popular && (
                  <div className="mb-4">
                    <Badge className="bg-[rgba(139,92,246,0.12)] text-[#8b5cf6] border-[rgba(139,92,246,0.3)]">
                      <Star className="h-3 w-3 mr-1" />
                      Most Popular
                    </Badge>
                  </div>
                )}

                <CardHeader className="p-0 mb-6">
                  <CardTitle className="text-[1.5rem] font-semibold text-[#FFFFFF] mb-2">
                    {tier.name}
                  </CardTitle>
                  <div className="flex items-baseline gap-2">
                    <span className="text-[2.25rem] font-bold text-[#FFFFFF]">
                      {tier.price}
                    </span>
                    <span className="text-sm text-[#94A3B8]">
                      /{tier.period}
                    </span>
                  </div>
                  <p className="text-sm text-[#94A3B8] mt-2">
                    {tier.description}
                  </p>
                </CardHeader>

                <CardContent className="p-0 space-y-6">
                  <ul className="space-y-3">
                    {tier.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <Check className="h-5 w-5 text-[#10B981] flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-[#F1F5F9]">
                          {feature}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    asChild
                    className={cn(
                      "w-full rounded-lg px-6 py-3 font-semibold transition-all duration-150",
                      tier.popular
                        ? `${colors.button} text-white hover:brightness-110`
                        : "bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6]",
                    )}
                  >
                    <Link to="/pricing">
                      {tier.cta}
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Footer note */}
        <div
          className={cn(
            "text-center mt-8",
            isVisible ? "stagger-item delay-400" : "opacity-0",
          )}
        >
          <p className="text-sm text-[#94A3B8]">
            All plans include 14-day money-back guarantee.{" "}
            <Link
              to="/pricing"
              className="text-[#8b5cf6] hover:text-[#a78bfa] transition-colors"
            >
              View full pricing details →
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}

export default PricingPreview;
