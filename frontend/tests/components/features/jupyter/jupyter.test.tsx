import React from "react";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { describe, it, expect } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { jupyterReducer } from "#/state/jupyter-slice";
import { JupyterEditor } from "#/components/features/jupyter/jupyter";

vi.mock("#/hooks/use-runtime-is-ready", () => ({
  useRuntimeIsReady: () => true,
}));

describe("JupyterEditor", () => {
  const mockStore = configureStore({
    reducer: {
      fileState: () => ({}),
      initalQuery: () => ({}),
      browser: () => ({}),
      chat: () => ({}),
      code: () => ({}),
      cmd: () => ({}),
      agent: () => ({}),
      jupyter: jupyterReducer,
      securityAnalyzer: () => ({}),
      status: () => ({}),
    },
    preloadedState: {
      jupyter: {
        cells: Array(20).fill({
          content: "Test cell content",
          type: "input",
          output: "Test output",
        }),
      },
    },
  });

  it("should have a scrollable container", () => {
    const qc = new QueryClient();
    render(
      <Provider store={mockStore}>
        <QueryClientProvider client={qc}>
          <MemoryRouter initialEntries={["/conversations/123"]}>
            <Routes>
              <Route
                path="/conversations/:conversationId"
                element={
                  <div style={{ height: "100vh" }}>
                    <JupyterEditor maxWidth={800} />
                  </div>
                }
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </Provider>,
    );

    const container = screen.getByTestId("jupyter-container");
    expect(container).toHaveClass("flex-1 overflow-y-auto");
  });
});
