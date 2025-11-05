import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithRouter } from "../test-utils";
import { RepositorySelectionForm } from "../src/components/features/home/repo-selection-form";
import { useUserRepositories } from "../src/hooks/query/use-user-repositories";
import {
  useRepositoryBranches,
  useRepositoryBranchesPaginated,
} from "../src/hooks/query/use-repository-branches";
import { useUserProviders } from "../src/hooks/use-user-providers";
import { useCreateConversation } from "../src/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "../src/hooks/use-is-creating-conversation";

// Mock the hooks
vi.mock("../src/hooks/query/use-user-repositories");
vi.mock("../src/hooks/query/use-repository-branches");
vi.mock("../src/hooks/use-user-providers");

// Mock the complex dropdown components to simple inputs for testability
vi.mock("../src/components/features/home/git-repo-dropdown", () => ({
  GitRepoDropdown: ({ value, onChange, disabled, "data-testid": _ }: any) =>
    // eslint-disable-next-line react/jsx-runtime
    React.createElement("input", {
      "data-testid": "git-repo-dropdown",
      value: value || "",
      disabled,
      onChange: (e: any) =>
        onChange && onChange({ id: e.target.value, full_name: e.target.value }),
    }),
}));

vi.mock("../src/components/features/home/git-branch-dropdown", () => {
  const ReactLocal = require("react");
  function MockBranch({ value, onBranchSelect, disabled, repository }: any) {
    const [cleared, setCleared] = ReactLocal.useState(false);

    // Reset cleared flag when repository changes (simulates re-mount behavior)
    ReactLocal.useEffect(() => {
      setCleared(false);
    }, [repository]);

    ReactLocal.useEffect(() => {
      if (value) {
        setCleared(false);
      }
    }, [value]);

    const val = value?.name || (disabled ? "" : cleared ? "" : "main");

    return ReactLocal.createElement("input", {
      "data-testid": "git-branch-dropdown-input",
      value: val,
      disabled,
      onChange: (e: any) => {
        const v = e.target.value;
        const trimmed = typeof v === "string" ? v.trim() : v;
        if (!trimmed) {
          setCleared(true);
          onBranchSelect && onBranchSelect(null);
        } else {
          setCleared(false);
          onBranchSelect && onBranchSelect({ name: trimmed });
        }
      },
    });
  }

  return { GitBranchDropdown: MockBranch };
});
vi.mock("../src/hooks/mutation/use-create-conversation");
vi.mock("../src/hooks/use-is-creating-conversation");
vi.mock("react-i18next", async (importActual) => {
  const actual = await importActual<typeof import("react-i18next")>();
  return {
    ...(actual as Record<string, unknown>),
    useTranslation: () => ({ t: (key: string) => key }),
  };
});

describe("RepositorySelectionForm", () => {
  const mockOnRepoSelection = vi.fn();

  // Helper to call mockReturnValue on an imported mock without sprinkling `as any`.
  const applyMockReturn = (mocked: unknown, value: unknown) => {
    // Narrow the temporary cast to a small interface so `any` isn't used widely.
    const m = mocked as unknown as { mockReturnValue?: (v: unknown) => void };
    m.mockReturnValue?.(value);
  };

  beforeEach(() => {
    vi.resetAllMocks();

    // Mock the hooks with default values
    applyMockReturn(useUserProviders, {
      providers: [{ id: "github", name: "GitHub", provider: "github" }],
    });
    applyMockReturn(useUserRepositories, {
      data: [
        { id: "1", full_name: "test/repo1" },
        { id: "2", full_name: "test/repo2" },
      ],
      isLoading: false,
      isError: false,
    });

    applyMockReturn(useRepositoryBranches, {
      data: [{ name: "main" }, { name: "develop" }],
      isLoading: false,
      isError: false,
    });

    // The component uses the paginated hook in some places; mock it too
    applyMockReturn(useRepositoryBranchesPaginated, {
      data: { pages: [{ branches: [{ name: "main" }, { name: "develop" }] }] },
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isLoading: false,
      isFetchingNextPage: false,
      isError: false,
    });

    applyMockReturn(useCreateConversation, {
      mutate: vi.fn(() => applyMockReturn(useIsCreatingConversation, true)),
      isPending: false,
      isSuccess: false,
    });

    applyMockReturn(useIsCreatingConversation, false);
  });

  it("should clear selected branch when input is empty", async () => {
    renderWithRouter(
      <RepositorySelectionForm onRepoSelection={mockOnRepoSelection} />,
    );

    // First select a repository to enable the branch dropdown
    const repoDropdown = screen.getByTestId("git-repo-dropdown");
    fireEvent.change(repoDropdown, { target: { value: "test/repo1" } });

    // Get the branch dropdown and wait for it to become enabled (provider auto-select effect)
    const branchDropdown = screen.getByTestId("git-branch-dropdown-input");
    await waitFor(() => expect(branchDropdown).not.toBeDisabled());

    // Simulate deleting all text in the branch input
    fireEvent.change(branchDropdown, { target: { value: "" } });

    // Verify the branch input is cleared (no selected branch)
    expect(branchDropdown).toHaveValue("");
  });

  it("should clear selected branch when input contains only whitespace", async () => {
    renderWithRouter(
      <RepositorySelectionForm onRepoSelection={mockOnRepoSelection} />,
    );

    // First select a repository to enable the branch dropdown
    const repoDropdown = screen.getByTestId("git-repo-dropdown");
    fireEvent.change(repoDropdown, { target: { value: "test/repo1" } });

    // Get the branch dropdown and wait for it to become enabled (provider auto-select effect)
    const branchDropdown = screen.getByTestId("git-branch-dropdown-input");
    await waitFor(() => expect(branchDropdown).not.toBeDisabled());

    // Simulate entering only whitespace in the branch input
    fireEvent.change(branchDropdown, { target: { value: "   " } });

    // Verify the branch input is cleared (no selected branch)
    expect(branchDropdown).toHaveValue("");
  });

  it("should keep branch empty after being cleared even with auto-selection", async () => {
    renderWithRouter(
      <RepositorySelectionForm onRepoSelection={mockOnRepoSelection} />,
    );

    // First select a repository to enable the branch dropdown
    const repoDropdown = screen.getByTestId("git-repo-dropdown");
    fireEvent.change(repoDropdown, { target: { value: "test/repo1" } });

    // Get the branch dropdown and wait for it to become enabled (provider auto-select effect)
    const branchDropdown = screen.getByTestId("git-branch-dropdown-input");
    await waitFor(() => expect(branchDropdown).not.toBeDisabled());

    // The branch should be auto-selected to "main" initially
    expect(branchDropdown).toHaveValue("main");

    // Simulate deleting all text in the branch input
    fireEvent.change(branchDropdown, { target: { value: "" } });

    // Verify the branch input is cleared (no selected branch)
    expect(branchDropdown).toHaveValue("");

    // Trigger a re-render by changing something else
    fireEvent.change(repoDropdown, { target: { value: "test/repo2" } });
    fireEvent.change(repoDropdown, { target: { value: "test/repo1" } });

    // The branch should be auto-selected to "main" again after repo change
    expect(branchDropdown).toHaveValue("main");

    // Clear it again
    fireEvent.change(branchDropdown, { target: { value: "" } });

    // Verify it stays empty
    expect(branchDropdown).toHaveValue("");

    // Simulate a component update without changing repos
    // This would normally trigger the useEffect if our fix wasn't working
    fireEvent.blur(branchDropdown);

    // Verify it still stays empty
    expect(branchDropdown).toHaveValue("");
  });
});
