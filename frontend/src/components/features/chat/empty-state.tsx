import React, { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
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
        "w-full max-w-[440px] mx-auto space-y-6 transition-all duration-500",
        className,
      )}
    >
      {/* Simple Header */}
      <div className="text-center space-y-4">
        <h2 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] leading-tight">
          {t(
            "emptyState.whatWouldYouLikeToBuild",
            "What would you like to build?",
          )}
        </h2>
        <p className="text-[var(--text-tertiary)] text-sm leading-relaxed">
          {t(
            "emptyState.chooseSuggestionOrType",
            "Choose a suggestion below or type your own message to get started",
          )}
        </p>
      </div>

      {/* Examples - Desktop style */}
      <div ref={examplesRef} className="grid grid-cols-1 gap-3">
        {filteredExamples.slice(0, 3).map((example) => (
          <button
            key={example.id}
            type="button"
            onClick={() => onSelectExample(example.prompt)}
            className={cn(
              "w-full text-left px-4 py-3 rounded-lg border transition-all duration-200",
              "bg-[var(--bg-input)] border-[var(--border-primary)] text-[var(--text-primary)]",
              "hover:bg-[var(--bg-elevated)] hover:border-[var(--border-accent)]",
            )}
          >
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)] flex items-center justify-center text-[var(--border-accent)]">
                {example.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[var(--text-primary)] mb-0.5">
                  {example.title}
                </div>
                <div className="text-xs text-[var(--text-tertiary)] line-clamp-1">
                  {example.description}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Footer Hint */}
      <div className="text-center pt-2">
        <p className="text-xs text-[var(--text-tertiary)]">
          {t(
            "emptyState.iCanHelpYou",
            "I can help you code, debug, refactor, and learn",
          )}
        </p>
      </div>
    </div>
  );
}
