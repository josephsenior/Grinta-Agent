/**
 * Shared pricing data constants
 * Used by both the pricing page and pricing preview component
 */

export type PricingTierColor = "gray" | "violet" | "emerald";

export interface PricingTier {
  name: string;
  price: number; // Base price (will be formatted as needed)
  period: string;
  description: string;
  features: string[];
  limitations?: string[];
  cta: string;
  popular?: boolean;
  color: PricingTierColor;
}

/**
 * Base pricing tiers data
 * This is the source of truth for all pricing information
 */
export const PRICING_TIERS: PricingTier[] = [
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

/**
 * Simplified pricing tiers for preview components
 * Uses a subset of features for compact display
 */
export const PRICING_TIERS_PREVIEW: Omit<PricingTier, "limitations">[] =
  PRICING_TIERS.map((tier) => ({
    name: tier.name,
    price: tier.price,
    period: tier.period,
    description: (() => {
      if (tier.name === "Free") return "Perfect for trying out Forge";
      if (tier.name === "Pro") return "Best for professional developers";
      return "For power users";
    })(),
    features: (() => {
      if (tier.name === "Free") {
        return [
          "Bring Your Own API Key",
          "100 conversations/day",
          "CodeAct autonomous agent",
          "All 200+ LLM models",
          "Community support",
        ];
      }
      if (tier.name === "Pro") {
        return [
          "$15 in platform credits/month",
          "OR use your own API key",
          "500 conversations/day",
          "Priority queue",
          "Email support (24h)",
          "Advanced analytics",
        ];
      }
      return [
        "$25 in premium credits/month",
        "OR use your own API key",
        "1000 conversations/day",
        "Priority support (4h)",
        "Early access to features",
        "Dedicated account manager",
      ];
    })(),
    cta: (() => {
      if (tier.name === "Free") return "Get Started";
      if (tier.name === "Pro") return "Start Pro Trial";
      return "Start Pro+ Trial";
    })(),
    popular: tier.popular,
    color: tier.color,
  }));

/**
 * Feature comparison data for the pricing page
 */
export interface FeatureComparisonItem {
  name: string;
  free: boolean | string;
  pro: boolean | string;
  proPlus: boolean | string;
}

export interface FeatureComparisonCategory {
  category: string;
  features: FeatureComparisonItem[];
}

export const FEATURE_COMPARISON: FeatureComparisonCategory[] = [
  {
    category: "Core Features",
    features: [
      {
        name: "CodeAct autonomous agent",
        free: true,
        pro: true,
        proPlus: true,
      },
      { name: "All LLM models (200+)", free: true, pro: true, proPlus: true },
      { name: "Real-time cost tracking", free: true, pro: true, proPlus: true },
      {
        name: "BYOK (Bring Your Own Key)",
        free: true,
        pro: true,
        proPlus: true,
      },
      { name: "Docker sandboxing", free: true, pro: true, proPlus: true },
      { name: "Browser automation", free: true, pro: true, proPlus: true },
    ],
  },
  {
    category: "Platform Credits",
    features: [
      {
        name: "Monthly platform credits",
        free: false,
        pro: "$15",
        proPlus: "$25",
      },
      {
        name: "Rollover unused credits",
        free: false,
        pro: false,
        proPlus: true,
      },
      {
        name: "Credit top-up discount",
        free: false,
        pro: "10%",
        proPlus: "20%",
      },
    ],
  },
  {
    category: "Usage Limits",
    features: [
      {
        name: "Conversations per day",
        free: "100",
        pro: "500",
        proPlus: "1000",
      },
      { name: "Priority queue", free: false, pro: true, proPlus: true },
      { name: "Concurrent sessions", free: "1", pro: "3", proPlus: "10" },
    ],
  },
  {
    category: "Support & Analytics",
    features: [
      {
        name: "Community support (GitHub)",
        free: true,
        pro: true,
        proPlus: true,
      },
      { name: "Email support", free: false, pro: "24h", proPlus: "4h" },
      { name: "Advanced analytics", free: false, pro: true, proPlus: true },
      {
        name: "Usage optimization tips",
        free: false,
        pro: true,
        proPlus: true,
      },
      {
        name: "Dedicated account manager",
        free: false,
        pro: false,
        proPlus: true,
      },
    ],
  },
  {
    category: "Advanced Features",
    features: [
      {
        name: "Early access to features",
        free: false,
        pro: false,
        proPlus: true,
      },
      { name: "Custom model routing", free: false, pro: false, proPlus: true },
      { name: "White-label options", free: false, pro: false, proPlus: true },
      {
        name: "API rate limit increase",
        free: false,
        pro: false,
        proPlus: true,
      },
    ],
  },
];

/**
 * FAQ items for the pricing page
 */
export interface FAQItem {
  question: string;
  answer: string;
}

export const FAQ_ITEMS: FAQItem[] = [
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
