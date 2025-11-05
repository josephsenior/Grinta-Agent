import React, { useState, useRef, useEffect } from "react";
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
}

export function CustomDropdown({
  items,
  value,
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
}: CustomDropdownProps) {
  // Helper function to find item label by key
  const findItemLabel = (list: DropdownItem[] | DropdownSection[], key: string): string => {
    if (Array.isArray(list) && list.length > 0 && "key" in list[0]) {
      // It's DropdownItem[]
      const item = (list as DropdownItem[]).find((it) => it.key === key);
      return item?.label || "";
    }
    // It's DropdownSection[]
    for (const section of list as DropdownSection[]) {
      const item = section.items.find((it) => it.key === key);
      if (item) return item.label;
    }
    return "";
  };

  // Initialize states with proper values
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState(() => findItemLabel(items, value || ""));
  const [filteredItems, setFilteredItems] = useState(items);
  const [selectedKey, setSelectedKey] = useState(value || "");
  const [isUserTyping, setIsUserTyping] = useState(false); // Track if user is actively typing
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Memoize item lookup for performance
  const itemsMap = React.useMemo(() => {
    const map = new Map<string, string>();
    if (Array.isArray(items) && items.length > 0 && "key" in items[0]) {
      (items as DropdownItem[]).forEach(item => map.set(item.key, item.label));
    } else {
      (items as DropdownSection[]).forEach(section => {
        section.items.forEach(item => map.set(item.key, item.label));
      });
    }
    return map;
  }, [items]);

  // Update inputValue when value or items change
  useEffect(() => {
    const newInputValue = findItemLabel(items, value || "");
    setInputValue(newInputValue);
    setSelectedKey(value || "");
    setIsUserTyping(false); // Reset typing flag when value changes externally
  }, [value, items]);

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        console.log('Click outside detected, closing dropdown');
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle escape key to close dropdown
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen]);

  // Filter items based on input - ONLY when user is actively typing
  useEffect(() => {
    // Don't filter if user hasn't started typing
    if (!isUserTyping) {
      setFilteredItems(items);
      return;
    }

    // Don't filter if input is empty
    if (!inputValue.trim()) {
      setFilteredItems(items);
      return;
    }

    const filterItems = (
      list: DropdownItem[] | DropdownSection[],
    ): DropdownItem[] | DropdownSection[] => {
      if (Array.isArray(list) && list.length > 0 && "key" in list[0]) {
        // It's DropdownItem[]
        return (list as DropdownItem[]).filter((it) =>
          it.label.toLowerCase().includes(inputValue.toLowerCase()),
        );
      }
      // It's DropdownSection[]
      return (list as DropdownSection[])
        .map((section) => ({
          ...section,
          items: section.items.filter((it) =>
            it.label.toLowerCase().includes(inputValue.toLowerCase()),
          ),
        }))
        .filter((section) => section.items.length > 0);
    };

    setFilteredItems(filterItems(items));
  }, [inputValue, items, isUserTyping]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setIsUserTyping(true); // User is now actively typing
    onInputChange?.(newValue);

    if (!isOpen) {
      setIsOpen(true);
    }
  };

  const handleItemClick = (key: string, label: string) => {
    setSelectedKey(key);
    setInputValue(label);
    setIsOpen(false);
    setIsUserTyping(false); // Reset typing flag when user selects an item
    onSelectionChange?.(key);
  };

  const handleItemClickFor = (item: DropdownItem) => () => {
    console.log('Dropdown item clicked:', item.key, item.label);
    if (!item.disabled) {
      handleItemClick(item.key, item.label);
    }
  };

  const handleInputFocus = () => {
    if (!disabled) {
      setIsOpen(true);
    }
  };

  // Reuse focus handler for click to avoid duplicate logic
  const handleInputClick = handleInputFocus;

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedKey("");
    setInputValue("");
    onSelectionChange?.("");
  };

  // Helper removed: getSelectedLabel was unused. The component keeps selectedKey
  // and displays the selected label inline where needed.

  const renderItems = () => {
    if (
      Array.isArray(filteredItems) &&
      filteredItems.length > 0 &&
      "key" in filteredItems[0]
    ) {
      // Render simple items
      return (filteredItems as DropdownItem[]).map((item) => (
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
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Button click event:', item.key);
            handleItemClickFor(item)();
          }}
          onMouseDown={(e) => {
            e.preventDefault(); // Prevent focus loss
          }}
          disabled={item.disabled}
        >
          <div className="flex items-center justify-between">
            <span>{item.label}</span>
            {selectedKey === item.key && (
              <Check className="w-4 h-4 text-violet-500" />
            )}
          </div>
        </button>
      ));
    }
    // Render sections
    return (filteredItems as DropdownSection[]).map((section) => (
      <div key={section.title || section.items[0]?.key}>
        <div className="px-4 py-2 text-xs font-medium text-foreground-secondary border-b border-border/50">
          {section.title}
        </div>
        {section.items.map((item) => (
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
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('Section button click event:', item.key);
              handleItemClickFor(item)();
            }}
            onMouseDown={(e) => {
              e.preventDefault(); // Prevent focus loss
            }}
            disabled={item.disabled}
          >
            <div className="flex items-center justify-between">
              <span>{item.label}</span>
              {selectedKey === item.key && (
                <Check className="w-4 h-4 text-violet-500" />
              )}
            </div>
          </button>
        ))}
      </div>
    ));
  };

  return (
    <div ref={dropdownRef} className={cn("relative w-full", className)}>
      {/* Input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onClick={handleInputClick}
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

        {/* Icons */}
        <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
          {/* Loading Spinner */}
          {isLoading && (
            <div className="p-1">
              <div className="w-4 h-4 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
            </div>
          )}

          {/* Error Icon */}
          {error && !isLoading && (
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
          )}

          {/* Clear Button */}
          {isClearable && inputValue && !isLoading && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 hover:bg-violet-500/10 rounded transition-colors"
              aria-label="Clear selection"
            >
              <svg
                className="w-4 h-4 text-foreground-secondary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}

          {/* Dropdown Toggle */}
          {!isLoading && (
            <button
              type="button"
              onClick={() => setIsOpen(!isOpen)}
              className={cn(
                "p-1 rounded transition-colors",
                "hover:bg-violet-500/10 focus:bg-brand-500/10 focus:outline-none",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                isOpen && "bg-brand-500/10",
              )}
              aria-label="Toggle dropdown"
              disabled={disabled}
            >
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-foreground-secondary transition-transform duration-200",
                  isOpen && "rotate-180",
                )}
              />
            </button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-2 text-sm text-danger-500 flex items-center gap-1">
          <svg
            className="w-4 h-4 flex-shrink-0"
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
          <span>{error}</span>
        </div>
      )}

      {/* Dropdown */}
      {isOpen && !isLoading && (
        <div className="absolute z-[9999] w-full mt-1 bg-background-secondary backdrop-blur-xl rounded-xl border border-border shadow-lg shadow-brand-500/10 max-h-60 overflow-y-auto pointer-events-auto">
          {filteredItems.length === 0 ? (
            <div className="px-4 py-3 text-sm text-foreground-secondary text-center">
              {/* i18n: No options found */}
              No options found
            </div>
          ) : (
            renderItems()
          )}
        </div>
      )}
      
    </div>
  );
}
