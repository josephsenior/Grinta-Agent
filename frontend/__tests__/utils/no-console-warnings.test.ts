import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import React from "react";

describe("no console warnings", () => {
  it("does not emit console.warn or console.error during a simple render", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    function Dummy() {
      return React.createElement("div", { "data-testid": "dummy" }, "ok");
    }

    const { getByTestId } = render(React.createElement(Dummy));
    expect(getByTestId("dummy")).toBeDefined();

    expect(warnSpy).not.toHaveBeenCalled();
    expect(errorSpy).not.toHaveBeenCalled();

    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });
});
