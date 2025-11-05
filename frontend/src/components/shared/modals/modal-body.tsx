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
        "bg-[#0b0d0f] flex flex-col gap-6 items-start p-8 rounded-[20px] border border-[rgba(255,255,255,0.04)]",
        "backdrop-blur-sm shadow-[0_18px_50px_rgba(0,0,0,0.65)] transform transition-all duration-150",
        width === "small" && "w-[94vw] max-w-[560px]",
        width === "medium" && "w-[94vw] max-w-[900px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
