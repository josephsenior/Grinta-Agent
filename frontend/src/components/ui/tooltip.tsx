import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "#/utils/utils";

export type TooltipPlacement =
  | "top"
  | "bottom"
  | "left"
  | "right"
  | "top-start"
  | "top-end"
  | "bottom-start"
  | "bottom-end";

function mapPlacement(placement?: TooltipPlacement) {
  if (!placement) return { side: "top" as const, align: "center" as const };
  const [side, align] = placement.split("-") as [
    "top" | "bottom" | "left" | "right",
    "start" | "end" | undefined,
  ];
  return {
    side,
    align: (align ?? "center") as "start" | "end" | "center",
  };
}

interface TooltipProps {
  /** The content displayed in the tooltip popup. */
  content: React.ReactNode;
  /** The trigger element. Must accept a ref. */
  children: React.ReactNode;
  /** Where to place the tooltip relative to the trigger. */
  placement?: TooltipPlacement;
  /** Delay in ms before hiding after pointer leaves. */
  closeDelay?: number;
  /** Delay in ms before showing after pointer enters. */
  openDelay?: number;
  /** Slot‑based class overrides for base (content) and content (inner text). */
  classNames?: {
    base?: string;
    content?: string;
  };
}

export function Tooltip({
  content,
  children,
  placement,
  closeDelay = 100,
  openDelay = 200,
  classNames,
}: TooltipProps) {
  const { side, align } = mapPlacement(placement);

  return (
    <TooltipPrimitive.Provider delayDuration={openDelay}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>
          {/* Wrap non-element children in a span so Radix can attach its ref */}
          {React.isValidElement(children) ? (
            children
          ) : (
            <span className="inline-block">{children}</span>
          )}
        </TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side={side}
            align={align}
            sideOffset={6}
            className={cn(
              "z-[9999] rounded-md bg-black/90 border border-neutral-800 px-3 py-2 text-xs text-white shadow-xl animate-in fade-in-0 zoom-in-95",
              classNames?.base,
            )}
          >
            <span className={classNames?.content}>{content}</span>
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

export type { TooltipProps };
