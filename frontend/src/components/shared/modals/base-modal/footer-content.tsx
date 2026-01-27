import { Button } from "@heroui/react";
import React from "react";

export interface Action {
  action: () => void;
  isDisabled?: boolean;
  label: string;
  className?: string;
  closeAfterAction?: boolean;
  variant?: "primary" | "secondary" | "danger";
}

interface FooterContentProps {
  actions: Action[];
  closeModal: () => void;
}

export function FooterContent({ actions, closeModal }: FooterContentProps) {
  const getButtonClasses = (variant: Action["variant"] = "secondary") => {
    const baseClasses =
      "transition-all duration-300 ease-in-out rounded-xl px-6 py-2.5 font-medium";

    switch (variant) {
      case "primary":
        return `${baseClasses} bg-brand-500 hover:bg-brand-500/90 text-white border border-brand-500/30 hover:border-brand-500/50 active:scale-[0.98]`;
      case "danger":
        return `${baseClasses} bg-danger-400 hover:bg-danger-400/90 text-white border border-danger-400/30 hover:border-danger-400/50 active:scale-[0.98]`;
      default:
        return `${baseClasses} bg-background-tertiary hover:bg-background-secondary text-foreground-secondary border border-border hover:border-border active:scale-[0.98]`;
    }
  };

  return (
    <div className="flex gap-3 justify-end">
      {actions.map(
        ({
          action,
          isDisabled,
          label,
          className,
          closeAfterAction,
          variant,
        }) => (
          <Button
            key={label}
            type="button"
            isDisabled={isDisabled}
            onPress={() => {
              action();
              if (closeAfterAction) {
                closeModal();
              }
            }}
            className={className || getButtonClasses(variant)}
          >
            {label}
          </Button>
        ),
      )}
    </div>
  );
}
