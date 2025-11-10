import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Jupyter from "#/routes/jupyter-tab";
import { renderWithProviders } from "../../test-utils";

type ResizeObserverCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
let latestResizeObserverCallback: ResizeObserverCallback | null = null;

class MockResizeObserver {
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    latestResizeObserverCallback = callback;
  }

  observe() {}

  unobserve() {}

  disconnect() {
    if (latestResizeObserverCallback === this.callback) {
      latestResizeObserverCallback = null;
    }
  }
}

vi.stubGlobal("ResizeObserver", MockResizeObserver);

vi.mock("#/components/features/jupyter/jupyter", () => ({
  JupyterEditor: ({ maxWidth }: { maxWidth: number }) => (
    <div data-testid="jupyter-editor">maxWidth:{maxWidth}</div>
  ),
}));

describe("Jupyter tab route", () => {
  beforeEach(() => {
    latestResizeObserverCallback = null;
  });

  it("renders the editor with a default max width", async () => {
    renderWithProviders(<Jupyter />);

    expect(await screen.findByTestId("jupyter-editor")).toHaveTextContent("maxWidth:9999");
  });

  it("updates the editor width when the container resizes", async () => {
    renderWithProviders(<Jupyter />);

    const editor = await screen.findByTestId("jupyter-editor");
    expect(editor).toHaveTextContent("maxWidth:9999");

    latestResizeObserverCallback?.([{ contentRect: { width: 640 } }]);

    expect(await screen.findByTestId("jupyter-editor")).toHaveTextContent("maxWidth:640");
  });
});
