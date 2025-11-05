import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SlackSettingsScreen from "../slack-settings";
import * as slackApi from "#/api/slack";

// Mock the API module
vi.mock("#/api/slack");

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock lucide-react
vi.mock("lucide-react", () => ({
  ExternalLink: () => <div data-testid="external-link-icon" />,
  Trash2: () => <div data-testid="trash-icon" />,
  CheckCircle: () => <div data-testid="check-circle-icon" />,
  XCircle: () => <div data-testid="x-circle-icon" />,
  Plus: () => <div data-testid="plus-icon" />,
}));

describe("SlackSettingsScreen", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it("should render loading state", () => {
    vi.mocked(slackApi.listSlackWorkspaces).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithQueryClient(<SlackSettingsScreen />);
    
    expect(screen.getByText("Slack Integration")).toBeInTheDocument();
  });

  it("should display empty state when no workspaces installed", async () => {
    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue([]);

    renderWithQueryClient(<SlackSettingsScreen />);

    await waitFor(() => {
      expect(screen.getByText("No Slack workspaces installed yet")).toBeInTheDocument();
    });
  });

  it("should display installed workspaces", async () => {
    const mockWorkspaces = [
      { team_id: "T123", team_name: "Test Workspace 1" },
      { team_id: "T456", team_name: "Test Workspace 2" },
    ];

    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue(mockWorkspaces);

    renderWithQueryClient(<SlackSettingsScreen />);

    await waitFor(() => {
      expect(screen.getByText("Test Workspace 1")).toBeInTheDocument();
      expect(screen.getByText("Test Workspace 2")).toBeInTheDocument();
    });
  });

  it("should handle install button click", async () => {
    const user = userEvent.setup();
    const mockInstallUrl = "https://slack.com/oauth/authorize?client_id=test";

    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue([]);
    vi.mocked(slackApi.getSlackInstallUrl).mockResolvedValue({
      url: mockInstallUrl,
    });

    // Mock window.location
    delete (window as any).location;
    window.location = { href: "" } as any;

    renderWithQueryClient(<SlackSettingsScreen />);

    const installButton = screen.getByTestId("install-slack-button");
    await user.click(installButton);

    await waitFor(() => {
      expect(slackApi.getSlackInstallUrl).toHaveBeenCalled();
    });
  });

  it("should handle uninstall button click", async () => {
    const user = userEvent.setup();
    const mockWorkspaces = [
      { team_id: "T123", team_name: "Test Workspace" },
    ];

    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue(mockWorkspaces);
    vi.mocked(slackApi.uninstallSlackWorkspace).mockResolvedValue();

    // Mock window.confirm
    window.confirm = vi.fn(() => true);

    renderWithQueryClient(<SlackSettingsScreen />);

    await waitFor(() => {
      expect(screen.getByText("Test Workspace")).toBeInTheDocument();
    });

    const uninstallButton = screen.getByTestId("uninstall-slack-T123");
    await user.click(uninstallButton);

    await waitFor(() => {
      expect(slackApi.uninstallSlackWorkspace).toHaveBeenCalledWith("T123");
    });
  });

  it("should show setup instructions", async () => {
    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue([]);

    renderWithQueryClient(<SlackSettingsScreen />);

    await waitFor(() => {
      expect(screen.getByText("Setup Instructions")).toBeInTheDocument();
      expect(screen.getByText(/SLACK_CLIENT_ID/)).toBeInTheDocument();
      expect(screen.getByText(/SLACK_CLIENT_SECRET/)).toBeInTheDocument();
    });
  });

  it("should show how it works guide", async () => {
    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue([]);

    renderWithQueryClient(<SlackSettingsScreen />);

    await waitFor(() => {
      expect(screen.getByText("How Slack Integration Works")).toBeInTheDocument();
      expect(screen.getByText(/Install the OpenHands app/)).toBeInTheDocument();
      expect(screen.getByText(/Mention @OpenHands/)).toBeInTheDocument();
    });
  });

  it("should show features list", async () => {
    vi.mocked(slackApi.listSlackWorkspaces).mockResolvedValue([]);

    renderWithQueryClient(<SlackSettingsScreen />);

    await waitFor(() => {
      expect(screen.getByText("Features")).toBeInTheDocument();
      expect(screen.getByText(/Real-time agent updates/)).toBeInTheDocument();
    });
  });
});

