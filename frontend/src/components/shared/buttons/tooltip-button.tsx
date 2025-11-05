import { Tooltip, TooltipProps } from "@heroui/react";
import React, { ReactNode, useRef } from "react";
import { NavLink } from "react-router-dom";
import { cn } from "#/utils/utils";

export interface TooltipButtonProps {
  children: ReactNode;
  tooltip: string;
  onClick?: () => void;
  href?: string;
  navLinkTo?: string;
  ariaLabel: string;
  testId?: string;
  className?: React.HTMLAttributes<HTMLButtonElement>["className"];
  tooltipClassName?: React.HTMLAttributes<HTMLDivElement>["className"];
  disabled?: boolean;
  placement?: TooltipProps["placement"];
}

export function TooltipButton({
  children,
  tooltip,
  onClick,
  href,
  navLinkTo,
  ariaLabel,
  testId,
  className,
  tooltipClassName,
  disabled = false,
  placement,
}: TooltipButtonProps) {
  const wrapperRef = useRef<HTMLButtonElement | null>(null);
  const handleClick = () => {
    if (disabled) {
      return;
    }
    if (onClick) {
      onClick();
    }
  };

  let content: React.ReactNode;

  const focusClasses =
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500 focus-visible:ring-offset-neutral-900";

  if (navLinkTo && !disabled) {
    content = (
      <NavLink
        to={navLinkTo}
        onClick={handleClick}
        className={({ isActive }) =>
          cn(
            "hover:opacity-80 flex items-center justify-center",
            focusClasses,
            isActive ? "text-white" : "text-text-foreground-secondary",
            className,
          )
        }
        aria-label={ariaLabel}
        data-testid={testId}
      >
        {children}
      </NavLink>
    );
  } else if (navLinkTo && disabled) {
    // render a non-button fallback when disabled
    content = (
      <span
        role="button"
        aria-label={ariaLabel}
        data-testid={testId}
        className={cn(
          "text-text-foreground-secondary flex items-center justify-center opacity-50 cursor-not-allowed",
          className,
        )}
        aria-disabled="true"
      >
        {children}
      </span>
    );
  } else if (href && !disabled) {
    content = (
      <a
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        onClick={handleClick}
        className={cn(
          "hover:opacity-80 flex items-center justify-center",
          focusClasses,
          className,
        )}
        aria-label={ariaLabel}
        data-testid={testId}
      >
        {children}
      </a>
    );
  } else if (href && disabled) {
    content = (
      <span
        role="button"
        aria-label={ariaLabel}
        data-testid={testId}
        className={cn(
          "opacity-50 cursor-not-allowed flex items-center justify-center",
          className,
        )}
        aria-disabled="true"
      >
        {children}
      </span>
    );
  } else {
    // render a non-button interactive element to avoid nested <button> inside other buttons
    // keep it accessible via role and keyboard handlers
    content = (
      <span
        ref={wrapperRef as unknown as React.RefObject<HTMLSpanElement>}
        role="button"
        tabIndex={disabled ? -1 : 0}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === "" || e.key === "Enter") onClick?.();
        }}
        aria-label={ariaLabel}
        data-testid={testId}
        className={cn(
          "hover:opacity-80 flex items-center justify-center text-text-foreground-secondary",
          focusClasses,
          className,
        )}
        aria-disabled={disabled}
      >
        {children}
      </span>
    );
  }

  return (
    <Tooltip
      content={tooltip}
      closeDelay={100}
      placement={placement}
      className={cn(
        "bg-background-secondary text-white border border-border shadow-xl",
        tooltipClassName,
      )}
    >
      <span className="inline-block">{content}</span>
    </Tooltip>
  );
}
