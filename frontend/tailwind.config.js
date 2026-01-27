/** @type {import('tailwindcss').Config} */
import { heroui } from "@heroui/react";
import typography from "@tailwindcss/typography";

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,html}",
    "./src/**/**/*.css",
    // include any tests or story files that may contain Tailwind classes
    "./__tests__/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      letterSpacing: {
        "brand-tight": "-0.015em",
      },
      boxShadow: {
        "brand-focus":
          "0 0 0 2px rgba(0,0,0,0.9), 0 0 0 4px rgba(189,147,249,0.5)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        outfit: ["Inter", "sans-serif"], // Keep outfit alias for compatibility
        mono: ["JetBrains Mono", "monospace"],
      },
      fontSize: {
        xxs: ["0.75rem", { lineHeight: "1.5" }], // 12px, lineHeight 1.5
        xs: ["0.875rem", { lineHeight: "1.5" }], // 14px, lineHeight 1.5
        s: ["1rem", { lineHeight: "1.5" }], // 16px, lineHeight 1.5
        m: ["1.125rem", { lineHeight: "1.5" }], // 18px, lineHeight 1.5
        l: ["1.5rem", { lineHeight: "1.2" }], // 24px, lineHeight 1.2
        xl: ["2rem", { lineHeight: "1.2" }], // 32px, lineHeight 1.2
        xxl: ["2.25rem", { lineHeight: "1.2" }], // 36px, lineHeight 1.2
        xxxl: ["3rem", { lineHeight: "1.2" }], // 48px, lineHeight 1.2
      },
      colors: {
        // Sophisticated enterprise palette - inspired by premium tech brands
        primary: {
          50: "#FAFAFA",
          100: "#F4F4F5", 
          200: "#E4E4E7",
          300: "#D4D4D8",
          400: "#A1A1AA",
          500: "#71717A", // Sophisticated zinc
          600: "#52525B",
          700: "#3F3F46",
          800: "#27272A",
          900: "#18181B",
          DEFAULT: "#71717A",
        },

        // Pure Black OLED Background System
        background: {
          DEFAULT: "var(--color-background-primary)",
          surface: "var(--color-background-secondary)",
          elevated: "var(--color-background-secondary)",
          glass: "rgba(7, 16, 40, 0.95)",
          primary: "var(--color-background-primary)",
          secondary: "var(--color-background-secondary)",
          tertiary: "var(--color-background-tertiary)",
        },

        // Violet Brand Colors
        brand: {
          // Design token brand colors
          violet: "#8b5cf6", // Main violet brand
          violetDark: "#7c3aed", // Dark violet variant (camelCase)
          "violet-dark": "#7c3aed", // Dark violet variant (kebab-case for Tailwind classes)
          violetLight: "#a78bfa", // Light violet variant
          "violet-light": "#a78bfa", // Light violet variant (kebab-case for Tailwind classes)
          // Extended brand color scale
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b5cf6", // Main violet brand (alias for violet)
          600: "#7c3aed", // Dark violet (alias for violetDark)
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
          DEFAULT: "#8b5cf6",
        },

        // Luxury accent colors - premium grade
        accent: {
          violet: "#8b5cf6", // Primary brand color
          gold: "#F59E0B", // Luxury gold
          "rose-gold": "#F97316", // Rose gold shimmer
          amber: "#FCD34D", // Bright amber highlight
          navy: "#1E3A8A", // Deep navy blue
          emerald: "#10B981", // Emerald green
          sapphire: "#3B82F6", // Sapphire blue
          platinum: "#E5E7EB", // Platinum silver
          bronze: "#CA8A04", // Bronze accent
          // Legacy colors for backward compatibility
          cyan: "#22D3EE",
          green: "#34D399",
          yellow: "#FBBF24",
          orange: "#FB923C",
          pink: "#F472B6",
          purple: "#A78BFA",
        },

        // Sophisticated semantic colors
        success: { 
          DEFAULT: "#10B981",
          50: "rgba(16, 185, 129, 0.1)",
          100: "rgba(16, 185, 129, 0.2)",
        },
        danger: { 
          DEFAULT: "#EF4444",
          50: "rgba(239, 68, 68, 0.1)",
          100: "rgba(239, 68, 68, 0.2)",
        },
        warning: {
          DEFAULT: "#F59E0B",
          50: "rgba(245, 158, 11, 0.1)",
          100: "rgba(245, 158, 11, 0.2)",
        },
        info: { 
          DEFAULT: "#3B82F6", // Sapphire blue as per design spec
          50: "rgba(59, 130, 246, 0.1)",
          100: "rgba(59, 130, 246, 0.2)",
        },

        // Professional neutral grays
        neutral: {
          50: "#F8FAFC",
          100: "#F1F5F9",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#94A3B8",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#0F172A",
          950: "#020617",
        },

        // Professional text hierarchy
        text: {
          primary: "#FFFFFF",
          secondary: "#F1F5F9", 
          tertiary: "#94A3B8",
          muted: "#6a6f7f",
          accent: "#8b5cf6", // Violet brand
        },

        // Border colors - Violet themed
        border: {
          primary: "#1a1a1a",
          secondary: "#0f0f0f",
          accent: "#8b5cf6", // Violet brand
          subtle: "#151515",
          glass: "rgba(139, 92, 246, 0.1)",
        },

        // Legacy aliases for compatibility
        logo: "#8b5cf6", // Updated to violet brand
        base: "#000000", // Pure black
        "base-secondary": "#0a0a0a", // Slightly elevated black
        basic: "#F8F8F2",
        tertiary: "#6272a4",
        "tertiary-light": "#8be9fd",
        content: "#F8F8F2",
        "content-2": "#BFBFC8",
        
        // Foreground colors
        foreground: {
          DEFAULT: "#FFFFFF",
          primary: "#FFFFFF",
          secondary: "#bfbfc8",
          tertiary: "#8b8fb0",
        },
      },

      spacing: {
        // Design token spacing scale
        xs: "0.25rem", // 4px
        sm: "0.5rem", // 8px
        md: "1rem", // 16px
        lg: "1.5rem", // 24px
        xl: "2rem", // 32px
        "2xl": "3rem", // 48px
        "3xl": "4rem", // 64px
        "4xl": "6rem", // 96px
        // Additional custom spacing
        18: "4.5rem",
        22: "5.5rem",
        88: "22rem",
        112: "28rem",
        128: "32rem",
      },

      lineHeight: {
        tight: "1.2", // Headings
        normal: "1.5", // Body
        relaxed: "1.75", // Long-form content (as per design spec)
      },
      transitionDuration: {
        fast: "150ms", // Micro-interactions
        normal: "300ms", // Standard transitions
        slow: "500ms", // Page transitions
      },
      transitionTimingFunction: {
        "ease-out": "cubic-bezier(0.16, 1, 0.3, 1)", // Entrance
        "ease-in": "cubic-bezier(0.4, 0, 1, 1)", // Exit
        spring: "cubic-bezier(0.68, -0.55, 0.265, 1.55)", // Bouncy
      },
      borderRadius: {
        // Design token border radius scale
        sm: "0.25rem", // 4px
        md: "0.5rem", // 8px
        lg: "0.75rem", // 12px
        xl: "1rem", // 16px
        "2xl": "1.5rem", // 24px
        "3xl": "2rem", // 32px
        full: "9999px", // Pills, circles
      },

      boxShadow: {
        luxury: "0 4px 20px rgba(0, 0, 0, 0.15)",
        "luxury-lg": "0 8px 40px rgba(0, 0, 0, 0.2)",
        "luxury-xl": "0 20px 60px rgba(0, 0, 0, 0.3)",
        glow: "0 0 20px rgba(139, 92, 246, 0.3)",
        "glow-lg": "0 0 40px rgba(139, 92, 246, 0.4)",
        "glow-gold": "0 0 30px rgba(245, 158, 11, 0.5)",
        "glow-emerald": "0 0 30px rgba(16, 185, 129, 0.4)",
        "glow-sapphire": "0 0 30px rgba(59, 130, 246, 0.4)",
      },

      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "fade-in-up": "fadeInUp 0.5s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "slide-down": "slideDown 0.3s ease-out",
        "scale-in": "scaleIn 0.2s ease-out",
        "pulse-glow": "pulseGlow 2s infinite",
        "shimmer": "shimmer 2s linear infinite",
        "toast-enter": "toastEnter 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        "toast-exit": "toastExit 0.2s ease-in",
        "cursor-blink": "cursorBlink 1s step-end infinite",
        // Staggered message animations (bolt.diy inspired)
        "message-enter": "messageEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
        "message-enter-delay-1": "messageEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both",
        "message-enter-delay-2": "messageEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both",
        "message-enter-delay-3": "messageEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both",
        "message-enter-delay-4": "messageEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both",
      },

      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInUp: {
          "0%": { 
            opacity: "0",
            transform: "translateY(10px)",
          },
          "100%": { 
            opacity: "1",
            transform: "translateY(0)",
          },
        },
        slideUp: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideDown: {
          "0%": { transform: "translateY(-10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        scaleIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        // Smooth message entry animation (bolt.diy style)
        messageEnter: {
          "0%": {
            opacity: "0",
            transform: "translateY(8px) scale(0.98)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0) scale(1)",
          },
        },
        // Shimmer animation for skeleton loaders
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        // Toast entrance animation
        toastEnter: {
          "0%": {
            opacity: "0",
            transform: "translateY(-100%) scale(0.9)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0) scale(1)",
          },
        },
        // Toast exit animation
        toastExit: {
          "0%": {
            opacity: "1",
            transform: "translateY(0) scale(1)",
          },
          "100%": {
            opacity: "0",
            transform: "translateY(-20px) scale(0.95)",
          },
        },
        // Cursor blink animation for thinking display
        cursorBlink: {
          "0%, 50%": { opacity: "1" },
          "51%, 100%": { opacity: "0" },
        },
      },
    },
  },
  darkMode: "class",
  plugins: [
    typography,
    heroui(),
    function ({ addBase, addComponents, addUtilities, theme }) {
      addBase({
        ":root": {
          "--color-brand-violet-start": "#a78bfa",
          "--color-brand-violet-mid": "#8b5cf6",
          "--color-brand-violet-end": "#7c3aed",
          "--color-luxury-gradient": "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 50%, #6d28d9 100%)",
        },
      });
      addComponents({
        ".btn": {
          "@apply inline-flex items-center justify-center rounded-md font-medium text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 focus-visible:ring-offset-black disabled:opacity-50 disabled:cursor-not-allowed select-none":
            {},
        },
        ".btn-primary": {
          /* Use transparent background and violet text instead of heavy background or borders */
          background: "transparent",
          color: "var(--color-brand-violet-mid)",
          border: "none",
          "@apply shadow-glow hover:brightness-95": {},
        },
        ".btn-icon": {
          "@apply btn h-10 w-10 p-0 rounded-full bg-background/60 hover:bg-accent-gold/10 text-content hover:text-accent-gold":
            {},
        },
        ".badge-semantic": {
          "@apply inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full":
            {},
        },
        ".badge-success": {
          background: "rgba(80,250,123,0.12)",
          color: "#50fa7b",
        },
        ".badge-warning": {
          background: "rgba(241,250,140,0.12)",
          color: "#f1fa8c",
        },
        ".badge-danger": {
          background: "rgba(255,110,110,0.12)",
          color: "#ff6e6e",
        },
      });
      addUtilities({
        ".gradient-brand-text": {
          background:
            "linear-gradient(90deg,var(--color-brand-violet-start),var(--color-brand-violet-mid),var(--color-brand-violet-end))",
          "-webkit-background-clip": "text",
          color: "transparent",
        },
        ".gradient-luxury-text": {
          background:
            "linear-gradient(135deg, #FBBF24 0%, #F59E0B 50%, #10B981 100%)",
          "-webkit-background-clip": "text",
          color: "transparent",
        },
        ".shadow-glow": {
          boxShadow: "0 0 20px rgba(139, 92, 246, 0.3)",
        },
        ".shadow-glow-lg": {
          boxShadow: "0 0 40px rgba(139, 92, 246, 0.4)",
        },
      });
    },
  ],
};
