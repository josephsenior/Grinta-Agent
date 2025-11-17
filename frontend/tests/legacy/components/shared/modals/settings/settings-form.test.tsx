import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../../../../test-utils";
import { createRoutesStub } from "react-router-dom";
import { screen } from "@testing-library/react";
import Forge from "#/api/forge";
import { SettingsForm } from "#/components/shared/modals/settings/settings-form";
import { DEFAULT_SETTINGS } from "#/services/settings";

describe("SettingsForm", () => {
  const onCloseMock = vi.fn();

  const RouteStub = createRoutesStub([
    {
      Component: () => (
        <SettingsForm
          settings={DEFAULT_SETTINGS}
          models={[DEFAULT_SETTINGS.LLM_MODEL]}
          onClose={onCloseMock}
        />
      ),
      path: "/",
    },
  ]);

  it("should save the user settings and close the modal when the form is submitted", async () => {
    const user = userEvent.setup();
    const saveSettingsSpy = vi.spyOn(Forge, "saveSettings");
    
    renderWithProviders(<RouteStub />);

    const saveButton = screen.getByRole("button", { name: /save/i });
    await user.click(saveButton);

    expect(saveSettingsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        llm_model: expect.any(String),
      }),
    );
    
    saveSettingsSpy.mockRestore();
  });
});
