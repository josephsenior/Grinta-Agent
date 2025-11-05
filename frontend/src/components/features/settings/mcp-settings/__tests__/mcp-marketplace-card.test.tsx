import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect } from "vitest";
import { MCPMarketplaceCard } from "../mcp-marketplace-card";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";

// Mock lucide-react
vi.mock("lucide-react", () => ({
  ExternalLink: () => <div data-testid="external-link-icon" />,
  Download: () => <div data-testid="download-icon" />,
  Info: () => <div data-testid="info-icon" />,
  Check: () => <div data-testid="check-icon" />,
  Sparkles: () => <div data-testid="sparkles-icon" />,
  TrendingUp: () => <div data-testid="trending-icon" />,
}));

describe("MCPMarketplaceCard", () => {
  const mockMCP: MCPMarketplaceItem = {
    id: "test-mcp-id",
    slug: "test-mcp",
    name: "test-mcp",
    description: "A test MCP server",
    author: "Test Author",
    category: "browser",
    type: "sse",
    config: {},
    icon: "🧪",
    homepage: "https://github.com/test/mcp-server",
    featured: false,
    popular: false,
    installCount: 1500,
    rating: 4.5,
  };

  const defaultProps = {
    mcp: mockMCP,
    isInstalled: false,
    onInstall: vi.fn(),
    onViewDetails: vi.fn(),
  };

  it("should render MCP name and description", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    expect(screen.getByText("test-mcp")).toBeInTheDocument();
    expect(screen.getByText("A test MCP server")).toBeInTheDocument();
  });

  it("should display author information", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    expect(screen.getByText(/by Test Author/)).toBeInTheDocument();
  });

  it("should show install count formatted", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    expect(screen.getByText("1.5k")).toBeInTheDocument();
  });

  it("should format large install counts correctly", () => {
    const popularMCP = { ...mockMCP, installCount: 50000 };
    render(<MCPMarketplaceCard {...defaultProps} mcp={popularMCP} />);

    expect(screen.getByText("50.0k")).toBeInTheDocument();
  });

  it("should display rating", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    expect(screen.getByText("⭐ 4.5")).toBeInTheDocument();
  });

  it("should show featured badge when featured", () => {
    const featuredMCP = { ...mockMCP, featured: true };
    render(<MCPMarketplaceCard {...defaultProps} mcp={featuredMCP} />);

    expect(screen.getByText("Featured")).toBeInTheDocument();
  });

  it("should show popular badge when popular", () => {
    const popularMCP = { ...mockMCP, popular: true };
    render(<MCPMarketplaceCard {...defaultProps} mcp={popularMCP} />);

    expect(screen.getByText("Popular")).toBeInTheDocument();
  });

  it("should show both badges when featured and popular", () => {
    const specialMCP = { ...mockMCP, featured: true, popular: true };
    render(<MCPMarketplaceCard {...defaultProps} mcp={specialMCP} />);

    expect(screen.getByText("Featured")).toBeInTheDocument();
    expect(screen.getByText("Popular")).toBeInTheDocument();
  });

  it("should display category and type tags", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    expect(screen.getByText("browser")).toBeInTheDocument();
    expect(screen.getByText("NPM")).toBeInTheDocument();
  });

  it("should call onInstall when install button is clicked", async () => {
    const user = userEvent.setup();
    render(<MCPMarketplaceCard {...defaultProps} />);

    const installButton = screen.getByRole("button", { name: /Install/i });
    await user.click(installButton);

    expect(defaultProps.onInstall).toHaveBeenCalledWith(mockMCP);
  });

  it("should show installed state when isInstalled is true", () => {
    render(<MCPMarketplaceCard {...defaultProps} isInstalled={true} />);

    const installedButton = screen.getByRole("button", { name: /Installed/i });
    expect(installedButton).toBeDisabled();
    expect(screen.getAllByTestId("check-icon")).toHaveLength(2); // One in button, one as indicator
  });

  it("should call onViewDetails when info button is clicked", async () => {
    const user = userEvent.setup();
    render(<MCPMarketplaceCard {...defaultProps} />);

    const infoButton = screen.getByLabelText("View details");
    await user.click(infoButton);

    expect(defaultProps.onViewDetails).toHaveBeenCalledWith(mockMCP);
  });

  it("should render homepage link when available", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    const homepageLink = screen.getByLabelText("Open homepage");
    expect(homepageLink).toHaveAttribute("href", "https://github.com/test/mcp-server");
    expect(homepageLink).toHaveAttribute("target", "_blank");
  });

  it("should not render homepage link when not available", () => {
    const mcpWithoutHomepage = { ...mockMCP, homepage: undefined };
    render(<MCPMarketplaceCard {...defaultProps} mcp={mcpWithoutHomepage} />);

    expect(screen.queryByLabelText("Open homepage")).not.toBeInTheDocument();
  });

  it("should display icon if provided", () => {
    render(<MCPMarketplaceCard {...defaultProps} />);

    expect(screen.getByText("🧪")).toBeInTheDocument();
  });

  it("should show default icon when icon not provided", () => {
    const mcpWithoutIcon = { ...mockMCP, icon: undefined };
    render(<MCPMarketplaceCard {...defaultProps} mcp={mcpWithoutIcon} />);

    expect(screen.getByText("📦")).toBeInTheDocument();
  });

  it("should apply hover styles", async () => {
    const user = userEvent.setup();
    const { container } = render(<MCPMarketplaceCard {...defaultProps} />);

    const card = container.firstChild as HTMLElement;
    
    await user.hover(card);

    // Check that hover overlay appears
    await waitFor(() => {
      const overlay = container.querySelector(".opacity-100");
      expect(overlay).toBeInTheDocument();
    });
  });
});

