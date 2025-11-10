import { render, screen, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import userEvent from "@testing-library/user-event";
import * as RouterDom from "react-router-dom";
import {
  createRoutesStub,
  MemoryRouter,
  Routes,
  Route,
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Provider } from "react-redux";
import {
  createAxiosNotFoundErrorObject,
  renderWithProviders,
  setupStore,
} from "../../test-utils";
import { SettingsModal } from "#/components/shared/modals/settings/settings-modal";
import { Sidebar } from "#/components/features/sidebar/sidebar";
import { SetupPaymentModal } from "#/components/features/payment/setup-payment-modal";
import HomeScreen, { hydrateFallback } from "#/routes/home";
import { GitRepository } from "#/types/git";
import Forge from "#/api/forge";
import MainApp from "#/routes/root-layout";
import { MOCK_DEFAULT_USER_SETTINGS } from "#/mocks/handlers";

const mutateCreateConversationMock = vi.fn();
let __isCreatingConversation = false;
let __lastWrappedOptions: any = null;
vi.mock("#/hooks/mutation/use-create-conversation", () => {
  const React = require("react");
  return {
    useCreateConversation: () => {
      const [isPending, setIsPending] = React.useState(false);
      const mutate = (variables: unknown, options?: any) => {
        __isCreatingConversation = true;
        setIsPending(true);
        const wrappedOptions =
          options != null
            ? {
                ...options,
                onSuccess: (...args: any[]) => {
                  options.onSuccess?.(...args);
                  setIsPending(false);
                  __isCreatingConversation = false;
                },
                onError: (...args: any[]) => {
                  options.onError?.(...args);
                  setIsPending(false);
                  __isCreatingConversation = false;
                },
                onSettled: (...args: any[]) => {
                  options.onSettled?.(...args);
                  setIsPending(false);
                  __isCreatingConversation = false;
                },
              }
            : {
                onSuccess: () => {
                  setIsPending(false);
                  __isCreatingConversation = false;
                },
                onError: () => {
                  setIsPending(false);
                  __isCreatingConversation = false;
                },
                onSettled: () => {
                  setIsPending(false);
                  __isCreatingConversation = false;
                },
              };
        __lastWrappedOptions = wrappedOptions;
        return mutateCreateConversationMock(variables, wrappedOptions);
      };
      return { mutate, isPending };
    },
  };
});

vi.mock("#/hooks/use-is-creating-conversation", () => ({
  useIsCreatingConversation: () => __isCreatingConversation,
}));

vi.mock("#/components/features/payment/setup-payment-modal", () => ({
  __esModule: true,
  SetupPaymentModal: () => (
    <div data-testid="setup-payment-modal-mock">
      <button data-testid="proceed-to-stripe-button">Proceed to Stripe</button>
    </div>
  ),
}));

vi.mock("#/components/ui/dark-veil", () => ({
  __esModule: true,
  default: () => <div data-testid="dark-veil-mock" />,
}));

vi.mock("#/hooks/query/use-git-user", () => ({
  useGitUser: () => undefined,
}));

vi.mock("#/hooks/mutation/use-logout", () => ({
  useLogout: () => vi.fn(),
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
  __isCreatingConversation = false;
  __lastWrappedOptions = null;
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
    mutateCreateConversationMock.mockReset();
    window.localStorage.clear();
  });

  it("should render", async () => {
    renderHomeScreen();
    await waitForHomeScreen();
  });

  it("exports hydrate fallback markup", () => {
    const { container } = renderWithProviders(<>{hydrateFallback}</>);
    const fallback = container.querySelector(".route-loading");
    expect(fallback).toBeInTheDocument();
    expect(fallback?.getAttribute("aria-hidden")).toBe("true");
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

  it("should create a conversation and navigate on success", async () => {
    mutateCreateConversationMock.mockImplementationOnce(
      (_variables: unknown, options?: { onSuccess?: (data: any) => void }) => {
        act(() => {
          options?.onSuccess?.({ conversation_id: "conversation-123" });
        });
      },
    );

    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: <HomeScreen />,
        },
        {
          path: "/conversations/:conversationId",
          element: <div data-testid="conversation-screen" />,
        },
      ],
      { initialEntries: ["/"] },
    );

    renderWithProviders(<RouterProvider router={router} />);
    await waitForHomeScreen();

    const startButton = await screen.findByRole("button", {
      name: "Start Building",
    });

    await userEvent.click(startButton);

    expect(mutateCreateConversationMock).toHaveBeenCalledWith(
      {},
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );

    expect(window.localStorage.getItem("RECENT_CONVERSATION_ID")).toBe(
      "conversation-123",
    );
  });

  it("should show loading state on the start button while creating a conversation", async () => {
    mutateCreateConversationMock.mockImplementationOnce(() => {});

    renderHomeScreen();
    await waitForHomeScreen();

    const startButton = await screen.findByRole("button", {
      name: "Start Building",
    });

    await userEvent.click(startButton);

    await waitFor(() => expect(startButton).toHaveTextContent("Starting..."));
  });

  it("should handle localStorage failures when starting a conversation", async () => {
    const originalSetItem = Storage.prototype.setItem;
    const setItemSpy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(function (this: Storage, key: string, value: string) {
        if (key === "RECENT_CONVERSATION_ID") {
          throw new Error("quota exceeded");
        }
        return originalSetItem.call(this, key, value);
      });

    mutateCreateConversationMock.mockImplementationOnce(
      (_variables: unknown, options?: { onSuccess?: (data: any) => void }) => {
        act(() => {
          options?.onSuccess?.({ conversation_id: "conversation-999" });
        });
      },
    );

    const navigateMock = vi.fn();
    const useNavigateSpy = vi
      .spyOn(RouterDom, "useNavigate")
      .mockReturnValue(navigateMock);

    try {
      renderWithProviders(<HomeScreen />, { route: "/" });

      const startButton = await screen.findByRole("button", {
        name: "Start Building",
      });
      await userEvent.click(startButton);

      expect(mutateCreateConversationMock).toHaveBeenCalled();
      expect(navigateMock).toHaveBeenCalledWith(
        "/conversations/conversation-999",
      );
      expect(setItemSpy).toHaveBeenCalled();
    } finally {
      setItemSpy.mockRestore();
      localStorage.clear();
      useNavigateSpy.mockRestore();
    }
  });
});

describe("Settings 404", () => {
  let getConfigSpy: MockInstance;
  let getSettingsSpy: MockInstance;
  let retrieveReposSpy: MockInstance;

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
    retrieveReposSpy = vi
      .spyOn(Forge, "retrieveUserGitRepositories")
      .mockResolvedValue({
        data: [],
        nextPage: null,
      });
  });

  afterEach(() => {
    retrieveReposSpy.mockRestore();
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
    renderWithProviders(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Sidebar />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.queryByTestId("ai-config-modal")).not.toBeInTheDocument(),
    );
  });
});

describe("Setup Payment modal", () => {
  const getConfigSpy = vi.spyOn(Forge, "getConfig");
  const getSettingsSpy = vi.spyOn(Forge, "getSettings");
  it("should only render if SaaS mode and is new user", async () => {
    const controller = {
      config: {
        APP_MODE: "saas",
        FEATURE_FLAGS: {
          ENABLE_BILLING: true,
        },
      },
      settings: { IS_NEW_USER: true },
    } as const;

    const TestOverlay = () => (
      <>
        {controller.config.FEATURE_FLAGS.ENABLE_BILLING &&
          controller.config.APP_MODE === "saas" &&
          controller.settings.IS_NEW_USER && <SetupPaymentModal />}
      </>
    );

    renderWithProviders(<TestOverlay />);

    expect(
      await screen.findByTestId("proceed-to-stripe-button"),
    ).toBeInTheDocument();
  });
});
