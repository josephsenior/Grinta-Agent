import React, { useState, useRef, useEffect, useCallback } from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "#/utils/utils";

export interface DropdownItem {
  key: string;
  label: string;
  disabled?: boolean;
}

export interface DropdownSection {
  title: string;
  items: DropdownItem[];
}

interface CustomDropdownProps {
  items: DropdownItem[] | DropdownSection[];
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  inputClassName?: string;
  onSelectionChange?: (key: string) => void;
  onInputChange?: (value: string) => void;
  isClearable?: boolean;
  // Allow a free-form custom value to be entered and reported back
  allowsCustomValue?: boolean;
  onCustomValue?: (value: string) => void;
  "data-testid"?: string;
  "aria-label"?: string;
  isLoading?: boolean;
  loadingText?: string;
  error?: string;
  name?: string;
}

function isFlatItemList(
  list: DropdownItem[] | DropdownSection[],
): list is DropdownItem[] {
  return Array.isArray(list) && list.length > 0 && "key" in list[0];
}

function findItemLabel(
  list: DropdownItem[] | DropdownSection[],
  key: string,
): string {
  if (isFlatItemList(list)) {
    return list.find((item) => item.key === key)?.label ?? "";
  }

  for (const section of list) {
    const match = section.items.find((item) => item.key === key);
    if (match) {
      return match.label;
    }
  }

  return "";
}

function filterItemsByQuery(
  list: DropdownItem[] | DropdownSection[],
  query: string,
): DropdownItem[] | DropdownSection[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return list;
  }

  if (isFlatItemList(list)) {
    return list.filter((item) =>
      item.label.toLowerCase().includes(normalized),
    );
  }

  const sections = list as DropdownSection[];

  return sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) =>
        item.label.toLowerCase().includes(normalized),
      ),
    }))
    .filter((section) => section.items.length > 0);
}

interface CustomDropdownControllerParams {
  items: DropdownItem[] | DropdownSection[];
  value?: string;
  defaultValue?: string;
  onSelectionChange?: (key: string) => void;
  onInputChange?: (value: string) => void;
  disabled: boolean;
  isLoading: boolean;
}

interface CustomDropdownController {
  dropdownRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLInputElement | null>;
  isOpen: boolean;
  toggleDropdown: () => void;
  closeDropdown: () => void;
  inputValue: string;
  handleInputChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleInputFocus: () => void;
  filteredItems: DropdownItem[] | DropdownSection[];
  selectedKey: string;
  handleItemSelect: (item: DropdownItem) => void;
  clearSelection: () => void;
}

function useCustomDropdownController({
  items,
  value,
  defaultValue,
  onSelectionChange,
  onInputChange,
  disabled,
  isLoading,
}: CustomDropdownControllerParams): CustomDropdownController {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const initialKey = value ?? defaultValue ?? "";
  const [inputValue, setInputValue] = useState(() => findItemLabel(items, initialKey));
  const [filteredItems, setFilteredItems] = useState(items);
  const [selectedKey, setSelectedKey] = useState(initialKey);
  const [isUserTyping, setIsUserTyping] = useState(false);

  const openDropdown = useCallback(() => setIsOpen(true), []);
  const closeDropdown = useCallback(() => setIsOpen(false), []);
  const toggleDropdown = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  useEffect(() => {
    const hasControlledValue = value !== undefined || defaultValue !== undefined;
    if (!hasControlledValue) {
      return;
    }

    const externalKey = value ?? defaultValue ?? "";
    setInputValue(findItemLabel(items, externalKey));
    setSelectedKey(externalKey);
    setIsUserTyping(false);
  }, [value, defaultValue, items]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        closeDropdown();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [closeDropdown]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeDropdown();
        inputRef.current?.blur();
      }
    }

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, closeDropdown]);

  useEffect(() => {
    if (!isUserTyping) {
      setFilteredItems(items);
      return;
    }

    setFilteredItems(filterItemsByQuery(items, inputValue));
  }, [inputValue, items, isUserTyping]);

  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = event.target.value;
      setInputValue(newValue);
      setIsUserTyping(true);
      onInputChange?.(newValue);
      if (!isOpen && !disabled && !isLoading) {
        openDropdown();
      }
    },
    [onInputChange, isOpen, disabled, isLoading, openDropdown],
  );

  const handleInputFocus = useCallback(() => {
    if (!disabled && !isLoading) {
      openDropdown();
    }
  }, [disabled, isLoading, openDropdown]);

  useEffect(() => {
    if (!isOpen) {
      setFilteredItems(items);
      setIsUserTyping(false);
    }
  }, [isOpen, items]);

  const handleItemSelect = useCallback(
    (item: DropdownItem) => {
      if (item.disabled) {
        return;
      }

      setSelectedKey(item.key);
      setInputValue(item.label);
      setIsUserTyping(false);
      closeDropdown();
      onSelectionChange?.(item.key);
    },
    [closeDropdown, onSelectionChange],
  );

  const clearSelection = useCallback(() => {
    setSelectedKey("");
    setInputValue("");
    setIsUserTyping(false);
    onSelectionChange?.("");
  }, [onSelectionChange]);

  return {
    dropdownRef,
    inputRef,
    isOpen,
    toggleDropdown,
    closeDropdown,
    inputValue,
    handleInputChange,
    handleInputFocus,
    filteredItems,
    selectedKey,
    handleItemSelect,
    clearSelection,
  };
}

function DropdownItemsList({
  items,
  selectedKey,
  onSelect,
}: {
  items: DropdownItem[] | DropdownSection[];
  selectedKey: string;
  onSelect: (item: DropdownItem) => void;
}) {
  if (isFlatItemList(items)) {
    return (
      <>
        {items.map((item) => (
          <DropdownOptionButton
            key={item.key}
            item={item}
            selectedKey={selectedKey}
            onSelect={onSelect}
          />
        ))}
      </>
    );
  }

  const sections = items as DropdownSection[];

  return (
    <>
      {sections.map((section) => (
        <div key={section.title || section.items[0]?.key}>
          <div className="px-4 py-2 text-xs font-medium text-foreground-secondary border-b border-border/50">
            {section.title}
          </div>
          {section.items.map((item) => (
            <DropdownOptionButton
              key={item.key}
              item={item}
              selectedKey={selectedKey}
              onSelect={onSelect}
            />
          ))}
        </div>
      ))}
    </>
  );
}

function DropdownOptionButton({
  item,
  selectedKey,
  onSelect,
}: {
  item: DropdownItem;
  selectedKey: string;
  onSelect: (item: DropdownItem) => void;
}) {
  return (
    <button
      key={item.key}
      type="button"
      className={cn(
        "w-full text-left px-4 py-3 text-sm transition-all duration-200",
        "hover:bg-violet-500/10 hover:text-foreground",
        "focus:bg-brand-500/10 focus:text-foreground focus:outline-none",
        selectedKey === item.key && "bg-brand-500/20 text-foreground",
        item.disabled && "opacity-50 cursor-not-allowed",
        !item.disabled && "cursor-pointer",
      )}
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onSelect(item);
      }}
      onMouseDown={(event) => {
        event.preventDefault();
      }}
      disabled={item.disabled}
    >
      <div className="flex items-center justify-between">
        <span>{item.label}</span>
        {selectedKey === item.key && <Check className="w-4 h-4 text-violet-500" />}
      </div>
    </button>
  );
}

export function CustomDropdown({
  items,
  value,
  defaultValue,
  placeholder = "Select an option",
  disabled = false,
  className,
  inputClassName,
  onSelectionChange,
  onInputChange,
  isClearable = false,
  "data-testid": testId,
  "aria-label": ariaLabel,
  isLoading = false,
  loadingText = "Loading...",
  error,
  name,
}: CustomDropdownProps) {
  const controller = useCustomDropdownController({
    items,
    value,
    defaultValue,
    onSelectionChange,
    onInputChange,
    disabled,
    isLoading,
  });

  const handleClearClick = useCallback(
    (event: React.MouseEvent) => {
      event.stopPropagation();
      controller.clearSelection();
    },
    [controller],
  );

  return (
    <div ref={controller.dropdownRef} className={cn("relative w-full", className)}>
      <DropdownInput
        controller={controller}
        disabled={disabled}
        isLoading={isLoading}
        loadingText={loadingText}
        placeholder={placeholder}
        ariaLabel={ariaLabel}
        testId={testId}
        inputClassName={inputClassName}
        name={name}
        error={error}
        isClearable={isClearable}
        onClear={handleClearClick}
      />
      <DropdownErrorMessage error={error} />
      <DropdownMenu controller={controller} disabled={disabled} isLoading={isLoading} />
    </div>
  );
}

function DropdownInput({
  controller,
  disabled,
  isLoading,
  loadingText,
  placeholder,
  ariaLabel,
  testId,
  inputClassName,
  name,
  error,
  isClearable,
  onClear,
}: {
  controller: CustomDropdownController;
  disabled: boolean;
  isLoading: boolean;
  loadingText: string;
  placeholder: string;
  ariaLabel?: string;
  testId?: string;
  inputClassName?: string;
  name?: string;
  error?: string;
  isClearable: boolean;
  onClear: (event: React.MouseEvent) => void;
}) {
  const showClearButton = isClearable && controller.inputValue && !isLoading;
  const showErrorIcon = Boolean(error) && !isLoading;
  const showLoadingSpinner = isLoading;
  const showToggleButton = !isLoading;

  const renderStatusIcons = () => (
    <>
      {showLoadingSpinner && (
        <div className="p-1">
          <div className="w-4 h-4 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
        </div>
      )}

      {showErrorIcon && <DropdownErrorIcon />}

      {showClearButton && (
        <button
          type="button"
          onClick={onClear}
          className="p-1 hover:bg-violet-500/10 rounded transition-colors"
          aria-label="Clear selection"
        >
          <svg className="w-4 h-4 text-foreground-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </>
  );

  const renderToggleButton = () => {
    if (!showToggleButton) {
      return null;
    }

    return (
      <button
        type="button"
        onClick={controller.toggleDropdown}
        className={cn(
          "p-1 rounded transition-colors",
          "hover:bg-violet-500/10 focus:bg-brand-500/10 focus:outline-none",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          controller.isOpen && "bg-brand-500/10",
        )}
        aria-label="Toggle dropdown"
        disabled={disabled}
      >
        <ChevronDown
          className={cn(
            "w-4 h-4 text-foreground-secondary transition-transform duration-200",
            controller.isOpen && "rotate-180",
          )}
        />
      </button>
    );
  };

  return (
    <div className="relative">
      <input
        ref={controller.inputRef}
        type="text"
        name={name}
        value={controller.inputValue}
        onChange={controller.handleInputChange}
        onFocus={controller.handleInputFocus}
        onClick={controller.handleInputFocus}
        placeholder={isLoading ? loadingText : placeholder}
        disabled={disabled || isLoading}
        aria-label={ariaLabel}
        data-testid={testId}
        className={cn(
          "w-full h-10 px-4 pr-10 rounded-xl",
          "bg-background-secondary backdrop-blur-xl border",
          "text-foreground placeholder:text-foreground-secondary",
          "transition-all duration-200",
          error
            ? "border-danger-500/50 bg-danger-500/5 focus:border-danger-500/70 focus:bg-danger-500/10"
            : "border-border focus:border-brand-500/50 focus:bg-brand-500/5 focus:shadow-lg focus:shadow-brand-500/10",
          !error && "hover:border-brand-500/30 hover:bg-brand-500/3",
          "disabled:bg-background-tertiary disabled:border-border disabled:cursor-not-allowed disabled:opacity-50",
          inputClassName,
        )}
      />

      <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
        {renderStatusIcons()}
        {renderToggleButton()}
      </div>
    </div>
  );
}

function DropdownErrorMessage({ error }: { error?: string }) {
  if (!error) {
    return null;
  }

  return (
    <div className="mt-2 text-sm text-danger-500 flex items-center gap-1">
      <DropdownErrorIcon />
      <span>{error}</span>
    </div>
  );
}

function DropdownMenu({
  controller,
  disabled,
  isLoading,
}: {
  controller: CustomDropdownController;
  disabled: boolean;
  isLoading: boolean;
}) {
  if (!controller.isOpen || isLoading) {
    return null;
  }

  return (
    <div
      className="absolute z-50 mt-2 w-full rounded-xl border border-border bg-background-secondary shadow-lg overflow-hidden backdrop-blur-xl"
      role="listbox"
    >
      {controller.filteredItems && (
        <div className="max-h-60 overflow-y-auto custom-scrollbar">
          {controller.filteredItems.length === 0 && (
            <div className="px-4 py-3 text-sm text-foreground-secondary">
              No results found
            </div>
          )}
          <DropdownItemsList
            items={controller.filteredItems}
            selectedKey={controller.selectedKey}
            onSelect={controller.handleItemSelect}
          />
        </div>
      )}
    </div>
  );
}

function DropdownErrorIcon() {
  return (
    <div className="p-1">
      <svg
        className="w-4 h-4 text-danger-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
        />
      </svg>
    </div>
  );
}
