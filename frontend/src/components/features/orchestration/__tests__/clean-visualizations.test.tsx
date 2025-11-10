import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  CleanVisualAdapter,
  getPriorityBadgeClass,
} from "../clean-visualizations";

describe("clean-visualizations helpers", () => {
  it("maps priority values to badge classes", () => {
    expect(getPriorityBadgeClass("critical")).toContain("text-red-400");
    expect(getPriorityBadgeClass("MEDIUM")).toContain("text-yellow-400");
    expect(getPriorityBadgeClass(undefined)).toContain("text-neutral-400");
    expect(getPriorityBadgeClass("unknown-priority")).toContain(
      "text-neutral-400",
    );
  });
});

describe("CleanVisualAdapter", () => {
  it("renders fallback for unknown roles", () => {
    render(
      <CleanVisualAdapter
        artifact={
          {
            role: "unknown_role",
            data: {},
          } as any
        }
      />,
    );

    expect(screen.getByText(/Unknown role: unknown_role/i)).toBeInTheDocument();
  });
});
