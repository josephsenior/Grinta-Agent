import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AutonomyModeSelector } from "#/components/features/controls/autonomy-mode-selector";

describe("AutonomyModeSelector", () => {
  const mockOnModeChange = jest.fn();

  beforeEach(() => {
    mockOnModeChange.mockClear();
  });

  const renderWithRouter = (component: React.ReactElement) =>
    render(<BrowserRouter>{component}</BrowserRouter>);

  it("renders the current mode correctly", () => {
    renderWithRouter(
      <AutonomyModeSelector
        currentMode="balanced"
        onModeChange={mockOnModeChange}
      />,
    );

    expect(screen.getByText("Balanced")).toBeInTheDocument();
  });

  it("opens dropdown when clicked", () => {
    renderWithRouter(
      <AutonomyModeSelector
        currentMode="balanced"
        onModeChange={mockOnModeChange}
      />,
    );

    const button = screen.getByRole("button");
    fireEvent.click(button);

    expect(screen.getByText("Autonomy Mode")).toBeInTheDocument();
    expect(screen.getByText("Supervised")).toBeInTheDocument();
    expect(screen.getByText("Full Autonomous")).toBeInTheDocument();
  });

  it("calls onModeChange when a different mode is selected", () => {
    renderWithRouter(
      <AutonomyModeSelector
        currentMode="balanced"
        onModeChange={mockOnModeChange}
      />,
    );

    // Open dropdown
    const button = screen.getByRole("button");
    fireEvent.click(button);

    // Select supervised mode
    const supervisedButton = screen.getByText("Supervised");
    fireEvent.click(supervisedButton);

    expect(mockOnModeChange).toHaveBeenCalledWith("supervised");
  });

  it("closes dropdown when backdrop is clicked", async () => {
    renderWithRouter(
      <AutonomyModeSelector
        currentMode="balanced"
        onModeChange={mockOnModeChange}
      />,
    );

    // Open dropdown
    const button = screen.getByRole("button");
    fireEvent.click(button);

    // Should show dropdown content
    expect(screen.getByText("Autonomy Mode")).toBeInTheDocument();

    // Click backdrop
    await new Promise((resolve) => setTimeout(resolve, 0));
    fireEvent.click(document.body);

    await new Promise((resolve) => setTimeout(resolve, 0));

    await waitFor(() => {
      expect(screen.queryByText("Autonomy Mode")).not.toBeInTheDocument();
    });
  });

  it("shows correct icons for each mode", () => {
    renderWithRouter(
      <AutonomyModeSelector
        currentMode="balanced"
        onModeChange={mockOnModeChange}
      />,
    );

    // Open dropdown
    const button = screen.getByRole("button");
    fireEvent.click(button);

    // Check that icons are present (they have specific classes)
    expect(document.querySelector(".text-orange-500")).toBeInTheDocument(); // Supervised
    expect(document.querySelector(".text-blue-500")).toBeInTheDocument(); // Balanced
    expect(document.querySelector(".text-green-500")).toBeInTheDocument(); // Full
  });

  it("shows selected indicator for current mode", () => {
    renderWithRouter(
      <AutonomyModeSelector
        currentMode="full"
        onModeChange={mockOnModeChange}
      />,
    );

    // Open dropdown
    const button = screen.getByRole("button");
    fireEvent.click(button);

    // Check that the selected mode has the indicator dot
    const selectedIndicator = document.querySelector(".bg-brand-500");
    expect(selectedIndicator).toBeInTheDocument();
  });
});
