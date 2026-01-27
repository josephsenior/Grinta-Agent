import { screen, within } from "@testing-library/react";
import * as RouterDom from "react-router-dom";
import type { GetConfigResponse } from "#/api/forge.types";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SettingsScreen, { clientLoader } from "#/routes/settings";
import Forge from "#/api/forge";
import { renderWithProviders } from "#test-utils";

// Mock the i18next hook
vi.mock("react-i18next", async () => {
  const actual =
    await vi.importActual<typeof import("react-i18next")>("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => {
        const translations: Record<string, string> = {
          SETTINGS$NAV_INTEGRATIONS: "Integrations",
          SETTINGS$NAV_APPLICATION: "Application",
          SETTINGS$NAV_CREDITS: "Credits",
          SETTINGS$NAV_API_KEYS: "API Keys",
          SETTINGS$NAV_LLM: "LLM",
          SETTINGS$NAV_SECRETS: "Secrets",
          SETTINGS$NAV_MCP: "MCP",
          SETTINGS$NAV_USER: "User",
          SETTINGS$TITLE: "Settings",
        };
        return translations[key] || key;
      },
      i18n: {
        changeLanguage: vi.fn(() => Promise.resolve()),
      },
    }),
  };
});

const { handleLogoutMock, mockQueryClient, subscriptionAccessMock } =
  vi.hoisted(() => ({
    handleLogoutMock: vi.fn(),
    subscriptionAccessMock: vi.fn<() => boolean | undefined>(
      () => undefined,
    ),
    mockQueryClient: (() => {
      const { QueryClient } = require("@tanstack/react-query");
      return new QueryClient();
    })(),
  }));

const navigateMock = vi.fn();
vi.spyOn(RouterDom, "useNavigate").mockImplementation(() => navigateMock);

const baseConfig: GetConfigResponse = {
  APP_MODE: "oss",
  GITHUB_CLIENT_ID: "",
  POSTHOG_CLIENT_KEY: "",
  FEATURE_FLAGS: {
    ENABLE_BILLING: false,
    HIDE_LLM_SETTINGS: false,
    ENABLE_JIRA: false,
    ENABLE_JIRA_DC: false,
    ENABLE_LINEAR: false,
  },
};

vi.mock("#/hooks/use-app-logout", () => ({
  useAppLogout: vi.fn().mockReturnValue({ handleLogout: handleLogoutMock }),
}));

vi.mock("#/query-client-config", () => ({
  queryClient: mockQueryClient,
}));

vi.mock("#/hooks/query/use-subscription-access", () => ({
  useSubscriptionAccess: () => ({ data: subscriptionAccessMock() }),
}));

describe("Settings Screen", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    subscriptionAccessMock.mockReset();
    subscriptionAccessMock.mockReturnValue(undefined);
  });

  const RouterStub = RouterDom.createRoutesStub([
    {
          Component: SettingsScreen,
          loader: clientLoader as any,
      path: "/settings",
      children: [
        {
          Component: () => <div data-testid="llm-settings-screen" />,
          path: "/settings",
        },
        {
          Component: () => <div data-testid="git-settings-screen" />,
          path: "/settings/integrations",
        },
        {
          Component: () => <div data-testid="application-settings-screen" />,
          path: "/settings/app",
        },
        {
          Component: () => <div data-testid="user-settings-screen" />,
          path: "/settings/user",
        },
        {
          Component: () => <div data-testid="billing-settings-screen" />,
          path: "/settings/billing",
        },
        {
          Component: () => <div data-testid="api-keys-settings-screen" />,
          path: "/settings/api-keys",
        },
      ],
    },
  ]);

  const renderSettingsScreen = (path = "/settings") =>
    renderWithProviders(<RouterStub initialEntries={[path]} />, {
      queryClient: mockQueryClient,
    });

  it("should render the navbar", async () => {
    const sectionsToInclude = ["llm", "integrations", "application", "secrets"];
    const sectionsToExclude = ["api keys", "credits", "billing"];
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue({
      APP_MODE: "oss",
      GITHUB_CLIENT_ID: "test-client-id",
      FEATURE_FLAGS: {
        HIDE_LLM_SETTINGS: false,
      },
    });

    // Clear any existing query data
    mockQueryClient.clear();

    renderSettingsScreen();

    const navbar = await screen.findByRole("navigation");
    sectionsToInclude.forEach((section) => {
      const sectionElement = within(navbar).getByText(section, {
        exact: false, // case insensitive
      });
      expect(sectionElement).toBeInTheDocument();
    });
    sectionsToExclude.forEach((section) => {
      const sectionElement = within(navbar).queryByText(section, {
        exact: false, // case insensitive
      });
      expect(sectionElement).not.toBeInTheDocument();
    });

    getConfigSpy.mockRestore();
  });

  it("should render the saas navbar", async () => {
    const saasConfig: GetConfigResponse = {
      ...baseConfig,
      APP_MODE: "saas",
      FEATURE_FLAGS: {
        ...baseConfig.FEATURE_FLAGS,
        ENABLE_BILLING: true,
      },
    };

    // Clear any existing query data and set the config
    mockQueryClient.clear();
    mockQueryClient.setQueryData(["config"], saasConfig);
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(saasConfig);

    const expectedLinks = [
      "/settings/user",
      "/settings/integrations",
      "/settings/app",
      "/settings/billing",
      "/settings/secrets",
      "/settings/api-keys",
    ];

    renderSettingsScreen();

    const navbar = await screen.findByRole("navigation");
    expectedLinks.forEach((href) => {
      expect(navbar.querySelector(`a[href="${href}"]`)).not.toBeNull();
    });

    expect(navbar.querySelector('a[href="/settings"]')).toBeNull();

    getConfigSpy.mockRestore();
  });

  it("should render the LLM tab when subscription access is granted in saas mode", async () => {
    const saasConfig: GetConfigResponse = {
      ...baseConfig,
      APP_MODE: "saas",
    };

    subscriptionAccessMock.mockReturnValue(true);
    mockQueryClient.clear();
    mockQueryClient.setQueryData(["config"], saasConfig);
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(saasConfig);

    renderSettingsScreen();

    const navbar = await screen.findByRole("navigation");
    expect(navbar.querySelector('a[href="/settings"]')).not.toBeNull();

    getConfigSpy.mockRestore();
  });

  it("should navigate back to home when the back button is clicked", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(baseConfig);

    mockQueryClient.clear();

    renderSettingsScreen();

    const backButton = await screen.findByRole("button", {
      name: "Go back to home",
    });
    await backButton.click();

    expect(navigateMock).toHaveBeenCalledWith("/");

    getConfigSpy.mockRestore();
  });

  it("should not be able to access saas-only routes in oss mode", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(baseConfig);

    // Clear any existing query data
    mockQueryClient.clear();

    // In OSS mode, accessing restricted routes should redirect to /settings
    // Since createRoutesStub doesn't handle clientLoader redirects properly,
    // we test that the correct navbar is shown (OSS navbar) and that
    // the restricted route components are not rendered when accessing /settings
    renderSettingsScreen("/settings");

    // Verify we're in OSS mode by checking the navbar
    const navbar = await screen.findByRole("navigation");
    expect(within(navbar).getByText("LLM")).toBeInTheDocument();
    expect(
      within(navbar).queryByText("credits", { exact: false }),
    ).not.toBeInTheDocument();

    // Verify the LLM settings screen is shown
    expect(screen.getByTestId("llm-settings-screen")).toBeInTheDocument();
    expect(
      screen.queryByTestId("billing-settings-screen"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("api-keys-settings-screen"),
    ).not.toBeInTheDocument();

    getConfigSpy.mockRestore();
  });

  it.todo("should not be able to access oss-only routes in saas mode");
});

describe("clientLoader", () => {
  afterEach(() => {
    mockQueryClient.clear();
  });

  it("should return null when called without args", async () => {
    await expect(clientLoader(undefined as any)).resolves.toBeNull();
  });

  it("should redirect /settings to /settings/app", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(baseConfig);

    const request = new Request("https://example.com/settings");
    const response = await clientLoader({ request } as any);

    expect(response?.status).toBe(302);
    expect(response?.headers.get("Location")).toBe("/settings/app");

    getConfigSpy.mockRestore();
  });

  it("should redirect saas-only paths to /settings in oss mode", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(baseConfig);

    const request = new Request("https://example.com/settings/billing");
    const response = await clientLoader({ request } as any);

    expect(response?.status).toBe(302);
    expect(response?.headers.get("Location")).toBe("/settings");

    getConfigSpy.mockRestore();
  });

  it("should return null for allowed paths", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(baseConfig);

    const request = new Request("https://example.com/settings/app");
    await expect(clientLoader({ request } as any)).resolves.toBeNull();

    getConfigSpy.mockRestore();
  });
});

