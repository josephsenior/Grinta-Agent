import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import KnowledgeBaseSettings from "#/routes/settings.knowledge-base";
import { renderWithProviders } from "../../test-utils";

vi.mock("#/components/features/knowledge-base/knowledge-base-manager", () => ({
  KnowledgeBaseManager: () => <div data-testid="knowledge-base-manager" />,
}));

describe("Knowledge base settings route", () => {
  it("renders the knowledge base manager", () => {
    renderWithProviders(<KnowledgeBaseSettings />);

    expect(screen.getByTestId("knowledge-base-manager")).toBeInTheDocument();
  });
});
