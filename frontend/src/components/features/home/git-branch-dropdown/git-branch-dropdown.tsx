import React, { useState, useRef } from "react";
import { Branch } from "#/types/git";
import { Provider } from "#/types/settings";
import { cn } from "#/utils/utils";
import { useBranchData } from "#/hooks/query/use-branch-data";
import { useBranchEffects } from "./use-branch-effects";
import { useBranchHandlers } from "./use-branch-handlers";
import { useBranchInput } from "./use-branch-input";
import { useComboboxConfig } from "./use-combobox-config";
import { LoadingSpinner } from "../shared/loading-spinner";
import { ClearButton } from "../shared/clear-button";
import { ToggleButton } from "../shared/toggle-button";
import { ErrorMessage } from "../shared/error-message";
import { BranchDropdownMenu } from "./branch-dropdown-menu";

export interface GitBranchDropdownProps {
  repository: string | null;
  provider: Provider;
  selectedBranch: Branch | null;
  onBranchSelect: (branch: Branch | null) => void;
  defaultBranch?: string | null;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function GitBranchDropdown({
  repository,
  provider,
  selectedBranch,
  onBranchSelect,
  defaultBranch,
  placeholder = "Select branch...",
  disabled = false,
  className,
}: GitBranchDropdownProps) {
  const [userManuallyCleared, setUserManuallyCleared] = useState(false);
  const menuRef = useRef<HTMLUListElement>(null);

  const { inputValue, setInputValue, processedSearchInput } = useBranchInput();

  // Use the new branch data hook with default branch prioritization
  const {
    branches: filteredBranches,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isSearchLoading,
  } = useBranchData(
    repository,
    provider,
    defaultBranch || null,
    processedSearchInput,
    inputValue,
    selectedBranch,
  );

  const error = isError ? new Error("Failed to load branches") : null;

  const {
    handleClear,
    handleBranchSelect,
    handleInputValueChange,
    handleMenuScroll,
  } = useBranchHandlers({
    onBranchSelect,
    setInputValue,
    setUserManuallyCleared,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  });

  const {
    isOpen,
    selectedItem,
    highlightedIndex,
    getInputProps,
    getItemProps,
    getMenuProps,
    getToggleButtonProps,
  } = useComboboxConfig({
    filteredBranches,
    selectedBranch,
    inputValue,
    onBranchSelect: handleBranchSelect,
    onInputValueChange: handleInputValueChange,
  });

  useBranchEffects({
    repository,
    defaultBranch,
    selectedBranch,
    userManuallyCleared,
    filteredBranches,
    isLoading,
    isOpen,
    inputValue,
    onBranchSelect,
    setInputValue,
    setUserManuallyCleared,
  });

  const isLoadingState = isLoading || isSearchLoading || isFetchingNextPage;

  return (
    <div className={cn("relative", className)}>
      <div className="relative">
        <input
          // eslint-disable-next-line react/jsx-props-no-spreading
          {...getInputProps({
            disabled: disabled || !repository,
            placeholder,
            className: cn(
              "w-full px-3 py-2 border border-[#717888] rounded-sm shadow-sm min-h-[2.5rem]",
              "bg-[#454545] text-[#ECEDEE] placeholder:text-[#B7BDC2] placeholder:italic",
              "focus:outline-none focus:ring-1 focus:ring-[#717888] focus:border-[#717888]",
              "disabled:bg-[#363636] disabled:cursor-not-allowed disabled:opacity-60",
              "pr-10", // Space for toggle button
            ),
          })}
          data-testid="git-branch-dropdown-input"
        />

        <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
          {selectedBranch && (
            <ClearButton disabled={disabled} onClear={handleClear} />
          )}

          <ToggleButton
            isOpen={isOpen}
            disabled={disabled || !repository}
            getToggleButtonProps={getToggleButtonProps}
          />
        </div>

        {isLoadingState && <LoadingSpinner hasSelection={!!selectedBranch} />}
      </div>

      <BranchDropdownMenu
        isOpen={isOpen}
        filteredBranches={filteredBranches || []}
        inputValue={inputValue}
        highlightedIndex={highlightedIndex}
        selectedItem={selectedItem}
        getMenuProps={getMenuProps}
        getItemProps={getItemProps}
        onScroll={handleMenuScroll}
        menuRef={menuRef}
      />

      <ErrorMessage isError={!!error} />
    </div>
  );
}
