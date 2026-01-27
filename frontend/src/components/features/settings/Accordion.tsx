import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "#/utils/utils";

interface AccordionProps {
  title: string;
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

export function Accordion({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
  className,
}: AccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "border border-[var(--border-primary)] rounded-xl overflow-hidden",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-[var(--bg-elevated)] hover:bg-[var(--bg-tertiary)] transition-colors duration-200"
      >
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-8 h-8 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center">
              <Icon className="w-4 h-4 text-[var(--text-accent)]" />
            </div>
          )}
          <h3 className="text-base font-semibold text-[var(--text-primary)]">
            {title}
          </h3>
        </div>
        <ChevronDown
          className={cn(
            "w-5 h-5 text-[var(--text-tertiary)] transition-transform duration-200",
            isOpen && "rotate-180",
          )}
        />
      </button>
      {isOpen && (
        <div className="p-4 bg-[var(--bg-secondary)] border-t border-[var(--border-primary)] space-y-4">
          {children}
        </div>
      )}
    </div>
  );
}
