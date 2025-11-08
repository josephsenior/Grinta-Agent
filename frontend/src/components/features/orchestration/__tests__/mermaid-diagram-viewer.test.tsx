import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MermaidDiagramViewer } from "../mermaid-diagram-viewer";

const useMermaidDiagramMock = vi.fn();
const useZoomPanMock = vi.fn();
const useFullscreenShortcutsMock = vi.fn();

vi.mock("../hooks/mermaid-viewer-hooks", () => ({
  useMermaidDiagram: (...args: unknown[]) => useMermaidDiagramMock(...args),
  useZoomPan: (...args: unknown[]) => useZoomPanMock(...args),
  useFullscreenShortcuts: (...args: unknown[]) => useFullscreenShortcutsMock(...args),
}));

const baseZoomPan = {
  zoom: 100,
  cursor: "default",
  transformStyle: {},
  zoomIn: vi.fn(),
  zoomOut: vi.fn(),
  reset: vi.fn(),
  handleMouseDown: vi.fn(),
  handleMouseMove: vi.fn(),
  handleMouseUp: vi.fn(),
};

const baseDiagramState = {
  containerRef: { current: null } as React.RefObject<HTMLDivElement>,
  svgRef: { current: null } as React.MutableRefObject<SVGElement | null>,
  svg: "<svg></svg>",
  error: null as string | null,
  isRendering: false,
};

describe("MermaidDiagramViewer", () => {
  afterEach(() => {
    cleanup();
    vi.resetAllMocks();
  });

  it("renders placeholder when diagram is missing", () => {
    useMermaidDiagramMock.mockReturnValue({ ...baseDiagramState, svg: "" });
    useZoomPanMock.mockReturnValue(baseZoomPan);

    render(<MermaidDiagramViewer diagram="" />);
    expect(screen.getByText(/No diagram available/i)).toBeInTheDocument();
  });

  it("renders error state when mermaid fails", () => {
    useMermaidDiagramMock.mockReturnValue({
      ...baseDiagramState,
      error: "Boom!",
    });
    useZoomPanMock.mockReturnValue(baseZoomPan);

    render(<MermaidDiagramViewer diagram="graph TD; A-->B;" />);
    expect(screen.getByText(/Failed to render diagram/i)).toBeInTheDocument();
    expect(screen.getByText(/Boom!/i)).toBeInTheDocument();
  });

  it("shows controls when diagram is ready", () => {
    useMermaidDiagramMock.mockReturnValue(baseDiagramState);
    useZoomPanMock.mockReturnValue(baseZoomPan);

    render(<MermaidDiagramViewer diagram="graph TD; A-->B;" />);

    expect(screen.getByTitle(/Zoom in/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Fullscreen/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Export diagram/i)).toBeInTheDocument();
  });
});


