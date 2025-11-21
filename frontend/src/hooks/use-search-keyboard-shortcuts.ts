import { useEffect, RefObject } from "react";
import {
  handleOpenSearch,
  handleEscape,
  handleArrowKeys,
  handleEnter,
} from "./use-search-keyboard-shortcuts/handlers/key-handlers";

interface UseSearchKeyboardShortcutsOptions {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  inputRef: RefObject<HTMLInputElement | null>;
  selectedIndex: number;
  setSelectedIndex: (index: number | ((prev: number) => number)) => void;
  results: unknown[];
  onSelect: (index: number) => void;
  onClose?: () => void;
  openKey?: string;
  openModifier?: "ctrl" | "meta";
  shouldOpen?: (event: KeyboardEvent) => boolean;
  variant?: "button" | "inline";
}

export function useSearchKeyboardShortcuts({
  isOpen,
  setIsOpen,
  inputRef,
  selectedIndex,
  setSelectedIndex,
  results,
  onSelect,
  onClose,
  openKey = "k",
  openModifier = "meta",
  shouldOpen = () => true,
  variant: _variant = "inline", // eslint-disable-line @typescript-eslint/no-unused-vars
}: UseSearchKeyboardShortcutsOptions) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        handleOpenSearch({
          event,
          openModifier,
          openKey,
          shouldOpen,
          setIsOpen,
          inputRef,
        })
      ) {
        return;
      }

      if (
        handleEscape({
          event,
          isOpen,
          setIsOpen,
          onClose,
          inputRef,
        })
      ) {
        return;
      }

      if (
        handleArrowKeys({
          event,
          isOpen,
          results,
          selectedIndex,
          setSelectedIndex,
        })
      ) {
        return;
      }

      handleEnter({
        event,
        isOpen,
        results,
        selectedIndex,
        onSelect,
      });
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [
    isOpen,
    results,
    selectedIndex,
    openKey,
    openModifier,
    setIsOpen,
    setSelectedIndex,
    onSelect,
    onClose,
    inputRef,
    shouldOpen,
  ]);
}
