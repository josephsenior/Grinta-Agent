import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BadgeInput } from "#/components/shared/inputs/badge-input";

describe("BadgeInput", () => {
  it("should render the values", () => {
    const onChangeMock = vi.fn();
    render(<BadgeInput value={["test", "test2"]} onChange={onChangeMock} />);

    expect(screen.getByText("test")).toBeInTheDocument();
    expect(screen.getByText("test2")).toBeInTheDocument();
  });

  it("should render the input's as a badge on space", async () => {
    const onChangeMock = vi.fn();
    render(<BadgeInput value={["badge1"]} onChange={onChangeMock} />);

    const input = screen.getByTestId("badge-input");
    expect(input).toHaveValue("");

    fireEvent.change(input, { target: { value: "test" } });
    fireEvent.keyDown(input, { key: " ", code: "Space" });

    expect(onChangeMock).toHaveBeenCalledWith(["badge1", "test"]);
    expect(input).toHaveValue("");
  });

  it("should remove the badge on backspace", async () => {
    const onChangeMock = vi.fn();
    render(<BadgeInput value={["badge1", "badge2"]} onChange={onChangeMock} />);

    const input = screen.getByTestId("badge-input");
    expect(input).toHaveValue("");

    fireEvent.keyDown(input, { key: "Backspace" });

    expect(onChangeMock).toHaveBeenCalledWith(["badge1"]);
    expect(input).toHaveValue("");
  });

  it("should remove the badge on click", async () => {
    const onChangeMock = vi.fn();
    render(<BadgeInput value={["badge1"]} onChange={onChangeMock} />);

    const removeButton = screen.getByTestId("remove-button");
    await userEvent.click(removeButton);

    expect(onChangeMock).toHaveBeenCalledWith([]);
  });

  it("should not create empty badges", async () => {
    const onChangeMock = vi.fn();
    render(<BadgeInput value={[]} onChange={onChangeMock} />);

    const input = screen.getByTestId("badge-input");
    expect(input).toHaveValue("");

    fireEvent.keyDown(input, { key: " ", code: "Space" });
    expect(onChangeMock).not.toHaveBeenCalled();
  });
});
