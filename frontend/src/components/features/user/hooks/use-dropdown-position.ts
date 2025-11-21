import { useState, useEffect, RefObject } from "react";

interface DropdownPosition {
  top: number;
  right: number;
}

export function useDropdownPosition(
  isOpen: boolean,
  buttonRef: RefObject<HTMLButtonElement | null>,
): DropdownPosition | null {
  const [dropdownPosition, setDropdownPosition] =
    useState<DropdownPosition | null>(null);

  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right,
      });
    } else {
      setDropdownPosition(null);
    }
  }, [isOpen, buttonRef]);

  return dropdownPosition;
}
