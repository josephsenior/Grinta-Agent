import React from "react";
import { useTranslation } from "react-i18next";
import { Settings, Zap, Shield, Eye } from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";

export type AutonomyMode = "supervised" | "balanced" | "full";

interface AutonomyModeSelectorProps {
  currentMode: AutonomyMode;
  onModeChange: (mode: AutonomyMode) => void;
  className?: string;
}

const MODE_CONFIG = {
  supervised: {
    icon: Shield,
    label: "Supervised",
    description: "Always confirm actions",
    color: "text-orange-500",
    bgColor: "bg-orange-500/10",
    borderColor: "border-orange-500/20",
  },
  balanced: {
    icon: Eye,
    label: "Balanced",
    description: "Confirm high-risk actions",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/20",
  },
  full: {
    icon: Zap,
    label: "Full Autonomous",
    description: "Execute without confirmation",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
    borderColor: "border-green-500/20",
  },
} as const;

/**
 * Autonomy mode selector component
 * Allows users to switch between different autonomy levels
 * Keyboard shortcut: Ctrl+Shift+A to cycle through modes
 */
export function AutonomyModeSelector({
  currentMode,
  onModeChange,
  className,
}: AutonomyModeSelectorProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = React.useState(false);
  const [dropdownPosition, setDropdownPosition] = React.useState<
    "above" | "below"
  >("above");
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  const currentConfig = MODE_CONFIG[currentMode];
  const CurrentIcon = currentConfig.icon;

  const cycleMode = React.useCallback(() => {
    const modes: AutonomyMode[] = ["supervised", "balanced", "full"];
    const currentIndex = modes.indexOf(currentMode);
    const nextIndex = (currentIndex + 1) % modes.length;
    onModeChange(modes[nextIndex]);
  }, [currentMode, onModeChange]);

  // Keyboard shortcut: Ctrl+Shift+A to cycle through modes
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "A") {
        e.preventDefault();
        cycleMode();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [cycleMode]);

  // Click outside to close dropdown
  React.useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    // Delay to let current click event finish
    setTimeout(() => {
      document.addEventListener("click", handleClickOutside);
    }, 0);

    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, [isOpen]);

  const handleModeSelect = (mode: AutonomyMode) => {
    onModeChange(mode);
    setIsOpen(false);
  };

  // Smart positioning - check if there's enough space above
  const handleToggle = () => {
    if (!isOpen) {
      const buttonRect = document
        .querySelector('[data-testid="autonomy-mode-button"]')
        ?.getBoundingClientRect();
      if (buttonRect) {
        const spaceAbove = buttonRect.top;
        const spaceBelow = window.innerHeight - buttonRect.bottom;
        setDropdownPosition(spaceAbove > 200 ? "above" : "below");
      }
    }
    setIsOpen(!isOpen);
  };

  return (
    <div className={cn("relative", className)}>
      {/* Mode Button - More Prominent */}
      <Button
        variant="ghost"
        size="sm"
        onClick={(e) => {
          e.stopPropagation();
          handleToggle();
        }}
        data-testid="autonomy-mode-button"
        title={`Current mode: ${currentConfig.label} (${currentConfig.description})\nPress Ctrl+Shift+A to cycle`}
        className={cn(
          "h-9 px-4 gap-2.5 transition-all duration-200",
          "hover:bg-background-secondary border-2",
          currentConfig.bgColor,
          currentConfig.borderColor,
          "hover:border-current hover:shadow-lg hover:shadow-current/20",
          "group relative",
        )}
      >
        {/* Pulsing indicator */}
        <div
          className={cn(
            "absolute -top-1 -right-1 w-2 h-2 rounded-full animate-pulse",
            currentMode === "full"
              ? "bg-green-500"
              : currentMode === "supervised"
                ? "bg-orange-500"
                : "bg-blue-500",
          )}
        />

        <CurrentIcon className={cn("w-4 h-4", currentConfig.color)} />
        <span className={cn("text-sm font-semibold", currentConfig.color)}>
          {currentConfig.label}
        </span>

        {/* Keyboard hint */}
        <span className="hidden group-hover:inline-flex items-center gap-1 ml-1 text-[10px] text-text-tertiary">
          <kbd className="px-1 py-0.5 bg-background-tertiary rounded text-[9px]">
            ⌃⇧A
          </kbd>
        </span>
      </Button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className={cn(
            "absolute left-0 z-[10000] min-w-[200px]",
            dropdownPosition === "above" ? "bottom-full mb-1" : "top-full mt-1",
          )}
        >
          <div className="bg-background-secondary border border-border rounded-lg shadow-xl p-1">
            <div className="px-3 py-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-text-secondary" />
                <span className="text-xs font-medium text-text-secondary">
                  Autonomy Mode
                </span>
              </div>
            </div>

            {Object.entries(MODE_CONFIG).map(([mode, config]) => {
              const Icon = config.icon;
              const isSelected = mode === currentMode;

              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => handleModeSelect(mode as AutonomyMode)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-all duration-200",
                    "hover:bg-background-tertiary hover:shadow-md cursor-pointer",
                    isSelected &&
                      "bg-background-tertiary ring-1 ring-brand-500/50",
                  )}
                >
                  <Icon className={cn("w-4 h-4", config.color)} />
                  <div className="flex-1 min-w-0">
                    <div className={cn("text-xs font-medium", config.color)}>
                      {config.label}
                    </div>
                    <div className="text-[10px] text-text-tertiary">
                      {config.description}
                    </div>
                  </div>
                  {isSelected && (
                    <div className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
