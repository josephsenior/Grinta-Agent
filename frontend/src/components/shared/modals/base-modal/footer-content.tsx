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
        return `${baseClasses} bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-400 hover:to-primary-500 text-white border border-primary-400/30 hover:border-primary-300/50 shadow-lg hover:shadow-xl shadow-primary-500/25 hover:shadow-primary-500/40 active:scale-[0.98]`;
      case "danger":
        return `${baseClasses} bg-gradient-to-r from-danger-500 to-danger-600 hover:from-danger-400 hover:to-danger-500 text-white border border-danger-400/30 hover:border-danger-300/50 shadow-lg hover:shadow-xl shadow-danger-500/25 hover:shadow-danger-500/40 active:scale-[0.98]`;
      default:
        return `${baseClasses} bg-gradient-to-br from-grey-700/80 to-grey-800/90 hover:from-grey-600/90 hover:to-grey-700/95 text-foreground border border-grey-600/40 hover:border-grey-500/60 backdrop-blur-sm active:scale-[0.98]`;
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
