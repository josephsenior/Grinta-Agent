import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { MockInstance } from "vitest";
import { screen, render, waitFor } from "@testing-library/react";
import VSCodeTab from "#/routes/vscode-tab";

const runtimeReadyMock = vi.hoisted(() => vi.fn());
const vscodeUrlMock = vi.hoisted(() => vi.fn());
const vscodeNewTabMock = vi.hoisted(() => vi.fn());

vi.mock("#/hooks/use-runtime-is-ready", () => ({
  useRuntimeIsReady: runtimeReadyMock,
}));

vi.mock("#/hooks/query/use-vscode-url", () => ({
  useVSCodeUrl: vscodeUrlMock,
}));

vi.mock("#/utils/feature-flags", () => ({
  VSCODE_IN_NEW_TAB: vscodeNewTabMock,
}));

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
    }),
  };
});

describe("VSCodeTab route", () => {
  let windowOpenSpy: MockInstance | undefined;

  beforeEach(() => {
    runtimeReadyMock.mockReturnValue(true);
    vscodeNewTabMock.mockReturnValue(false);
    vscodeUrlMock.mockReturnValue({ data: { url: "http://localhost/vscode" }, isLoading: false, error: null });
  });

  afterEach(() => {
    windowOpenSpy?.mockRestore();
    windowOpenSpy = undefined;
    vi.clearAllMocks();
  });

  it("shows runtime inactive message when runtime is not ready", () => {
    runtimeReadyMock.mockReturnValue(false);

    render(<VSCodeTab />);

    expect(screen.getByText("DIFF_VIEWER$WAITING_FOR_RUNTIME")).toBeInTheDocument();
  });

  it("displays loading state while fetching VS Code URL", () => {
    vscodeUrlMock.mockReturnValue({ data: null, isLoading: true, error: null });

    render(<VSCodeTab />);

    expect(screen.getByText("VSCODE$LOADING")).toBeInTheDocument();
  });

  it("renders error state when URL fetch fails", () => {
    vscodeUrlMock.mockReturnValue({ data: { error: "URL missing" }, isLoading: false, error: null });

    render(<VSCodeTab />);

    expect(screen.getByText("URL missing")).toBeInTheDocument();
  });

  it("allows opening VS Code in new tab when cross-origin", async () => {
    vscodeNewTabMock.mockReturnValue(true);
    const url = "http://localhost:3030/vscode";
    vscodeUrlMock.mockReturnValue({ data: { url }, isLoading: false, error: null });
    windowOpenSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<VSCodeTab />);

    const button = await screen.findByRole("button", { name: "VSCODE$OPEN_IN_NEW_TAB" });
    expect(button).toBeInTheDocument();

    button.click();
    expect(windowOpenSpy).toHaveBeenCalledWith(url, "_blank", "noopener,noreferrer");
  });

  it("renders iframe when protocols match", async () => {
    vscodeNewTabMock.mockReturnValue(false);
    const url = `${window.location.protocol}//${window.location.host}/vscode`;
    vscodeUrlMock.mockReturnValue({ data: { url }, isLoading: false, error: null });

    render(<VSCodeTab />);

    await waitFor(() => expect(screen.getByTitle("VSCODE$TITLE")).toBeInTheDocument());
    const iframe = screen.getByTitle("VSCODE$TITLE") as HTMLIFrameElement;
    expect(iframe).toHaveAttribute("src", url);
  });

  it("shows URL parse error when provided URL is invalid", async () => {
    vscodeUrlMock.mockReturnValue({ data: { url: "not a valid url" }, isLoading: false, error: null });

    render(<VSCodeTab />);

    await waitFor(() => expect(screen.getByText("VSCODE$URL_PARSE_ERROR")).toBeInTheDocument());
  });
});
