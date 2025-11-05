import React from "react";
import {
  UseComboboxGetMenuPropsOptions,
  UseComboboxGetItemPropsOptions,
} from "downshift";
import { cn } from "#/utils/utils";

export interface GenericDropdownMenuProps<T> {
  isOpen: boolean;
  filteredItems: T[];
  inputValue: string;
  highlightedIndex: number;
  selectedItem: T | null;
  getMenuProps: <Options>(
    options?: UseComboboxGetMenuPropsOptions & Options,
  ) => Record<string, unknown>;
  getItemProps: <Options>(
    options: UseComboboxGetItemPropsOptions<T> & Options,
  ) => Record<string, unknown>;
  onScroll?: (event: React.UIEvent<HTMLUListElement>) => void;
  menuRef?: React.RefObject<HTMLUListElement | null>;
  renderItem: (
    item: T,
    index: number,
    highlightedIndex: number,
    selectedItem: T | null,
    getItemProps: <Options>(
      options: UseComboboxGetItemPropsOptions<T> & Options,
    ) => Record<string, unknown>,
  ) => React.ReactNode;
  renderEmptyState: (inputValue: string) => React.ReactNode;
}

export function GenericDropdownMenu<T>({
  isOpen,
  filteredItems,
  inputValue,
  highlightedIndex,
  selectedItem,
  getMenuProps,
  getItemProps,
  onScroll,
  menuRef,
  renderItem,
  renderEmptyState,
}: GenericDropdownMenuProps<T>) {
  // Always render the menu element so that Downshift's getMenuProps is called
  // and its ref can be attached. When closed, hide it visually and expose
  // aria-hidden for accessibility. This avoids the runtime warnings from
  // Downshift in test environments where the menu may not mount synchronously.

  // Downshift requires getMenuProps to be called on the menu element. Passing
  // suppressRefError avoids noise when the menu is conditionally rendered in
  // tests/envs where refs aren't attached the same way.
  // Call getMenuProps with the runtime option `suppressRefError` as a second
  // argument. The TypeScript types for Downshift don't allow two args, so cast
  // to any to avoid type errors. This prevents `suppressRefError` from being
  // forwarded to the DOM as an attribute.
  // Downshift's types don't allow passing the runtime options we need; coerce only to a loose record for DOM spread
  const menuProps = (
    getMenuProps as unknown as (...args: unknown[]) => Record<string, unknown>
  )(
    {
      ref: menuRef,
      className: cn(
        "absolute z-10 w-full bg-[#454545] border border-[#717888] rounded-xl shadow-lg max-h-60 overflow-auto",
        "focus:outline-none p-1 gap-2 flex flex-col",
      ),
      onScroll,
    },
    { suppressRefError: true },
  );

  return (
    <ul
      // eslint-disable-next-line react/jsx-props-no-spreading
      {...menuProps}
      aria-hidden={!isOpen}
      style={{ display: isOpen ? undefined : "none" }}
    >
      {isOpen &&
        (filteredItems.length === 0
          ? renderEmptyState(inputValue)
          : filteredItems.map((item, index) =>
              renderItem(
                item,
                index,
                highlightedIndex,
                selectedItem,
                getItemProps,
              ),
            ))}
    </ul>
  );
}
