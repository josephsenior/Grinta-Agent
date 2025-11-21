import { useMemo } from "react";
import { useRepositoryBranchesPaginated } from "./use-repository-branches";
import { useSearchBranches } from "./use-search-branches";
import { Branch } from "#/types/git";
import { Provider } from "#/types/settings";
import {
  shouldUseSearchResults,
  prioritizeDefaultBranch,
  mergeDefaultBranchIfNeeded,
} from "./use-branch-data/branch-selection";

export function useBranchData(
  repository: string | null,
  provider: Provider,
  defaultBranch: string | null,
  processedSearchInput: string,
  inputValue: string,
  selectedBranch?: Branch | null,
) {
  // Fetch branches with pagination
  const {
    data: branchData,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isFetchingNextPage,
    isError,
  } = useRepositoryBranchesPaginated(repository);

  // Search branches when user types
  const { data: searchData, isLoading: isSearchLoading } = useSearchBranches(
    repository,
    processedSearchInput,
    30,
    provider,
  );

  // Combine all branches from paginated data
  const allBranches = useMemo(
    () => branchData?.pages?.flatMap((page) => page.branches) || [],
    [branchData],
  );

  // Check if default branch is in the loaded branches
  const defaultBranchInLoaded = useMemo(
    () =>
      defaultBranch
        ? allBranches.find((branch) => branch.name === defaultBranch)
        : null,
    [allBranches, defaultBranch],
  );

  // Only search for default branch if it's not already in the loaded branches
  // and we have loaded some branches (to avoid searching immediately on mount)
  const shouldSearchDefaultBranch =
    defaultBranch &&
    !defaultBranchInLoaded &&
    allBranches.length > 0 &&
    !processedSearchInput; // Don't search for default branch when user is searching

  const { data: defaultBranchData, isLoading: isDefaultBranchLoading } =
    useSearchBranches(
      repository,
      shouldSearchDefaultBranch ? defaultBranch : "",
      30,
      provider,
    );

  // Get branches to display with default branch prioritized
  const branches = useMemo(() => {
    const useSearch = shouldUseSearchResults(
      processedSearchInput,
      searchData,
      selectedBranch ?? null,
      inputValue,
    );

    let branchesToUse: Branch[] = useSearch ? (searchData ?? []) : allBranches;

    if (defaultBranch) {
      if (useSearch) {
        branchesToUse = mergeDefaultBranchIfNeeded(
          branchesToUse,
          defaultBranch,
          defaultBranchData,
        );
      } else {
        branchesToUse = defaultBranchInLoaded
          ? prioritizeDefaultBranch(branchesToUse, defaultBranch)
          : mergeDefaultBranchIfNeeded(
              branchesToUse,
              defaultBranch,
              defaultBranchData,
            );
      }
    }

    return branchesToUse;
  }, [
    processedSearchInput,
    searchData,
    allBranches,
    selectedBranch,
    inputValue,
    defaultBranch,
    defaultBranchInLoaded,
    defaultBranchData,
  ]);

  return {
    branches,
    allBranches,
    fetchNextPage,
    hasNextPage,
    isLoading: isLoading || isDefaultBranchLoading,
    isFetchingNextPage,
    isError,
    isSearchLoading,
  };
}
