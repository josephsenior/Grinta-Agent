import React, { useState } from "react";
import {
  Check,
  X,
  Star,
  Zap,
  Shield,
  Sparkles,
  ArrowRight,
  HelpCircle,
  ChevronDown,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Badge } from "#/components/ui/badge";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";

interface PricingTier {
  name: string;
  price: number;
  period: string;
  description: string;
  features: string[];
  limitations: string[];
  cta: string;
  popular?: boolean;
  color: "gray" | "violet" | "emerald";
}

const PRICING_TIERS: PricingTier[] = [
  {
    name: "Free",
    price: 0,
    period: "forever",
    description: "Perfect for trying out Forge and small projects",
    features: [
      "Bring Your Own API Key (BYOK)",
      "100 conversations/day",
      "CodeAct autonomous agent",
      "All 200+ LLM models",
      "Real-time cost tracking",
      "Docker sandboxing",
      "GitHub community support",
      "Open source (MIT license)",
    ],
    limitations: [],
    cta: "Start Free",
    color: "gray",
  },
  {
    name: "Pro",
    price: 15,
    period: "month",
    description: "Best for professional developers and small teams",
    features: [
      "$15 in platform credits/month",
      "OR use your own API key (100% margin for you!)",
      "500 conversations/day",
      "All Free features included",
      "Priority queue (faster responses)",
      "Email support (24h response)",
      "Advanced analytics dashboard",
      "Usage insights & optimization tips",
      "Grok 4 Fast + Claude Haiku 4.5 models",
    ],
    limitations: [],
    cta: "Start Pro Trial",
    popular: true,
    color: "violet",
  },
  {
    name: "Pro+",
    price: 25,
    period: "month",
    description: "For power users who need the best performance",
    features: [
      "$25 in premium platform credits/month",
      "OR use your own API key",
      "1000 conversations/day",
      "All Pro features included",
      "Priority support (4h response)",
      "Early access to new features",
      "Dedicated account manager",
      "Custom model routing",
      "Premium models (Claude Sonnet 4, GPT-4o)",
      "White-label options",
    ],
    limitations: [],
    cta: "Start Pro+ Trial",
    color: "emerald",
  },
];

const FEATURE_COMPARISON = [
  {
    category: "Core Features",
    features: [
      { name: "CodeAct autonomous agent", free: true, pro: true, proPlus: true },
      { name: "All LLM models (200+)", free: true, pro: true, proPlus: true },
      { name: "Real-time cost tracking", free: true, pro: true, proPlus: true },
      { name: "BYOK (Bring Your Own Key)", free: true, pro: true, proPlus: true },
      { name: "Docker sandboxing", free: true, pro: true, proPlus: true },
      { name: "Browser automation", free: true, pro: true, proPlus: true },
    ],
  },
  {
    category: "Platform Credits",
    features: [
      { name: "Monthly platform credits", free: false, pro: "$15", proPlus: "$25" },
      { name: "Rollover unused credits", free: false, pro: false, proPlus: true },
      { name: "Credit top-up discount", free: false, pro: "10%", proPlus: "20%" },
    ],
  },
  {
    category: "Usage Limits",
    features: [
      { name: "Conversations per day", free: "100", pro: "500", proPlus: "1000" },
      { name: "Priority queue", free: false, pro: true, proPlus: true },
      { name: "Concurrent sessions", free: "1", pro: "3", proPlus: "10" },
    ],
  },
  {
    category: "Support & Analytics",
    features: [
      { name: "Community support (GitHub)", free: true, pro: true, proPlus: true },
      { name: "Email support", free: false, pro: "24h", proPlus: "4h" },
      { name: "Advanced analytics", free: false, pro: true, proPlus: true },
      { name: "Usage optimization tips", free: false, pro: true, proPlus: true },
      { name: "Dedicated account manager", free: false, pro: false, proPlus: true },
    ],
  },
  {
    category: "Advanced Features",
    features: [
      { name: "Early access to features", free: false, pro: false, proPlus: true },
      { name: "Custom model routing", free: false, pro: false, proPlus: true },
      { name: "White-label options", free: false, pro: false, proPlus: true },
      { name: "API rate limit increase", free: false, pro: false, proPlus: true },
    ],
  },
];

const FAQ_ITEMS = [
  {
    question: "What are platform credits?",
    answer:
      "Platform credits are pre-paid credits you can use with any LLM model without managing individual API keys. $15 in credits typically covers 150-200 conversations with Grok 4 Fast or Claude Haiku 4.5. You can always switch to BYOK if you prefer.",
  },
  {
    question: "Can I use my own API keys on paid plans?",
    answer:
      "Absolutely! All paid plans support BYOK (Bring Your Own Key). This gives you 100% control over your AI costs and privacy. You still get all the premium features like priority queue, analytics, and support.",
  },
  {
    question: "What happens if I exceed my conversation limit?",
    answer:
      "On the Free plan, you'll hit a soft cap at 100 conversations/day (resets at midnight UTC). On Pro/Pro+ plans, the limits are much higher and you can request increases. We'll never hard-block you - we'll just prompt you to upgrade or wait for the daily reset.",
  },
  {
    question: "Which AI models are included?",
    answer:
      "All plans include access to 200+ models from 30+ providers: OpenAI (GPT-4o, GPT-4o Mini), Anthropic (Claude Sonnet 4, Haiku 4.5), Google (Gemini), xAI (Grok 4 Fast), Mistral, Groq, and more. Pro+ plans get priority access to new models.",
  },
  {
    question: "How does billing work?",
    answer:
      "We use Stripe for secure payments. You can pay monthly or annually (save 20%). Cancel anytime - no questions asked. Unused platform credits roll over for Pro+ members, but expire after 3 months for Pro members.",
  },
  {
    question: "Is there a free trial?",
    answer:
      "The Free plan is unlimited in time - use it forever! For paid plans, we offer a 14-day money-back guarantee. Try Pro or Pro+ risk-free, and if you're not satisfied, we'll refund 100% of your payment.",
  },
];

export default function PricingPage(): React.ReactElement {
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const [openFAQIndex, setOpenFAQIndex] = useState<number | null>(null);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "annual">("monthly");

  const onStartPlan = (tierName: string) => {
    createConversation(
      {},
      {
        onSuccess: (data) => {
          try {
            localStorage.setItem("RECENT_CONVERSATION_ID", data.conversation_id);
            // Store selected plan for post-signup flow
            localStorage.setItem("SELECTED_PLAN", tierName.toLowerCase());
          } catch (err) {
            // ignore
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  const toggleFAQ = (index: number) => {
    setOpenFAQIndex(openFAQIndex === index ? null : index);
  };

  const getCardColorClasses = (color: PricingTier["color"], isPopular?: boolean) => {
    if (isPopular) {
      return {
        border: "border-brand-500/40",
        bg: "bg-brand-500/5",
        shadow: "shadow-xl shadow-brand-500/20",
        badge: "bg-brand-500 text-white",
        button: "bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40",
        glow: "from-brand-500/20 to-accent-500/20",
      };
    }

    switch (color) {
      case "violet":
        return {
          border: "border-brand-500/30",
          bg: "bg-brand-500/5",
          shadow: "shadow-lg shadow-brand-500/10",
          badge: "bg-brand-500/20 text-violet-500",
          button: "bg-brand-500/10 text-violet-500 hover:bg-brand-500/20 border-2 border-brand-500/30",
          glow: "from-brand-500/10 to-brand-500/5",
        };
      case "emerald":
        return {
          border: "border-success-500/30",
          bg: "bg-success-500/5",
          shadow: "shadow-lg shadow-success-500/10",
          badge: "bg-success-500/20 text-success-500",
          button: "bg-success-500/10 text-success-500 hover:bg-success-500/20 border-2 border-success-500/30",
          glow: "from-success-500/10 to-success-500/5",
        };
      default:
        return {
          border: "border-border/50",
          bg: "bg-background-secondary/50",
          shadow: "shadow-md",
          badge: "bg-foreground-tertiary/20 text-foreground-secondary",
          button: "bg-foreground/10 text-foreground hover:bg-foreground/20 border-2 border-border",
          glow: "from-foreground/5 to-foreground/5",
        };
    }
  };

  const renderFeatureValue = (value: boolean | string) => {
    if (value === true) {
      return (
        <div className="flex justify-center">
          <div className="w-6 h-6 rounded-full bg-success-500/20 flex items-center justify-center">
            <Check className="w-4 h-4 text-success-500" />
          </div>
        </div>
      );
    }
    if (value === false) {
      return (
        <div className="flex justify-center">
          <div className="w-6 h-6 rounded-full bg-foreground-tertiary/20 flex items-center justify-center">
            <X className="w-4 h-4 text-foreground-tertiary" />
          </div>
        </div>
      );
    }
    return (
      <div className="text-center">
        <Badge variant="secondary" className="bg-brand-500/10 text-violet-500 border-brand-500/20">
          {value}
        </Badge>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background-primary via-background-secondary to-background-primary">
      {/* Header */}
      <section className="relative py-20 px-6 overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 bg-gradient-to-b from-brand-500/5 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-px bg-gradient-to-r from-transparent via-border to-transparent" />

        <div className="relative max-w-7xl mx-auto text-center space-y-6 z-10">
          {/* Badge */}
          <div className="flex justify-center stagger-item delay-0">
            <Badge
              variant="secondary"
              className="glass-modern border-brand-500/30 text-violet-500 px-6 py-3 text-sm font-medium shadow-lg interactive-scale"
            >
              <Sparkles className="w-4 h-4 mr-2 floating-icon" />
              Simple, Transparent Pricing
            </Badge>
          </div>

          {/* Heading */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight tracking-tight stagger-item delay-100">
            <span className="text-foreground block mb-2">
              Choose Your Plan
            </span>
            <span className="bg-gradient-to-r from-brand-500 via-accent-500 to-brand-600 bg-clip-text text-transparent gradient-shimmer block">
              Start Free, Scale as You Grow
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-foreground-secondary max-w-3xl mx-auto leading-relaxed stagger-item delay-200">
            All plans include access to 200+ AI models. Use your own API keys for full control, or use platform credits for convenience.
          </p>

          {/* Billing toggle */}
          <div className="flex items-center justify-center gap-4 pt-4 stagger-item delay-300">
            <button
              onClick={() => setBillingPeriod("monthly")}
              className={cn(
                "px-6 py-3 rounded-lg font-semibold transition-all duration-300",
                billingPeriod === "monthly"
                  ? "bg-brand-500 text-white shadow-lg shadow-brand-500/30"
                  : "text-foreground-secondary hover:text-foreground"
              )}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod("annual")}
              className={cn(
                "px-6 py-3 rounded-lg font-semibold transition-all duration-300 relative",
                billingPeriod === "annual"
                  ? "bg-brand-500 text-white shadow-lg shadow-brand-500/30"
                  : "text-foreground-secondary hover:text-foreground"
              )}
            >
              Annual
              <Badge className="absolute -top-2 -right-2 bg-success-500 text-white text-xs px-2 py-0.5">
                Save 20%
              </Badge>
            </button>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="relative py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            {PRICING_TIERS.map((tier, index) => {
              const colors = getCardColorClasses(tier.color, tier.popular);
              const annualPrice = billingPeriod === "annual" ? Math.round(tier.price * 0.8 * 12) : tier.price;
              const displayPrice = billingPeriod === "annual" ? annualPrice : tier.price;

              return (
                <Card
                  key={tier.name}
                  className={cn(
                    "glass-modern relative overflow-hidden card-hover-lift gpu-accelerated transition-all duration-500",
                    "stagger-item",
                    colors.border,
                    colors.bg,
                    colors.shadow,
                    tier.popular && "scale-105 ring-2 ring-brand-500/30"
                  )}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  {/* Popular badge */}
                  {tier.popular && (
                    <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-brand-500 via-accent-500 to-brand-500 animate-shimmer" />
                  )}

                  {/* Glow effect */}
                  <div className={cn("absolute inset-0 bg-gradient-to-br opacity-50 pointer-events-none", colors.glow)} />

                  <CardHeader className="relative space-y-6">
                    {/* Tier name & badge */}
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-2xl font-bold text-foreground">
                        {tier.name}
                      </CardTitle>
                      {tier.popular && (
                        <Badge className={cn("font-semibold text-xs px-3 py-1", colors.badge)}>
                          <Star className="w-3 h-3 mr-1" />
                          Most Popular
                        </Badge>
                      )}
                    </div>

                    {/* Price */}
                    <div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-5xl font-bold text-foreground">
                          ${displayPrice}
                        </span>
                        <span className="text-foreground-secondary">
                          /{billingPeriod === "annual" ? "year" : tier.period}
                        </span>
                      </div>
                      {billingPeriod === "annual" && tier.price > 0 && (
                        <p className="text-sm text-success-500 mt-2 font-medium">
                          Save ${tier.price * 12 - annualPrice}/year
                        </p>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-sm text-foreground-secondary leading-relaxed">
                      {tier.description}
                    </p>

                    {/* CTA Button */}
                    <Button
                      onClick={() => onStartPlan(tier.name)}
                      disabled={isPending}
                      className={cn(
                        "w-full py-6 text-base font-bold transition-all duration-300 interactive-scale",
                        colors.button
                      )}
                    >
                      {isPending ? (
                        <>
                          <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                          Starting...
                        </>
                      ) : (
                        <>
                          {tier.cta}
                          <ArrowRight className="w-5 h-5 ml-2" />
                        </>
                      )}
                    </Button>
                  </CardHeader>

                  <CardContent className="relative space-y-4">
                    {/* Features list */}
                    <div className="space-y-3">
                      {tier.features.map((feature, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <div className="flex-shrink-0 w-5 h-5 rounded-full bg-success-500/20 flex items-center justify-center mt-0.5">
                            <Check className="w-3 h-3 text-success-500" />
                          </div>
                          <span className="text-sm text-foreground leading-relaxed">
                            {feature}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Trust badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 mt-12 text-sm text-foreground-secondary">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-success-500" />
              <span>14-day money-back guarantee</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-violet-500" />
              <span>Cancel anytime</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-success-500" />
              <span>No credit card required for Free plan</span>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Comparison Table */}
      <section className="relative py-20 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <Badge
              variant="secondary"
              className="glass-modern border-brand-500/30 text-violet-500 px-6 py-3 text-sm font-medium shadow-lg mb-4"
            >
              <HelpCircle className="w-4 h-4 mr-2" />
              Compare Plans
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Feature Comparison
            </h2>
            <p className="text-lg text-foreground-secondary">
              See what's included in each plan
            </p>
          </div>

          {/* Comparison Table */}
          <Card className="glass-modern border-border/50 shadow-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50 bg-background-tertiary/30">
                    <th className="text-left py-6 px-6 text-foreground font-bold text-lg">
                      Features
                    </th>
                    <th className="text-center py-6 px-6 text-foreground font-bold text-lg">
                      Free
                    </th>
                    <th className="text-center py-6 px-6 text-foreground font-bold text-lg">
                      <div className="flex items-center justify-center gap-2">
                        Pro
                        <Star className="w-4 h-4 text-violet-500 fill-violet-500" />
                      </div>
                    </th>
                    <th className="text-center py-6 px-6 text-foreground font-bold text-lg">
                      Pro+
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {FEATURE_COMPARISON.map((category, catIndex) => (
                    <React.Fragment key={category.category}>
                      {/* Category header */}
                      <tr className="bg-background-secondary/50">
                        <td
                          colSpan={4}
                          className="py-4 px-6 text-sm font-bold text-violet-500 uppercase tracking-wide"
                        >
                          {category.category}
                        </td>
                      </tr>
                      {/* Features */}
                      {category.features.map((feature, featureIndex) => (
                        <tr
                          key={featureIndex}
                          className="border-b border-border/30 hover:bg-background-tertiary/20 transition-colors"
                        >
                          <td className="py-4 px-6 text-foreground">
                            {feature.name}
                          </td>
                          <td className="py-4 px-6">
                            {renderFeatureValue(feature.free)}
                          </td>
                          <td className="py-4 px-6 bg-brand-500/5">
                            {renderFeatureValue(feature.pro)}
                          </td>
                          <td className="py-4 px-6">
                            {renderFeatureValue(feature.proPlus)}
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="relative py-20 px-6 bg-background-secondary/50">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <Badge
              variant="secondary"
              className="glass-modern border-brand-500/30 text-violet-500 px-6 py-3 text-sm font-medium shadow-lg mb-4"
            >
              <HelpCircle className="w-4 h-4 mr-2" />
              FAQ
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-lg text-foreground-secondary">
              Everything you need to know about our pricing
            </p>
          </div>

          {/* FAQ Items */}
          <div className="space-y-4">
            {FAQ_ITEMS.map((item, index) => (
              <Card
                key={index}
                className="glass-modern border-border/50 hover:border-brand-500/30 transition-all duration-300 overflow-hidden"
              >
                <button
                  onClick={() => toggleFAQ(index)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-background-tertiary/20 transition-colors"
                >
                  <span className="text-lg font-semibold text-foreground pr-8">
                    {item.question}
                  </span>
                  <ChevronDown
                    className={cn(
                      "w-5 h-5 text-foreground-secondary flex-shrink-0 transition-transform duration-300",
                      openFAQIndex === index && "rotate-180"
                    )}
                  />
                </button>
                <div
                  className={cn(
                    "overflow-hidden transition-all duration-300",
                    openFAQIndex === index ? "max-h-96" : "max-h-0"
                  )}
                >
                  <div className="px-6 pb-5 text-foreground-secondary leading-relaxed">
                    {item.answer}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* Contact CTA */}
          <div className="mt-12 text-center">
            <p className="text-foreground-secondary mb-4">
              Still have questions?
            </p>
            <a
              href="mailto:support@all-hands.dev"
              className="text-violet-500 hover:text-brand-600 font-medium hover:underline inline-flex items-center gap-2"
            >
              Contact our support team
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <Card className="glass-modern gradient-border-animated border-brand-500/40 shadow-2xl shadow-brand-500/20 overflow-hidden">
            <CardContent className="p-12 text-center">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 mb-4">
                  <Zap className="w-4 h-4 text-violet-500" />
                  <span className="text-sm font-medium text-violet-500">
                    Ready to get started?
                  </span>
                </div>

                <h3 className="text-3xl md:text-4xl font-bold text-foreground">
                  Start Building with AI Today
                </h3>

                <p className="text-lg text-foreground-secondary max-w-2xl mx-auto">
                  Join 50,000+ developers who are shipping code 10x faster with Forge
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                  <Button
                    onClick={() => onStartPlan("Free")}
                    disabled={isPending}
                    className="gradient-brand text-white px-12 py-6 text-lg font-bold shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40 transition-all duration-300 hover:scale-105"
                  >
                    {isPending ? "Starting..." : "Start Free"}
                    <ArrowRight className="w-5 h-5 ml-3" />
                  </Button>

                  <Button
                    variant="outline"
                    className="border-border hover:border-brand-500/50 text-foreground hover:text-violet-500 px-12 py-6 text-lg font-semibold"
                    onClick={() => navigate("/contact")}
                  >
                    Contact Sales
                  </Button>
                </div>

                <div className="flex items-center justify-center gap-6 text-sm text-foreground-tertiary pt-4">
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-success-500" />
                    <span>No credit card required</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-success-500" />
                    <span>Cancel anytime</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-success-500" />
                    <span>14-day money-back</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

