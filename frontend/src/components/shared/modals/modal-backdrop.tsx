import React from "react";

interface ModalBackdropProps {
  children: React.ReactNode;
  /** optional handler to close the modal; when absent Escape/backdrop won't close */
  onClose?: () => void;
  /** optional ref to focus initially inside the modal */
  initialFocusRef?: React.RefObject<HTMLElement>;
  /** optional aria-label for the dialog */
  "aria-label"?: string;
}

function getFocusableElements(container: HTMLElement | null): HTMLElement[] {
  if (!container) {
    return [];
  }
  const selector =
    'a[href], area[href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
  return Array.from(container.querySelectorAll<HTMLElement>(selector)).filter(
    (el) => {
      const style = window.getComputedStyle(el);
      return style && style.display !== "none" && style.visibility !== "hidden";
    },
  );
}

export function ModalBackdrop({
  children,
  onClose,
  initialFocusRef,
  "aria-label": ariaLabel,
}: ModalBackdropProps) {
  const backdropRef = React.useRef<HTMLDivElement | null>(null);
  const contentRef = React.useRef<HTMLDivElement | null>(null);
  const previouslyFocusedRef = React.useRef<HTMLElement | null>(null);

  // Manage initial focus and restore previous focus on unmount
  React.useEffect(() => {
    previouslyFocusedRef.current =
      (document.activeElement as HTMLElement) || null;

    const tryFocus = (el?: HTMLElement | null) => {
      try {
        el?.focus?.();
      } catch {
        // ignore
      }
    };

    if (initialFocusRef?.current) {
      tryFocus(initialFocusRef.current);
    } else {
      const focusables = getFocusableElements(contentRef.current);
      if (focusables.length) {
        tryFocus(focusables[0]);
      } else if (contentRef.current) {
        // fallback: make the content wrapper focusable
        contentRef.current.tabIndex = -1;
        tryFocus(contentRef.current);
      }
    }

    return () => {
      try {
        previouslyFocusedRef.current?.focus?.();
      } catch {
        // ignore
      }
    };
    // run only on mount/unmount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Key handling: Escape -> close (only if onClose provided); Tab -> focus trap
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (onClose) {
          e.preventDefault();
          e.stopPropagation();
          onClose();
        }
        return;
      }

      if (e.key === "Tab") {
        const modal = contentRef.current;
        if (!modal) {
          return;
        }

        const focusable = getFocusableElements(modal);
        if (focusable.length === 0) {
          e.preventDefault();
          (modal as HTMLElement).focus();
          return;
        }

        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = document.activeElement as HTMLElement | null;

        if (e.shiftKey) {
          if (active === first || active === modal) {
            e.preventDefault();
            last.focus();
          }
        } else if (active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown, { capture: true });
    return () => {
      document.removeEventListener("keydown", handleKeyDown, { capture: true });
    };
  }, [onClose]);

  // Backdrop click: close only if click happened on the backdrop element itself
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === backdropRef.current) {
      onClose?.();
    }
  };

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 flex items-center justify-center z-20"
      onMouseDown={handleMouseDown}
      aria-hidden={false}
    >
      <div
        aria-hidden="true"
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
      />

      <div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        tabIndex={-1}
        className="relative"
      >
        {children}
      </div>
    </div>
  );
}
