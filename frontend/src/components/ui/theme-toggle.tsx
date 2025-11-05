import React from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "#/context/theme-context";

interface ThemeToggleProps {
  variant?: "icon" | "button" | "dropdown";
  className?: string;
}

/**
 * Theme toggle component with multiple variants
 */
export function ThemeToggle({ variant = "icon", className = "" }: ThemeToggleProps) {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();

  if (variant === "icon") {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        className={`
          group relative p-2 rounded-lg
          bg-background-surface hover:bg-background-elevated
          border border-border-secondary hover:border-accent-gold/30
          transition-all duration-200
          ${className}
        `}
        title={`Current: ${theme} (${resolvedTheme}). Click to toggle`}
        aria-label="Toggle theme"
      >
        {/* Icon with smooth transition */}
        <div className="relative w-5 h-5">
          <Sun
            className={`
              absolute inset-0 w-5 h-5 text-accent-gold
              transition-all duration-300
              ${resolvedTheme === "light" ? "opacity-100 rotate-0 scale-100" : "opacity-0 rotate-90 scale-50"}
            `}
          />
          <Moon
            className={`
              absolute inset-0 w-5 h-5 text-text-accent
              transition-all duration-300
              ${resolvedTheme === "dark" ? "opacity-100 rotate-0 scale-100" : "opacity-0 -rotate-90 scale-50"}
            `}
          />
        </div>

        {/* Glow effect on hover */}
        <div
          className="
            absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100
            transition-opacity duration-200
            bg-gradient-to-r from-accent-gold/5 to-text-accent/5
          "
        />
      </button>
    );
  }

  if (variant === "button") {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        className={`
          group flex items-center gap-2 px-4 py-2 rounded-lg
          bg-background-surface hover:bg-background-elevated
          border border-border-secondary hover:border-accent-gold/30
          text-text-secondary hover:text-text-primary
          transition-all duration-200
          ${className}
        `}
        aria-label="Toggle theme"
      >
        {resolvedTheme === "dark" ? (
          <Moon className="w-4 h-4 text-text-accent" />
        ) : (
          <Sun className="w-4 h-4 text-accent-gold" />
        )}
        <span className="text-sm font-medium">
          {resolvedTheme === "dark" ? "Dark" : "Light"} Mode
        </span>
      </button>
    );
  }

  if (variant === "dropdown") {
    return (
      <div className={`relative ${className}`}>
        <div className="flex flex-col gap-1 p-1 bg-background-surface border border-border-secondary rounded-lg">
          {/* Light Option */}
          <button
            type="button"
            onClick={() => setTheme("light")}
            className={`
              flex items-center gap-3 px-3 py-2 rounded-md text-left
              transition-all duration-150
              ${
                theme === "light"
                  ? "bg-accent-gold/10 text-accent-gold border border-accent-gold/30"
                  : "text-text-secondary hover:bg-background-elevated hover:text-text-primary"
              }
            `}
          >
            <Sun className="w-4 h-4" />
            <span className="text-sm font-medium">Light</span>
            {theme === "light" && (
              <div className="ml-auto w-2 h-2 bg-accent-gold rounded-full" />
            )}
          </button>

          {/* Dark Option */}
          <button
            type="button"
            onClick={() => setTheme("dark")}
            className={`
              flex items-center gap-3 px-3 py-2 rounded-md text-left
              transition-all duration-150
              ${
                theme === "dark"
                  ? "bg-text-accent/10 text-text-accent border border-text-accent/30"
                  : "text-text-secondary hover:bg-background-elevated hover:text-text-primary"
              }
            `}
          >
            <Moon className="w-4 h-4" />
            <span className="text-sm font-medium">Dark</span>
            {theme === "dark" && (
              <div className="ml-auto w-2 h-2 bg-text-accent rounded-full" />
            )}
          </button>

          {/* System Option */}
          <button
            type="button"
            onClick={() => setTheme("system")}
            className={`
              flex items-center gap-3 px-3 py-2 rounded-md text-left
              transition-all duration-150
              ${
                theme === "system"
                  ? "bg-info/10 text-info border border-info/30"
                  : "text-text-secondary hover:bg-background-elevated hover:text-text-primary"
              }
            `}
          >
            <Monitor className="w-4 h-4" />
            <span className="text-sm font-medium">System</span>
            {theme === "system" && (
              <div className="ml-auto w-2 h-2 bg-info rounded-full" />
            )}
          </button>
        </div>

        {/* Helper text */}
        {theme === "system" && (
          <p className="mt-2 px-3 text-xs text-text-muted">
            Using system preference: {resolvedTheme}
          </p>
        )}
      </div>
    );
  }

  return null;
}

