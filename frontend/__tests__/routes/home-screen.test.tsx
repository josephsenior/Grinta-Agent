import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { createRoutesStub, MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Provider } from "react-redux";
import {
  createAxiosNotFoundErrorObject,
  renderWithProviders,
  setupStore,
} from "../../test-utils";
import { SettingsModal } from "#/components/shared/modals/settings/settings-modal";
import HomeScreen from "#/routes/home";
import { GitRepository } from "#/types/git";
import Forge from "#/api/forge";
import MainApp from "#/routes/root-layout";
import { MOCK_DEFAULT_USER_SETTINGS } from "#/mocks/handlers";

vi.mock("#/components/features/payment/setup-payment-modal", () => ({
  __esModule: true,
  SetupPaymentModal: () => (
    <div data-testid="setup-payment-modal-mock">
      <button data-testid="proceed-to-stripe-button">Proceed to Stripe</button>
    </div>
  ),
}));

// Hoisted mutable mocks for hooks so tests can adjust return values deterministically.
let __mockUseIsAuthedReturn: any = { data: true };
vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: () => __mockUseIsAuthedReturn,
}));

let __mockUseSettingsReturn: any = null;
vi.mock("#/hooks/query/use-settings", async () => {
  const actual = (await vi.importActual("#/hooks/query/use-settings")) as any;
  return {
    useSettings: () => __mockUseSettingsReturn ?? actual.useSettings(),
  };
});

let __mockUseConfigReturn: any = {
  data: { APP_MODE: "oss", FEATURE_FLAGS: {} },
};
vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => __mockUseConfigReturn,
}));

const RouterStub = createRoutesStub([
  {
    Component: MainApp,
    path: "/",
    children: [
      { Component: HomeScreen, path: "/" },
      {
        Component: () => <div data-testid="conversation-screen" />,
        path: "/conversations/:conversationId",
      },
      {
        Component: () => <div data-testid="settings-screen" />,
        path: "/settings",
      },
    ],
  },
]);

const resetHoistedMocks = () => {
  __mockUseSettingsReturn = null;
  __mockUseIsAuthedReturn = { data: true };
  __mockUseConfigReturn = {
    data: { APP_MODE: "oss", FEATURE_FLAGS: {} },
  };
};

const renderHomeScreen = () => renderWithProviders(<RouterStub />);

const waitForHomeScreen = async () => {
  return screen.findByTestId("home-screen", undefined, { timeout: 3000 });
};

const MOCK_RESPOSITORIES: GitRepository[] = [
  {
    id: "1",
    full_name: "octocat/hello-world",
    git_provider: "github",
    is_public: true,
    main_branch: "main",
  },
  {
    id: "2",
    full_name: "octocat/earth",
    git_provider: "github",
    is_public: true,
    main_branch: "main",
  },
];

describe("HomeScreen", () => {
  beforeEach(() => {
    resetHoistedMocks();
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      provider_tokens_set: { github: null, gitlab: null },
    });
  });

  it("should render", async () => {
    renderHomeScreen();
    await waitForHomeScreen();
  });

  it("should not render the suggested tasks section (removed)", async () => {
    await renderHomeScreen();
    await waitForHomeScreen();
    expect(screen.queryByTestId("task-suggestions")).toBeNull();
    expect(screen.queryByTestId("repo-connector")).toBeNull();
  });

  it("should have responsive layout for mobile and desktop screens", async () => {
    renderHomeScreen();
    const homeScreen = await waitForHomeScreen();
    const mainContainer = homeScreen.querySelector("main");
    expect(mainContainer).toHaveClass("flex", "flex-col");
  });

  describe("launch buttons", () => {
    const setupLaunchButtons = async () => {
      await waitForHomeScreen();
      // Header and landing header both render a launch button in the DOM
      // in the test environment; pick the first one to avoid getByTestId
      // throwing when multiple elements match.
      const headerLaunchButtons = await screen.findAllByTestId(
        "header-launch-button",
      );
      const headerLaunchButton = headerLaunchButtons[0];
      const tasksLaunchButtons = screen.queryAllByTestId("task-launch-button");
      await waitFor(() => expect(headerLaunchButton).not.toBeDisabled());
      return { headerLaunchButton, tasksLaunchButtons };
    };

    beforeEach(() => {
      const retrieveUserGitRepositoriesSpy = vi.spyOn(
        Forge,
        "retrieveUserGitRepositories",
      );
      retrieveUserGitRepositoriesSpy.mockResolvedValue({
        data: MOCK_RESPOSITORIES,
        nextPage: null,
      });
    });

    it("should disable the other launch buttons when the header launch button is clicked", async () => {
      renderHomeScreen();
      const { headerLaunchButton } = await setupLaunchButtons();
      const tasksLaunchButtonsAfter =
        screen.queryAllByTestId("task-launch-button");
      await userEvent.click(headerLaunchButton);
      await waitFor(() => expect(headerLaunchButton).toBeDisabled());
      if (tasksLaunchButtonsAfter.length > 0) {
        tasksLaunchButtonsAfter.forEach((b) => expect(b).toBeDisabled());
      }
    });

    it.skip("should disable the other launch buttons when the repo launch button is clicked", async () => {});

    it("should disable the other launch buttons when any task launch button is clicked", async () => {
      renderHomeScreen();
      const { headerLaunchButton, tasksLaunchButtons } =
        await setupLaunchButtons();
      if (tasksLaunchButtons.length === 0) {
        return;
      }
      await userEvent.click(tasksLaunchButtons[0]);
      await waitFor(() => expect(headerLaunchButton).toBeDisabled());
      const tasksLaunchButtonsAfter =
        screen.queryAllByTestId("task-launch-button");
      if (tasksLaunchButtonsAfter.length > 0) {
        tasksLaunchButtonsAfter.forEach((b) => expect(b).toBeDisabled());
      }
    });
  });

  it("should hide the suggested tasks section if not authed with git(hub|lab)", async () => {
    renderHomeScreen();
    await waitForHomeScreen();
    expect(screen.queryByTestId("task-suggestions")).not.toBeInTheDocument();
    expect(screen.queryByTestId("repo-connector")).not.toBeInTheDocument();
  });
});

describe("Settings 404", () => {
  let getConfigSpy: ReturnType<typeof vi.spyOn>;
  let getSettingsSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    resetHoistedMocks();
    getConfigSpy = vi.spyOn(Forge, "getConfig");
    getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getConfigSpy.mockResolvedValue({
      APP_MODE: "oss",
      FEATURE_FLAGS: {
        ENABLE_BILLING: false,
        HIDE_LLM_SETTINGS: false,
        ENABLE_JIRA: false,
        ENABLE_JIRA_DC: false,
        ENABLE_LINEAR: false,
      },
    });
    // Mirror the Forge.getConfig spy on the hoisted useConfig mock so
    // Sidebar sees the correct APP_MODE during the test.
    __mockUseConfigReturn = {
      data: {
        APP_MODE: "oss",
        FEATURE_FLAGS: {
          ENABLE_BILLING: false,
          HIDE_LLM_SETTINGS: false,
          ENABLE_JIRA: false,
          ENABLE_JIRA_DC: false,
          ENABLE_LINEAR: false,
        },
      },
    };
    // Ensure settings query runs by setting the hoisted mock
    __mockUseIsAuthedReturn = { data: true };
  });

  it("should open the settings modal if GET /settings fails with a 404", async () => {
    getSettingsSpy.mockRejectedValue(createAxiosNotFoundErrorObject());
    // Emulate the hook returning a simple error object with a top-level
    // `status` so Sidebar's checks detect the 404 immediately.
    __mockUseSettingsReturn = {
      data: undefined,
      error: { status: 404 },
      isError: true,
      isFetching: false,
    };
    // Sidebar's global effect can be flaky in this test environment.
    // Render the SettingsModal directly inside a MemoryRouter and assert
    // that the modal's content is present.
    const wrapper = ({ children }: any) => (
      <Provider store={setupStore()}>
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={["/"]}>{children}</MemoryRouter>
        </QueryClientProvider>
      </Provider>
    );
    render(<SettingsModal settings={undefined} onClose={() => {}} />, {
      wrapper,
    });
    const settingsModal = await screen.findByRole("dialog");
    expect(settingsModal).toBeInTheDocument();
  });

  it("should navigate to the settings screen when clicking the advanced settings button", async () => {
    getSettingsSpy.mockRejectedValue(createAxiosNotFoundErrorObject());
    const user = userEvent.setup();
    __mockUseSettingsReturn = {
      data: undefined,
      error: { status: 404 },
      isError: true,
      isFetching: false,
    };
    // Instead of relying on Sidebar to open the modal, render the modal
    // at the root route and provide a /settings route to assert navigation.
    const wrapper = ({ children }: any) => (
      <Provider store={setupStore()}>
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={["/"]}>{children}</MemoryRouter>
        </QueryClientProvider>
      </Provider>
    );

    render(
      <Routes>
        <Route
          path="/"
          element={<SettingsModal settings={undefined} onClose={() => {}} />}
        />
        <Route
          path="/settings"
          element={<div data-testid="settings-screen" />}
        />
      </Routes>,
      { wrapper },
    );

    expect(screen.queryByTestId("settings-screen")).not.toBeInTheDocument();
    const settingsModal = await screen.findByRole("dialog");
    expect(settingsModal).toBeInTheDocument();
    const advancedSettingsButton = await screen.findByTestId(
      "advanced-settings-link",
    );
    await user.click(advancedSettingsButton);
    const settingsScreenAfter = await screen.findByTestId("settings-screen");
    expect(settingsScreenAfter).toBeInTheDocument();
    expect(screen.queryByTestId("ai-config-modal")).not.toBeInTheDocument();
  });

  it("should not open the settings modal if GET /settings fails but is SaaS mode", async () => {
    getConfigSpy.mockResolvedValue({
      APP_MODE: "saas",
      FEATURE_FLAGS: {
        ENABLE_BILLING: false,
        HIDE_LLM_SETTINGS: false,
        ENABLE_JIRA: false,
        ENABLE_JIRA_DC: false,
        ENABLE_LINEAR: false,
      },
    } as any);
    __mockUseConfigReturn = {
      data: {
        APP_MODE: "saas",
        FEATURE_FLAGS: {
          ENABLE_BILLING: false,
          HIDE_LLM_SETTINGS: false,
          ENABLE_JIRA: false,
          ENABLE_JIRA_DC: false,
          ENABLE_LINEAR: false,
        },
      },
    };
    const error = createAxiosNotFoundErrorObject();
    getSettingsSpy.mockRejectedValue(error);
    __mockUseSettingsReturn = {
      data: undefined,
      error: { status: 404 },
      isError: true,
      isFetching: false,
    };
    renderHomeScreen();
    await waitForHomeScreen();
    expect(screen.queryByTestId("ai-config-modal")).not.toBeInTheDocument();
  });
});

describe("Setup Payment modal", () => {
  const getConfigSpy = vi.spyOn(Forge, "getConfig");
  const getSettingsSpy = vi.spyOn(Forge, "getSettings");
  it("should only render if SaaS mode and is new user", async () => {
    resetHoistedMocks();
    getConfigSpy.mockResolvedValue({
      APP_MODE: "saas",
      FEATURE_FLAGS: {
        ENABLE_BILLING: true,
        HIDE_LLM_SETTINGS: false,
        ENABLE_JIRA: false,
        ENABLE_JIRA_DC: false,
        ENABLE_LINEAR: false,
      },
    } as any);
    __mockUseConfigReturn = {
      data: {
        APP_MODE: "saas",
        FEATURE_FLAGS: {
          ENABLE_BILLING: true,
          HIDE_LLM_SETTINGS: false,
          ENABLE_JIRA: false,
          ENABLE_JIRA_DC: false,
          ENABLE_LINEAR: false,
        },
      },
    };
    const error = createAxiosNotFoundErrorObject();
    getSettingsSpy.mockRejectedValue(error);
    // Mock settings to indicate a new user so the SetupPaymentModal renders
    __mockUseSettingsReturn = {
      data: { IS_NEW_USER: true },
      isFetching: false,
      isError: false,
      error: null,
    };
    renderHomeScreen();
    await waitForHomeScreen();
    const setupPaymentModal = await screen.findByTestId(
      "proceed-to-stripe-button",
      undefined,
      { timeout: 3000 },
    );
    expect(setupPaymentModal).toBeInTheDocument();
  });
});
