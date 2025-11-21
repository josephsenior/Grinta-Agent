import React, { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Sparkles,
  Code,
  Bug,
  FileCode,
  Rocket,
  Lightbulb,
  Terminal,
  Zap,
  BookOpen,
  Wand2,
} from "lucide-react";
import { gsap } from "gsap";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import { useGSAPFadeIn } from "#/hooks/use-gsap-animations";

interface Example {
  id: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  prompt: string;
  category: "build" | "debug" | "learn" | "optimize";
  popular?: boolean;
}

interface EmptyStateProps {
  onSelectExample: (prompt: string) => void;
  className?: string;
}

const EXAMPLES: Example[] = [
  // Build
  {
    id: "build-feature",
    icon: <Code className="h-5 w-5" />,
    title: "Build a new feature",
    description: "Create a REST API endpoint with authentication",
    prompt:
      "Help me build a REST API endpoint with JWT authentication. I want to create user registration and login endpoints.",
    category: "build",
    popular: true,
  },
  {
    id: "create-component",
    icon: <FileCode className="h-5 w-5" />,
    title: "Create React component",
    description: "Build a reusable UI component with TypeScript",
    prompt:
      "Help me create a reusable React component with TypeScript. I need a data table with sorting, filtering, and pagination.",
    category: "build",
    popular: true,
  },
  {
    id: "setup-project",
    icon: <Rocket className="h-5 w-5" />,
    title: "Set up new project",
    description: "Initialize a full-stack application",
    prompt:
      "Help me set up a new full-stack project. I want to use React for frontend, Node.js/Express for backend, and PostgreSQL for database.",
    category: "build",
  },

  // Debug
  {
    id: "fix-bug",
    icon: <Bug className="h-5 w-5" />,
    title: "Debug an error",
    description: "Analyze and fix runtime errors",
    prompt:
      "I'm getting a runtime error in my application. Can you help me debug it?",
    category: "debug",
    popular: true,
  },
  {
    id: "performance-issue",
    icon: <Zap className="h-5 w-5" />,
    title: "Fix performance issues",
    description: "Optimize slow code execution",
    prompt:
      "My application is running slowly. Help me identify and fix performance bottlenecks.",
    category: "debug",
  },

  // Learn
  {
    id: "explain-concept",
    icon: <BookOpen className="h-5 w-5" />,
    title: "Explain a concept",
    description: "Learn about programming patterns",
    prompt:
      "Can you explain the concept of dependency injection with practical examples?",
    category: "learn",
  },
  {
    id: "best-practices",
    icon: <Lightbulb className="h-5 w-5" />,
    title: "Learn best practices",
    description: "Discover coding standards",
    prompt:
      "What are the best practices for structuring a React application? Show me examples.",
    category: "learn",
  },

  // Optimize
  {
    id: "refactor-code",
    icon: <Wand2 className="h-5 w-5" />,
    title: "Refactor code",
    description: "Improve code quality and maintainability",
    prompt:
      "Help me refactor this code to make it more maintainable and follow best practices.",
    category: "optimize",
    popular: true,
  },
  {
    id: "add-tests",
    icon: <Terminal className="h-5 w-5" />,
    title: "Write tests",
    description: "Add comprehensive test coverage",
    prompt:
      "Help me write unit and integration tests for my code. I want to achieve good test coverage.",
    category: "optimize",
  },
];

export function EmptyState({ onSelectExample, className }: EmptyStateProps) {
  const { t } = useTranslation();
  const [selectedCategory] = React.useState<
    "all" | "build" | "debug" | "learn" | "optimize"
  >("all");

  const filteredExamples = React.useMemo(() => {
    if (selectedCategory === "all") {
      return EXAMPLES.filter((e) => e.popular);
    }
    return EXAMPLES.filter((e) => e.category === selectedCategory);
  }, [selectedCategory]);

  const containerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.1,
    duration: 0.6,
  });
  const examplesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!examplesRef.current) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(examplesRef.current.children, { opacity: 1, y: 0 });
      return;
    }

    // Stagger animation for example cards
    const cards = Array.from(examplesRef.current.children) as HTMLElement[];
    gsap.set(cards, { opacity: 0, y: 20 });
    gsap.to(cards, {
      opacity: 1,
      y: 0,
      duration: 0.5,
      stagger: 0.1,
      ease: "power2.out",
      delay: 0.3,
    });
  }, [filteredExamples]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "w-full max-w-2xl mx-auto space-y-6 transition-all duration-500",
        className,
      )}
    >
      {/* Animated Hero Icon */}
      <div className="flex justify-center">
        <div className="relative">
          {/* Pulsing background glow */}
          <div className="absolute inset-0 bg-gradient-to-r from-brand-500/20 to-brand-600/20 rounded-full blur-2xl animate-pulse-glow" />

          {/* Main icon container */}
          <div className="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-500/10 to-brand-600/5 border border-brand-500/20 flex items-center justify-center shadow-lg shadow-brand-500/10">
            <Sparkles className="h-10 w-10 text-brand-500 animate-pulse" />
          </div>

          {/* Floating particles */}
          <div
            className="absolute -top-2 -right-2 w-3 h-3 rounded-full bg-brand-400 animate-bounce opacity-70"
            style={{ animationDelay: "0ms", animationDuration: "2s" }}
          />
          <div
            className="absolute -bottom-1 -left-2 w-2 h-2 rounded-full bg-brand-500 animate-bounce opacity-60"
            style={{ animationDelay: "300ms", animationDuration: "2.5s" }}
          />
          <div
            className="absolute top-3 -right-3 w-2 h-2 rounded-full bg-brand-300 animate-bounce opacity-50"
            style={{ animationDelay: "600ms", animationDuration: "3s" }}
          />
        </div>
      </div>

      {/* Compact Header */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-text-primary bg-gradient-to-r from-text-primary to-brand-500 bg-clip-text">
          {t(
            "emptyState.whatWouldYouLikeToBuild",
            "What would you like to build?",
          )}
        </h2>
        <p className="text-text-secondary text-sm max-w-lg mx-auto">
          {t(
            "emptyState.chooseSuggestionOrType",
            "Choose a suggestion below or type your own message to get started",
          )}
        </p>
      </div>

      {/* Simplified Category Filter - Just show popular */}
      <div className="flex items-center justify-center gap-2 py-2">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20">
          <Sparkles className="h-3.5 w-3.5 text-brand-500" />
          <span className="text-xs font-medium text-brand-500">
            {t("emptyState.popularTasks", "Popular Tasks")}
          </span>
        </div>
      </div>

      {/* Enhanced Examples - Only show 3 popular ones */}
      <div ref={examplesRef} className="grid grid-cols-1 gap-3">
        {filteredExamples.slice(0, 3).map((example) => (
          <Button
            key={example.id}
            variant="ghost"
            onClick={() => onSelectExample(example.prompt)}
            className={cn(
              "w-full justify-start h-auto py-3 px-4 text-left group relative overflow-hidden",
              "bg-gradient-to-br from-black to-brand-500/5 border border-brand-500/20",
              "hover:border-brand-500/40 hover:from-brand-500/5 hover:to-brand-500/10",
              "transition-all duration-300 hover:shadow-lg hover:shadow-brand-500/10",
              "hover:scale-[1.01] active:scale-[0.99]",
            )}
          >
            {/* Subtle gradient overlay on hover */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-brand-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            <div className="flex items-center gap-3 w-full relative z-10">
              {/* Icon with glow effect */}
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-500 group-hover:bg-brand-500/20 group-hover:border-brand-500/30 transition-all duration-300 group-hover:shadow-md group-hover:shadow-brand-500/20">
                {example.icon}
              </div>

              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-text-primary group-hover:text-brand-400 transition-colors duration-300 mb-0.5">
                  {example.title}
                </div>
                <div className="text-xs text-text-secondary group-hover:text-text-primary/80 transition-colors duration-300 line-clamp-1">
                  {example.description}
                </div>
              </div>

              {/* Arrow indicator */}
              <div className="flex-shrink-0 text-brand-500/0 group-hover:text-brand-500/100 transition-all duration-300 group-hover:translate-x-1">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </div>
          </Button>
        ))}
      </div>

      {/* Enhanced Footer Hint */}
      <div className="text-center pt-3 space-y-2">
        <p className="text-sm text-text-secondary font-medium">
          {t(
            "emptyState.iCanHelpYou",
            "I can help you code, debug, refactor, and learn",
          )}
        </p>
        <div className="flex items-center justify-center gap-2 text-xs text-text-tertiary">
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
            <span>{t("emptyState.alwaysAvailable", "Always available")}</span>
          </div>
          <span>•</span>
          <div className="flex items-center gap-1">
            <Zap className="h-3 w-3 text-brand-500" />
            <span>{t("emptyState.instantResponses", "Instant responses")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
