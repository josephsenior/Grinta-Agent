/**
 * Forge - Brand Configuration
 * Centralized branding and theming configuration
 */

export const BRAND = {
  name: "Forge",
  tagline: "Your AI-Powered Development Platform",
  description:
    "Forge is your AI-powered development platform for building software with intelligent agents. Code less, build more.",

  // Attribution
  attribution: {
    framework: "Advanced AI Agent Framework",
    license: "MIT",
    acknowledgment:
      "Powered by cutting-edge AI agents and production-grade infrastructure",
  },

  // URLs
  urls: {
    website: "https://forge.dev", // Update with actual URL
    github: "https://github.com/All-Hands-AI/Forge",
    docs: "https://docs.forge.dev", // Update with actual URL
    support: "mailto:support@forge.dev", // Update with actual email
  },

  // Features that differentiate from Forge
  features: {
    memory: {
      title: "Enterprise Memory",
      description:
        "Persistent vector-based memory that remembers your entire codebase",
      icon: "🧠",
    },
    quality: {
      title: "World-Class Code Quality",
      description: "9.04/10 Pylint score with zero complexity violations",
      icon: "✨",
    },
    performance: {
      title: "Optimized Performance",
      description: "64% faster with advanced caching and splitting",
      icon: "⚡",
    },
    deployment: {
      title: "Cloud-Ready",
      description: "Deploy anywhere from $0-34/month",
      icon: "☁️",
    },
  },

  // Theme colors (matching Forge-theme.css)
  colors: {
    primary: "#0066FF",
    accent: "#00E5FF",
    energy: "#FF6B00",
    success: "#10B981",
    warning: "#F59E0B",
    error: "#EF4444",
  },
} as const;

export type BrandConfig = typeof BRAND;
