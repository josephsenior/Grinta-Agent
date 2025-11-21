import { useState, useMemo } from "react";
import { useDebounce } from "#/hooks/use-debounce";

export function useBranchInput() {
  const [inputValue, setInputValue] = useState("");
  const debouncedInputValue = useDebounce(inputValue, 300);

  const processedSearchInput = useMemo(
    () =>
      debouncedInputValue.trim().length > 0 ? debouncedInputValue.trim() : "",
    [debouncedInputValue],
  );

  return {
    inputValue,
    setInputValue,
    processedSearchInput,
  };
}
