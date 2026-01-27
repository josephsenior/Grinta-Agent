import React from "react";
import { cn } from "#/utils/utils";

type ModalWidth = "small" | "medium";

interface ModalBodyProps {
  testID?: string;
  children: React.ReactNode;
  className?: React.HTMLProps<HTMLDivElement>["className"];
  width?: ModalWidth;
}

export function ModalBody({
  testID,
  children,
  className,
  width = "small",
}: ModalBodyProps) {
  return (
    <div
      data-testid={testID}
      role="dialog"
      aria-modal="true"
      className={cn(
        "bg-background-secondary flex flex-col gap-6 items-start p-8 rounded-lg border border-border",
        "shadow-lg transform transition-all duration-150",
        width === "small" && "w-[94vw] max-w-[560px]",
        width === "medium" && "w-[94vw] max-w-[900px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
