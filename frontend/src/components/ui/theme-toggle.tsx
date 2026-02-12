import React from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  useTheme,
  type Theme,
  type ResolvedTheme,
} from "#/context/theme-context";

interface ThemeToggleProps {
  variant?: "icon" | "button" | "dropdown";
  className?: string;
}

function ThemeToggleIcon({
  className,
  resolvedTheme,
  toggleTheme,
  theme,
}: {
  className: string;
  resolvedTheme: ResolvedTheme;
  toggleTheme: () => void;
  theme: Theme;
}) {
  const isLight = resolvedTheme === "light";
  const sunOpacity = isLight ? 1 : 0;
  const sunTransform = isLight
    ? "rotate(0deg) scale(1)"
    : "rotate(90deg) scale(0.5)";
  const moonOpacity = resolvedTheme === "dark" ? 1 : 0;
  const moonTransform =
    resolvedTheme === "dark"
      ? "rotate(0deg) scale(1)"
      : "rotate(-90deg) scale(0.5)";

  return (
    <button
      type="button"
      onClick={() => {
        toggleTheme();
        return undefined;
      }}
      className={`group relative p-2 rounded-lg transition-all duration-200 text-[var(--text-secondary)] ${className}`}
      onMouseEnter={(e) => {
        const target = e.currentTarget;
        target.style.color = "var(--text-primary)";
        target.style.backgroundColor = "var(--bg-tertiary)";
        return undefined;
      }}
      onMouseLeave={(e) => {
        const target = e.currentTarget;
        target.style.color = "var(--text-secondary)";
        target.style.backgroundColor = "transparent";
        return undefined;
      }}
      title={`Current: ${theme} (${resolvedTheme}). Click to toggle`}
      aria-label="Toggle theme"
    >
      <div className="relative w-5 h-5">
        <Sun
          className="absolute inset-0 w-5 h-5 transition-all duration-300 text-[#F59E0B]"
          style={{
            opacity: sunOpacity,
            transform: sunTransform,
          }}
        />
        <Moon
          className="absolute inset-0 w-5 h-5 transition-all duration-300 text-[var(--text-primary)]"
          style={{
            opacity: moonOpacity,
            transform: moonTransform,
          }}
        />
      </div>
    </button>
  );
}

function ThemeToggleButton({
  className,
  resolvedTheme,
  toggleTheme,
}: {
  className: string;
  resolvedTheme: ResolvedTheme;
  toggleTheme: () => void;
}) {
  const { t } = useTranslation();
  const isDark = resolvedTheme === "dark";
  const IconComponent = isDark ? Moon : Sun;
  const iconClassName = isDark
    ? "w-4 h-4 text-text-accent"
    : "w-4 h-4 text-accent-gold";
  const modeText = isDark ? "Dark" : "Light";

  return (
    <button
      type="button"
      onClick={() => {
        toggleTheme();
        return undefined;
      }}
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
      <IconComponent className={iconClassName} />
      <span className="text-sm font-medium">
        {t("UI$MODE", "{{mode}} Mode", { mode: modeText })}
      </span>
    </button>
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
  const baseClasses =
    "flex items-center gap-3 px-3 py-2 rounded-md text-left transition-all duration-150";
  const inactiveClasses =
    "text-text-secondary hover:bg-background-elevated hover:text-text-primary";
  const buttonClassName = isActive
    ? `${baseClasses} ${activeClasses}`
    : `${baseClasses} ${inactiveClasses}`;

  return (
    <button type="button" onClick={onClick} className={buttonClassName}>
      {icon}
      <span className="text-sm font-medium">{label}</span>
      {isActive && <div className="ml-auto w-2 h-2 rounded-full bg-current" />}
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
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}) {
  const { t } = useTranslation();
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
          {t(
            "UI$USING_SYSTEM_PREFERENCE",
            "Using system preference: {{theme}}",
            {
              theme: resolvedTheme,
            },
          )}
        </p>
      )}
    </div>
  );
}

/**
 * Theme toggle component with multiple variants
 */
export function ThemeToggle({
  variant = "icon",
  className = "",
}: ThemeToggleProps) {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();

  const sharedProps = {
    className,
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
  } as const;

  if (variant === "icon") {
    return <ThemeToggleIcon {...sharedProps} />;
  }
  if (variant === "button") {
    return <ThemeToggleButton {...sharedProps} />;
  }
  if (variant === "dropdown") {
    return <ThemeToggleDropdown {...sharedProps} />;
  }
  return null;
}
