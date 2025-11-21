import React, { useCallback, useMemo, useState } from "react";
import {
  exportDiagramAsSVG,
  exportDiagramAsPNG,
  copyMermaidSource,
  downloadMermaidSource,
} from "#/utils/diagram-export";
import {
  useFullscreenShortcuts,
  useMermaidDiagram,
  useZoomPan,
} from "./hooks/mermaid-viewer-hooks";

interface MermaidDiagramViewerProps {
  diagram: string;
  className?: string;
  onNodeClick?: (nodeId: string) => void;
  showExportButtons?: boolean;
  exportFilename?: string;
  enableFullscreen?: boolean;
  enableZoom?: boolean;
}

type ExportFormat = "svg" | "png" | "source" | "copy";

// Helper functions and components - defined before use
async function performMermaidExport({
  format,
  diagram,
  exportFilename,
  svgElement,
}: {
  format: ExportFormat;
  diagram: string;
  exportFilename: string;
  svgElement: SVGSVGElement | null;
}): Promise<void> {
  const filename = `${exportFilename}.${format === "source" ? "mmd" : format}`;

  switch (format) {
    case "svg":
      if (svgElement) {
        exportDiagramAsSVG(svgElement, filename);
      }
      break;
    case "png":
      if (svgElement) {
        await exportDiagramAsPNG(svgElement, filename);
      }
      break;
    case "source":
      downloadMermaidSource(diagram, filename);
      break;
    case "copy":
      await copyMermaidSource(diagram);
      break;
    default:
      break;
  }
}

function MermaidFullscreenControl({
  icon,
  onClick,
  title,
}: {
  icon: "plus" | "minus" | "reset";
  onClick: () => void;
  title: string;
}) {
  let iconPath: string;
  if (icon === "plus") {
    iconPath = "M12 4v16m8-8H4";
  } else if (icon === "minus") {
    iconPath = "M20 12H4";
  } else {
    iconPath =
      "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15";
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="p-2 rounded bg-white/20 hover:bg-white/30 transition-colors text-white"
      title={title}
      aria-label={title}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d={iconPath}
        />
      </svg>
    </button>
  );
}

function MermaidZoomControls({
  zoom,
  onZoomIn,
  onZoomOut,
  onReset,
}: {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}) {
  return (
    <div className="flex items-center gap-1 bg-white dark:bg-background-tertiary rounded-lg shadow-md px-2 py-1">
      <button
        type="button"
        onClick={onZoomOut}
        className="p-1 hover:bg-background-tertiary rounded transition-colors"
        title="Zoom out (-)"
        aria-label="Zoom out"
      >
        <svg
          className="w-4 h-4 text-foreground-secondary/70 dark:text-foreground-secondary"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20 12H4"
          />
        </svg>
      </button>
      <span className="text-xs font-medium text-foreground-secondary/70 dark:text-foreground-secondary min-w-[3rem] text-center">
        {Math.round(zoom * 100)}%
      </span>
      <button
        type="button"
        onClick={onZoomIn}
        className="p-1 hover:bg-background-tertiary rounded transition-colors"
        title="Zoom in (+)"
        aria-label="Zoom in"
      >
        <svg
          className="w-4 h-4 text-foreground-secondary/70 dark:text-foreground-secondary"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4v16m8-8H4"
          />
        </svg>
      </button>
      <button
        type="button"
        onClick={onReset}
        className="p-1 hover:bg-background-tertiary rounded transition-colors"
        title="Reset (0)"
        aria-label="Reset zoom"
      >
        <svg
          className="w-4 h-4 text-foreground-secondary/70 dark:text-foreground-secondary"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>
  );
}

function MermaidExportDropdown({
  isExporting,
  onClose,
  onExport,
}: {
  isExporting: boolean;
  onClose: () => void;
  onExport: (format: ExportFormat) => Promise<void>;
}) {
  const handleExportClick = async (format: ExportFormat) => {
    await onExport(format);
    onClose();
  };

  const options: Array<{ label: string; format: ExportFormat }> = [
    { label: "Export as SVG", format: "svg" },
    { label: "Export as PNG", format: "png" },
    { label: "Download source", format: "source" },
    { label: "Copy source", format: "copy" },
  ];

  return (
    <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-background-tertiary border border-border rounded-lg shadow-lg z-20">
      {options.map((option) => (
        <button
          key={option.format}
          type="button"
          onClick={() => handleExportClick(option.format)}
          disabled={isExporting}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-foreground-secondary hover:bg-background-tertiary disabled:opacity-50"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function MermaidExportMenu({
  isOpen,
  isExporting,
  onToggle,
  onRequestClose,
  onExport,
}: {
  isOpen: boolean;
  isExporting: boolean;
  onToggle: () => void;
  onRequestClose: () => void;
  onExport: (format: ExportFormat) => Promise<void>;
}) {
  return (
    <div className="relative">
      <button
        type="button"
        onClick={onToggle}
        className="p-2 rounded-lg bg-white dark:bg-background-tertiary shadow-md hover:bg-background-tertiary/80 dark:hover:bg-background-tertiary/70 transition-colors"
        title="Export diagram"
        aria-label="Export diagram"
      >
        <svg
          className="w-4 h-4 text-foreground-secondary"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v6h6M20 20v-6h-6M18.364 5.636L5.636 18.364"
          />
        </svg>
      </button>

      {isOpen && (
        <MermaidExportDropdown
          isExporting={isExporting}
          onClose={onRequestClose}
          onExport={onExport}
        />
      )}
    </div>
  );
}

function MermaidFullscreenOverlay({
  exportFilename,
  cursor,
  transformStyle,
  svg,
  zoom,
  enableZoom,
  onClose,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onZoomIn,
  onZoomOut,
  onReset,
}: {
  exportFilename: string;
  cursor: string;
  transformStyle: React.CSSProperties;
  svg: string | null;
  zoom: number;
  enableZoom: boolean;
  onClose: () => void;
  onMouseDown: (event: React.MouseEvent<HTMLDivElement>) => void;
  onMouseMove: (event: React.MouseEvent<HTMLDivElement>) => void;
  onMouseUp: (event: React.MouseEvent<HTMLDivElement>) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-black/95 backdrop-blur-sm animate-fade-in">
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/80 to-transparent p-4 flex items-center justify-between z-10">
        <div className="text-white">
          <h3 className="text-lg font-semibold">{exportFilename}</h3>
          <p className="text-sm text-foreground-secondary">
            Press ESC to exit fullscreen
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-white"
          title="Exit fullscreen (ESC)"
          aria-label="Exit fullscreen"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <div className="h-full flex items-center justify-center p-8 pt-20">
        <div
          className="max-w-7xl w-full h-full overflow-auto"
          onMouseDown={enableZoom ? onMouseDown : undefined}
          onMouseMove={enableZoom ? onMouseMove : undefined}
          onMouseUp={enableZoom ? onMouseUp : undefined}
          onMouseLeave={enableZoom ? onMouseUp : undefined}
          style={{ cursor }}
        >
          <div style={transformStyle} className="inline-block">
            <div dangerouslySetInnerHTML={{ __html: svg ?? "" }} />
          </div>
        </div>
      </div>

      {enableZoom && (
        <div className="absolute bottom-4 right-4 flex flex-col gap-2 bg-white/10 backdrop-blur rounded-lg p-2">
          <MermaidFullscreenControl
            icon="plus"
            onClick={onZoomIn}
            title="Zoom in (+)"
          />
          <span className="text-white text-sm font-medium text-center px-2">
            {Math.round(zoom * 100)}%
          </span>
          <MermaidFullscreenControl
            icon="minus"
            onClick={onZoomOut}
            title="Zoom out (-)"
          />
          <MermaidFullscreenControl
            icon="reset"
            onClick={onReset}
            title="Reset zoom (0)"
          />
        </div>
      )}
    </div>
  );
}

const buildFallbackContent = ({
  diagram,
  error,
  className,
}: {
  diagram: string;
  error: string | null;
  className: string;
}) => {
  if (!diagram) {
    return (
      <div
        className={`flex items-center justify-center p-8 text-foreground-secondary ${className}`}
      >
        No diagram available
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`flex flex-col items-center justify-center p-8 text-error-500 ${className}`}
      >
        <svg
          className="w-12 h-12 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <p className="text-sm font-medium">Failed to render diagram</p>
        <p className="text-xs mt-2 text-foreground-secondary">{error}</p>
      </div>
    );
  }

  return null;
};

const buildFullscreenOverlay = ({
  enableFullscreen,
  isFullscreen,
  ...overlayProps
}: {
  enableFullscreen: boolean;
  isFullscreen: boolean;
} & React.ComponentProps<typeof MermaidFullscreenOverlay>) => {
  if (!enableFullscreen || !isFullscreen) {
    return null;
  }

  return <MermaidFullscreenOverlay {...overlayProps} />;
};

// Hook that must be called unconditionally
const useDiagramControls = ({
  shouldShowControls,
  enableZoom,
  enableFullscreen,
  showExportButtons,
  zoom,
  zoomIn,
  zoomOut,
  reset,
  enterFullscreen,
  showExportMenu,
  setShowExportMenu,
  isExporting,
  handleExport,
}: {
  shouldShowControls: boolean;
  enableZoom: boolean;
  enableFullscreen: boolean;
  showExportButtons: boolean;
  zoom: number;
  zoomIn: () => void;
  zoomOut: () => void;
  reset: () => void;
  enterFullscreen: () => void;
  showExportMenu: boolean;
  setShowExportMenu: React.Dispatch<React.SetStateAction<boolean>>;
  isExporting: boolean;
  handleExport: (format: ExportFormat) => Promise<void>;
}) =>
  useMemo(() => {
    if (!shouldShowControls) {
      return null;
    }

    return (
      <div className="absolute top-2 right-2 z-10 flex gap-2">
        {enableZoom && (
          <MermaidZoomControls
            zoom={zoom}
            onZoomIn={zoomIn}
            onZoomOut={zoomOut}
            onReset={reset}
          />
        )}

        {enableFullscreen && (
          <button
            type="button"
            onClick={enterFullscreen}
            className="p-2 rounded-lg bg-white dark:bg-background-tertiary shadow-md hover:bg-background-tertiary/80 dark:hover:bg-background-tertiary/70 transition-colors"
            title="Enter fullscreen"
            aria-label="Enter fullscreen"
          >
            <svg
              className="w-4 h-4 text-foreground-secondary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 3H5a2 2 0 00-2 2v3m0 8v3a2 2 0 002 2h3m8 0h3a2 2 0 002-2v-3m0-8V5a2 2 0 00-2-2h-3"
              />
            </svg>
          </button>
        )}

        {showExportButtons && (
          <MermaidExportMenu
            isOpen={showExportMenu}
            isExporting={isExporting}
            onToggle={() => setShowExportMenu((prev) => !prev)}
            onRequestClose={() => setShowExportMenu(false)}
            onExport={handleExport}
          />
        )}
      </div>
    );
  }, [
    shouldShowControls,
    enableZoom,
    zoom,
    zoomIn,
    zoomOut,
    reset,
    enableFullscreen,
    enterFullscreen,
    showExportButtons,
    showExportMenu,
    setShowExportMenu,
    isExporting,
    handleExport,
  ]);

export function MermaidDiagramViewer({
  diagram,
  className = "",
  onNodeClick,
  showExportButtons = true,
  exportFilename = "diagram",
  enableFullscreen = true,
  enableZoom = true,
}: MermaidDiagramViewerProps) {
  const { containerRef, svgRef, svg, error, isRendering } = useMermaidDiagram({
    diagram,
    onNodeClick,
  });

  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const {
    zoom,
    cursor,
    transformStyle,
    zoomIn,
    zoomOut,
    reset,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
  } = useZoomPan({ enabled: enableZoom });

  const enterFullscreen = useCallback(() => {
    setShowExportMenu(false);
    setIsFullscreen(true);
  }, []);
  const exitFullscreen = useCallback(() => {
    setIsFullscreen(false);
    handleMouseUp();
  }, [handleMouseUp]);

  useFullscreenShortcuts({
    enableZoom,
    enableFullscreen,
    isFullscreen,
    zoomIn,
    zoomOut,
    resetZoom: reset,
    enterFullscreen,
    exitFullscreen,
  });

  const handleExport = useCallback(
    async (format: ExportFormat) => {
      setIsExporting(true);
      try {
        const svgElement =
          svgRef.current instanceof SVGSVGElement ? svgRef.current : null;
        await performMermaidExport({
          format,
          diagram,
          exportFilename,
          svgElement,
        });
        setShowExportMenu(false);
      } catch (exportError) {
        console.error("Export failed:", exportError);
      } finally {
        setIsExporting(false);
      }
    },
    [diagram, exportFilename, svgRef],
  );

  // All hooks must be called before any conditional returns
  const shouldShowControls =
    Boolean(svg) && (showExportButtons || enableFullscreen || enableZoom);
  const controls = useDiagramControls({
    shouldShowControls,
    enableZoom,
    enableFullscreen,
    showExportButtons,
    zoom,
    zoomIn,
    zoomOut,
    reset,
    enterFullscreen,
    showExportMenu,
    setShowExportMenu,
    isExporting,
    handleExport,
  });

  const fullscreenOverlay = buildFullscreenOverlay({
    enableFullscreen,
    isFullscreen,
    exportFilename,
    cursor,
    transformStyle,
    svg,
    zoom,
    enableZoom,
    onClose: exitFullscreen,
    onMouseDown: handleMouseDown,
    onMouseMove: handleMouseMove,
    onMouseUp: handleMouseUp,
    onReset: reset,
    onZoomIn: zoomIn,
    onZoomOut: zoomOut,
  });

  // Now we can do conditional returns after all hooks
  const fallbackContent = buildFallbackContent({ diagram, error, className });
  if (fallbackContent) {
    return fallbackContent;
  }

  const zoomHandlers = enableZoom
    ? {
        onMouseDown: handleMouseDown,
        onMouseMove: handleMouseMove,
        onMouseUp: handleMouseUp,
        onMouseLeave: handleMouseUp,
      }
    : {};

  return (
    <>
      <div className="relative">
        {controls}

        <div
          ref={containerRef}
          className={`relative rounded-lg border border-border bg-background-secondary p-4 ${className}`}
          {...zoomHandlers}
          style={{ cursor, overflow: enableZoom ? "hidden" : "visible" }}
        >
          {isRendering && (
            <div className="absolute inset-0 flex items-center justify-center bg-background-secondary/60">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            </div>
          )}

          <div style={transformStyle} className="inline-block">
            <div ref={containerRef} dangerouslySetInnerHTML={{ __html: svg }} />
          </div>
        </div>
      </div>

      {fullscreenOverlay}
    </>
  );
}
