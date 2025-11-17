import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "test-utils";
import { createRoutesStub } from "react-router-dom";
import { ExpandableMessage } from "#/components/features/chat/expandable-message";
import Forge from "#/api/forge";

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: {
        changeLanguage: () => new Promise(() => {}),
        language: "en",
        exists: () => true,
      },
    }),
  };
});

describe("ExpandableMessage", () => {
  it("should render with neutral border for non-action messages", () => {
    renderWithProviders(<ExpandableMessage message="Hello" type="thought" />);
    const element = screen.getAllByText("Hello")[0];
    const container = element.closest(
      "div.flex.gap-2.items-center.justify-start",
    );
    expect(container).toHaveClass("border-neutral-300");
    const statusIcon = screen
      .queryAllByTestId("mocked-svg")
      .find((el) =>
        el.classList.contains("fill-success") ||
        el.classList.contains("fill-danger"),
      );
    expect(statusIcon).toBeUndefined();
  });

  it("should render with neutral border for error messages", () => {
    renderWithProviders(
      <ExpandableMessage message="Error occurred" type="error" />,
    );
    const element = screen.getAllByText("Error occurred")[0];
    const container = element.closest(
      "div.flex.gap-2.items-center.justify-start",
    );
    expect(container).toHaveClass("border-danger");
    const statusIcon = screen
      .queryAllByTestId("mocked-svg")
      .find((el) =>
        el.classList.contains("fill-success") ||
        el.classList.contains("fill-danger"),
      );
    expect(statusIcon).toBeUndefined();
  });

  it("should render with success icon for successful action messages", () => {
    renderWithProviders(
      <ExpandableMessage
        id="OBSERVATION_MESSAGE$RUN"
        message="Command executed successfully"
        type="action"
        success
      />,
    );
    const element = screen.getByText("OBSERVATION_MESSAGE$RUN");
    const container = element.closest(
      "div.flex.gap-2.items-center.justify-start",
    );
    expect(container).toHaveClass("border-neutral-300");
    const icon = screen
      .getAllByTestId("mocked-svg")
      .find((el) => el.classList.contains("fill-success"));
    expect(icon).toBeDefined();
  });

  it("should render with error icon for failed action messages", () => {
    renderWithProviders(
      <ExpandableMessage
        id="OBSERVATION_MESSAGE$RUN"
        message="Command failed"
        type="action"
        success={false}
      />,
    );
    const element = screen.getByText("OBSERVATION_MESSAGE$RUN");
    const container = element.closest(
      "div.flex.gap-2.items-center.justify-start",
    );
    expect(container).toHaveClass("border-neutral-300");
    const icon = screen
      .getAllByTestId("mocked-svg")
      .find((el) => el.classList.contains("fill-danger"));
    expect(icon).toBeDefined();
  });

  it("should render with neutral border and no icon for action messages without success prop", () => {
    renderWithProviders(
      <ExpandableMessage
        id="OBSERVATION_MESSAGE$RUN"
        message="Running command"
        type="action"
      />,
    );
    const element = screen.getByText("OBSERVATION_MESSAGE$RUN");
    const container = element.closest(
      "div.flex.gap-2.items-center.justify-start",
    );
    expect(container).toHaveClass("border-neutral-300");
    const statusIcon = screen
      .queryAllByTestId("mocked-svg")
      .find((el) =>
        el.classList.contains("fill-success") ||
        el.classList.contains("fill-danger"),
      );
    expect(statusIcon).toBeUndefined();
  });

  it("should render with neutral border and no icon for action messages with undefined success (timeout case)", () => {
    renderWithProviders(
      <ExpandableMessage
        id="OBSERVATION_MESSAGE$RUN"
        message="Command timed out"
        type="action"
        success={undefined}
      />,
    );
    const element = screen.getByText("OBSERVATION_MESSAGE$RUN");
    const container = element.closest(
      "div.flex.gap-2.items-center.justify-start",
    );
    expect(container).toHaveClass("border-neutral-300");
    const statusIcon = screen
      .queryAllByTestId("mocked-svg")
      .find((el) =>
        el.classList.contains("fill-success") ||
        el.classList.contains("fill-danger"),
      );
    expect(statusIcon).toBeUndefined();
  });

  it("should render the out of credits message when the user is out of credits", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue({
      APP_MODE: "saas",
      FEATURE_FLAGS: {
        ENABLE_BILLING: true,
        HIDE_LLM_SETTINGS: false,
        ENABLE_JIRA: false,
        ENABLE_JIRA_DC: false,
        ENABLE_LINEAR: false,
      },
    });
    const RouterStub = createRoutesStub([
      {
        Component: () => (
          <ExpandableMessage
            id="STATUS$ERROR_LLM_OUT_OF_CREDITS"
            message=""
            type=""
          />
        ),
        path: "/",
      },
    ]);

    renderWithProviders(<RouterStub />);
    await screen.findByTestId("out-of-credits");
  });
});
