import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect } from "vitest";
import { ModalBackdrop } from "../modal-backdrop";

describe("ModalBackdrop", () => {
  it("calls onClose when Escape pressed and onClose provided", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <ModalBackdrop onClose={onClose}>
        <div>
          <button type="button">first</button>
          <button type="button">second</button>
        </div>
      </ModalBackdrop>,
    );

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("does not call onClose when Escape pressed and onClose is absent", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <ModalBackdrop>
        <div>
          <button type="button">first</button>
        </div>
      </ModalBackdrop>,
    );

    await user.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("traps focus inside the modal when tabbing", async () => {
    const user = userEvent.setup();

    render(
      <ModalBackdrop>
        <div>
          <button type="button">first</button>
          <button type="button">second</button>
        </div>
      </ModalBackdrop>,
    );

    const first = screen.getByRole("button", { name: /first/i });
    const second = screen.getByRole("button", { name: /second/i });

    // initial focus should land on first
    await waitFor(() => {
      expect(document.activeElement).toBe(first);
    });

    await user.tab();
    expect(document.activeElement).toBe(second);

    await user.tab();
    expect(document.activeElement).toBe(first);

    await user.tab({ shift: true });
    expect(document.activeElement).toBe(second);
  });
});
