import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FileExplorer } from "#/components/features/file-explorer/file-explorer";

vi.mock("#/api/forge", () => ({
  default: {
    getFiles: vi
      .fn()
      .mockResolvedValue([
        "src/components/App.tsx",
        "src/utils/helpers.ts",
        "README.md",
        "package.json",
      ]),
  },
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe("FileExplorer", () => {
  const renderExplorer = () =>
    render(
      <FileExplorer
        conversationId="test-conversation"
        onFileSelect={() => {}}
        onFileOpen={() => {}}
        onFileDelete={() => {}}
        onFileRename={() => {}}
      />,
    );

  it("renders without crashing", async () => {
    renderExplorer();

    expect(await screen.findByText("Files")).toBeInTheDocument();
  });

  it("shows loading state initially", async () => {
    renderExplorer();

    expect(
      await screen.findByTestId("file-explorer-loading"),
    ).toBeInTheDocument();
  });
});
