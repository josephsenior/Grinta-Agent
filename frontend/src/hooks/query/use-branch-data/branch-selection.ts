import type { Branch } from "#/types/git";

export function shouldUseSearchResults(
  processedSearchInput: string | null,
  searchData: Branch[] | undefined,
  selectedBranch: Branch | null,
  inputValue: string,
): boolean {
  return (
    !!processedSearchInput &&
    !!searchData &&
    !(selectedBranch && inputValue === selectedBranch.name)
  );
}

export function findDefaultBranchInList(
  branches: Branch[],
  defaultBranch: string,
): Branch | undefined {
  return branches.find((branch) => branch.name === defaultBranch);
}

export function prioritizeDefaultBranch(
  branches: Branch[],
  defaultBranch: string,
): Branch[] {
  const defaultBranchObj = findDefaultBranchInList(branches, defaultBranch);

  if (!defaultBranchObj) {
    return branches;
  }

  const otherBranches = branches.filter(
    (branch) => branch.name !== defaultBranch,
  );
  return [defaultBranchObj, ...otherBranches];
}

export function mergeDefaultBranchIfNeeded(
  branches: Branch[],
  defaultBranch: string,
  defaultBranchData: Branch[] | undefined,
): Branch[] {
  const defaultBranchObj = findDefaultBranchInList(branches, defaultBranch);

  if (defaultBranchObj) {
    return prioritizeDefaultBranch(branches, defaultBranch);
  }

  if (defaultBranchData && defaultBranchData.length > 0) {
    const defaultBranchFromData = findDefaultBranchInList(
      defaultBranchData,
      defaultBranch,
    );

    if (defaultBranchFromData) {
      return [defaultBranchFromData, ...branches];
    }
  }

  return branches;
}
