import { RefObject } from "react";
import {
  isInputElement,
  isModifierPressed,
  matchesKey,
} from "../../utils/keyboard-utils";

interface HandleOpenSearchParams {
  event: KeyboardEvent;
  openModifier: "ctrl" | "meta" | undefined;
  openKey: string;
  shouldOpen: (event: KeyboardEvent) => boolean;
  setIsOpen: (open: boolean) => void;
  inputRef: RefObject<HTMLInputElement | null>;
}

export function handleOpenSearch({
  event,
  openModifier,
  openKey,
  shouldOpen,
  setIsOpen,
  inputRef,
}: HandleOpenSearchParams): boolean {
  if (
    openModifier &&
    isModifierPressed(event, openModifier) &&
    matchesKey(event, openKey) &&
    shouldOpen(event)
  ) {
    if (isInputElement(event.target)) {
      return false;
    }

    event.preventDefault();
    setIsOpen(true);
    setTimeout(() => inputRef.current?.focus(), 0);
    return true;
  }
  return false;
}

interface HandleEscapeParams {
  event: KeyboardEvent;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  onClose?: () => void;
  inputRef: RefObject<HTMLInputElement | null>;
}

export function handleEscape({
  event,
  isOpen,
  setIsOpen,
  onClose,
  inputRef,
}: HandleEscapeParams): boolean {
  if (event.key === "Escape" && isOpen) {
    event.preventDefault();
    setIsOpen(false);
    onClose?.();
    inputRef.current?.blur();
    return true;
  }
  return false;
}

interface HandleArrowKeysParams {
  event: KeyboardEvent;
  isOpen: boolean;
  results: unknown[];
  selectedIndex: number;
  setSelectedIndex: (index: number | ((prev: number) => number)) => void;
}

export function handleArrowKeys({
  event,
  isOpen,
  results,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  selectedIndex: _selectedIndex,
  setSelectedIndex,
}: HandleArrowKeysParams): boolean {
  if (!isOpen) {
    return false;
  }

  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    setSelectedIndex((prev) => {
      if (event.key === "ArrowDown") {
        return prev < results.length - 1 ? prev + 1 : 0;
      }
      return prev > 0 ? prev - 1 : results.length - 1;
    });
    return true;
  }
  return false;
}

interface HandleEnterParams {
  event: KeyboardEvent;
  isOpen: boolean;
  results: unknown[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export function handleEnter({
  event,
  isOpen,
  results,
  selectedIndex,
  onSelect,
}: HandleEnterParams): boolean {
  if (!isOpen) {
    return false;
  }

  if (event.key === "Enter" && results[selectedIndex]) {
    event.preventDefault();
    onSelect(selectedIndex);
    return true;
  }
  return false;
}
