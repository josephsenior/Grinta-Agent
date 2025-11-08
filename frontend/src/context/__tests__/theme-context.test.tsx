import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect, beforeEach, afterEach } from "vitest";
import { ThemeProvider, useTheme } from "../theme-context";

// Test component that uses the theme context
function TestComponent() {
  const { theme, setTheme } = useTheme();
  
  return (
    <div>
      <div data-testid="current-theme">{theme}</div>
      <button onClick={() => setTheme("light")} data-testid="set-light">
        Light
      </button>
      <button onClick={() => setTheme("dark")} data-testid="set-dark">
        Dark
      </button>
      <button onClick={() => setTheme("system")} data-testid="set-system">
        System
      </button>
    </div>
  );
}

describe("ThemeContext", () => {
  let mockMatchMedia: ReturnType<typeof vi.fn>;
  let localStorageMock: { [key: string]: string };
  
  beforeEach(() => {
    // Mock localStorage
    localStorageMock = {};
    
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn((key: string) => localStorageMock[key] || null),
        setItem: vi.fn((key: string, value: string) => {
          localStorageMock[key] = value;
        }),
        removeItem: vi.fn((key: string) => {
          delete localStorageMock[key];
        }),
        clear: vi.fn(() => {
          localStorageMock = {};
        }),
      },
      writable: true,
    });
    
    // Mock matchMedia
    mockMatchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-color-scheme: dark)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: mockMatchMedia,
    });
  });
  
  afterEach(() => {
    vi.restoreAllMocks();
  });
  
  it("should default to dark theme", () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    // Default is "dark" per ThemeProvider implementation
    expect(screen.getByTestId("current-theme")).toHaveTextContent("dark");
  });
  
  it("should load theme from localStorage", () => {
    localStorageMock["Forge-theme-preference"] = "light";
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    expect(screen.getByTestId("current-theme")).toHaveTextContent("light");
  });
  
  it("should change theme when setTheme is called", async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    // Initial theme is dark by default
    expect(screen.getByTestId("current-theme")).toHaveTextContent("dark");
    
    // Click light theme button
    await user.click(screen.getByTestId("set-light"));
    
    await waitFor(() => {
      expect(screen.getByTestId("current-theme")).toHaveTextContent("light");
    });
  });
  
  it("should save theme to localStorage", async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    await user.click(screen.getByTestId("set-dark"));
    
    await waitFor(() => {
      expect(localStorage.setItem).toHaveBeenCalledWith("Forge-theme-preference", "dark");
    });
  });
  
  it("should apply dark class to root element", async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    await user.click(screen.getByTestId("set-dark"));
    
    await waitFor(() => {
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });
  });
  
  it("should apply light class to root element", async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    await user.click(screen.getByTestId("set-light"));
    
    await waitFor(() => {
      expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    });
  });
  
  it("should detect system theme when set to system", async () => {
    const user = userEvent.setup();
    
    // Mock system prefers dark
    mockMatchMedia.mockImplementation((query: string) => ({
      matches: query === "(prefers-color-scheme: dark)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    await user.click(screen.getByTestId("set-system"));
    
    await waitFor(() => {
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });
  });
  
  it("should switch all themes correctly", async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    // Start with dark (default)
    expect(screen.getByTestId("current-theme")).toHaveTextContent("dark");
    
    // Switch to light
    await user.click(screen.getByTestId("set-light"));
    await waitFor(() => {
      expect(screen.getByTestId("current-theme")).toHaveTextContent("light");
      expect(localStorage.setItem).toHaveBeenCalledWith("Forge-theme-preference", "light");
    });
    
    // Switch to system
    await user.click(screen.getByTestId("set-system"));
    await waitFor(() => {
      expect(screen.getByTestId("current-theme")).toHaveTextContent("system");
      expect(localStorage.setItem).toHaveBeenCalledWith("Forge-theme-preference", "system");
    });
    
    // Switch back to dark
    await user.click(screen.getByTestId("set-dark"));
    await waitFor(() => {
      expect(screen.getByTestId("current-theme")).toHaveTextContent("dark");
      expect(localStorage.setItem).toHaveBeenCalledWith("Forge-theme-preference", "dark");
    });
  });
  
  it("should throw error when useTheme is called outside ThemeProvider", () => {
    // Suppress console.error for this test
    const originalError = console.error;
    console.error = vi.fn();
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow("useTheme must be used within a ThemeProvider");
    
    console.error = originalError;
  });
});

