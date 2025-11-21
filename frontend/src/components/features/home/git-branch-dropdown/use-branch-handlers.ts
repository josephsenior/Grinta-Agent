import { useCallback } from "react";
import type { Branch } from "#/types/git";

interface UseBranchHandlersProps {
  onBranchSelect: (branch: Branch | null) => void;
  setInputValue: (value: string) => void;
  setUserManuallyCleared: (value: boolean) => void;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
}

export function useBranchHandlers({
  onBranchSelect,
  setInputValue,
  setUserManuallyCleared,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}: UseBranchHandlersProps) {
  const handleClear = useCallback(() => {
    setInputValue("");
    onBranchSelect(null);
    setUserManuallyCleared(true);
  }, [onBranchSelect, setInputValue, setUserManuallyCleared]);

  const handleBranchSelect = useCallback(
    (branch: Branch | null) => {
      onBranchSelect(branch);
      setInputValue("");
    },
    [onBranchSelect, setInputValue],
  );

  const handleInputValueChange = useCallback(
    ({ inputValue: newInputValue }: { inputValue?: string }) => {
      if (newInputValue !== undefined) {
        setInputValue(newInputValue);
      }
    },
    [setInputValue],
  );

  const handleMenuScroll = useCallback(
    (event: React.UIEvent<HTMLUListElement>) => {
      const { scrollTop, scrollHeight, clientHeight } = event.currentTarget;
      if (
        scrollHeight - scrollTop <= clientHeight * 1.5 &&
        hasNextPage &&
        !isFetchingNextPage
      ) {
        fetchNextPage();
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage],
  );

  return {
    handleClear,
    handleBranchSelect,
    handleInputValueChange,
    handleMenuScroll,
  };
}
