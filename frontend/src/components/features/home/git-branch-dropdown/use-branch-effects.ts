import { useEffect } from "react";
import type { Branch } from "#/types/git";

interface UseBranchEffectsProps {
  repository: string | null;
  defaultBranch: string | null | undefined;
  selectedBranch: Branch | null;
  userManuallyCleared: boolean;
  filteredBranches: Branch[] | undefined;
  isLoading: boolean;
  isOpen: boolean;
  inputValue: string;
  onBranchSelect: (branch: Branch | null) => void;
  setInputValue: (value: string) => void;
  setUserManuallyCleared: (value: boolean) => void;
}

export function useBranchEffects({
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
}: UseBranchEffectsProps) {
  // Reset branch selection when repository changes
  useEffect(() => {
    if (repository) {
      onBranchSelect(null);
      setUserManuallyCleared(false);
    }
  }, [repository, onBranchSelect, setUserManuallyCleared]);

  // Auto-select default branch when branches are loaded
  useEffect(() => {
    if (
      repository &&
      defaultBranch &&
      !selectedBranch &&
      !userManuallyCleared &&
      filteredBranches &&
      filteredBranches.length > 0 &&
      !isLoading
    ) {
      const defaultBranchObj = filteredBranches.find(
        (branch) => branch.name === defaultBranch,
      );

      if (defaultBranchObj) {
        onBranchSelect(defaultBranchObj);
      }
    }
  }, [
    repository,
    defaultBranch,
    selectedBranch,
    userManuallyCleared,
    filteredBranches,
    onBranchSelect,
    isLoading,
  ]);

  // Reset input when repository changes
  useEffect(() => {
    setInputValue("");
  }, [repository, setInputValue]);

  // Initialize input value when selectedBranch changes
  useEffect(() => {
    if (selectedBranch && !isOpen && inputValue !== selectedBranch.name) {
      setInputValue(selectedBranch.name);
    } else if (!selectedBranch && !isOpen && inputValue) {
      setInputValue("");
    }
  }, [selectedBranch, isOpen, inputValue, setInputValue]);
}
