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

  const sharedProps = {
    className,
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
  } as const;

  switch (variant) {
    case "icon":
      return <ThemeToggleIcon {...sharedProps} />;
    case "button":
      return <ThemeToggleButton {...sharedProps} />;
    case "dropdown":
      return <ThemeToggleDropdown {...sharedProps} />;
    default:
      return null;
  }
}

function ThemeToggleIcon({
  className,
  resolvedTheme,
  toggleTheme,
  theme,
}: {
  className: string;
  resolvedTheme: string;
  toggleTheme: () => void;
  theme: string;
}) {
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

function ThemeToggleButton({
  className,
  resolvedTheme,
  toggleTheme,
}: {
  className: string;
  resolvedTheme: string;
  toggleTheme: () => void;
}) {
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

function ThemeToggleDropdown({
  className,
  theme,
  resolvedTheme,
  setTheme,
}: {
  className: string;
  theme: string;
  resolvedTheme: string;
  setTheme: (theme: string) => void;
}) {
  return (
    <div className={`relative ${className}`}>
      <div className="flex flex-col gap-1 p-1 bg-background-surface border border-border-secondary rounded-lg">
        <ThemeDropdownOption
          label="Light"
          icon={<Sun className="w-4 h-4" />}
          isActive={theme === "light"}
          onClick={() => setTheme("light")}
          activeClasses="bg-accent-gold/10 text-accent-gold border border-accent-gold/30"
        />

        <ThemeDropdownOption
          label="Dark"
          icon={<Moon className="w-4 h-4" />}
          isActive={theme === "dark"}
          onClick={() => setTheme("dark")}
          activeClasses="bg-text-accent/10 text-text-accent border border-text-accent/30"
        />

        <ThemeDropdownOption
          label="System"
          icon={<Monitor className="w-4 h-4" />}
          isActive={theme === "system"}
          onClick={() => setTheme("system")}
          activeClasses="bg-info/10 text-info border border-info/30"
        />
      </div>

      {theme === "system" && (
        <p className="mt-2 px-3 text-xs text-text-muted">
          Using system preference: {resolvedTheme}
        </p>
      )}
    </div>
  );
}

function ThemeDropdownOption({
  label,
  icon,
  isActive,
  onClick,
  activeClasses,
}: {
  label: string;
  icon: React.ReactNode;
  isActive: boolean;
  onClick: () => void;
  activeClasses: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
              flex items-center gap-3 px-3 py-2 rounded-md text-left
              transition-all duration-150
              ${
                isActive
                  ? activeClasses
                  : "text-text-secondary hover:bg-background-elevated hover:text-text-primary"
              }
            `}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
      {isActive && <div className="ml-auto w-2 h-2 rounded-full bg-current" />}
    </button>
  );
}

