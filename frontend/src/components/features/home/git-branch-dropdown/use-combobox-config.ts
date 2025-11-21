import { useCombobox } from "downshift";
import type { Branch } from "#/types/git";

interface UseComboboxConfigProps {
  filteredBranches: Branch[] | undefined;
  selectedBranch: Branch | null;
  inputValue: string;
  onBranchSelect: (branch: Branch | null) => void;
  onInputValueChange: ({ inputValue }: { inputValue?: string }) => void;
}

export function useComboboxConfig({
  filteredBranches,
  selectedBranch,
  inputValue,
  onBranchSelect,
  onInputValueChange,
}: UseComboboxConfigProps) {
  return useCombobox({
    items: filteredBranches || [],
    selectedItem: selectedBranch,
    itemToString: (item) => item?.name || "",
    onSelectedItemChange: ({ selectedItem: newSelectedItem }) => {
      onBranchSelect(newSelectedItem || null);
    },
    onInputValueChange,
    inputValue,
  });
}
