import React, { useEffect, useRef, useState } from "react";
import DOMPurify from "dompurify";
import EventLogger from "#/utils/event-logger";
import {
  exportDiagramAsSVG,
  exportDiagramAsPNG,
  copyMermaidSource,
  downloadMermaidSource,
} from "#/utils/diagram-export";

interface MermaidDiagramViewerProps {
  diagram: string;
  className?: string;
  onNodeClick?: (nodeId: string) => void;
  showExportButtons?: boolean;
  exportFilename?: string;
  enableFullscreen?: boolean;
  enableZoom?: boolean;
}

// Track if mermaid has been initialized
let mermaidInitialized = false;

// Initialize mermaid lazily to avoid bundling errors
const initializeMermaid = async () => {
  if (mermaidInitialized) return;
  
  try {
    const mermaid = (await import("mermaid")).default;
    
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "strict",  // 🔒 SECURITY: strict mode prevents XSS
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
      themeVariables: {
        primaryColor: "#8b5cf6",
        primaryTextColor: "#e5e7eb",
        primaryBorderColor: "#7c3aed",
        lineColor: "#6b7280",
        secondaryColor: "#1f2937",
        tertiaryColor: "#111827",
        background: "#000000",
        mainBkg: "#1f2937",
        secondBkg: "#374151",
        border1: "#4b5563",
        border2: "#6b7280",
        note: "#374151",
        noteBorder: "#6b7280",
        noteBkg: "#1f2937",
        noteText: "#e5e7eb",
        text: "#e5e7eb",
        critical: "#ef4444",
        done: "#10b981",
        active: "#8b5cf6",
        grid: "#374151",
        nodeBorder: "#6b7280",
        clusterBkg: "#1f2937",
        clusterBorder: "#4b5563",
        titleColor: "#e5e7eb",
        edgeLabelBackground: "#1f2937",
        actorBorder: "#6b7280",
        actorBkg: "#374151",
        actorTextColor: "#e5e7eb",
        actorLineColor: "#6b7280",
        signalColor: "#e5e7eb",
        signalTextColor: "#111827",
        labelBoxBkgColor: "#374151",
        labelBoxBorderColor: "#6b7280",
        labelTextColor: "#e5e7eb",
        loopTextColor: "#e5e7eb",
        activationBorderColor: "#6b7280",
        activationBkgColor: "#374151",
        sequenceNumberColor: "#111827",
      },
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: "basis",
      },
    });
    
    mermaidInitialized = true;
  } catch (error) {
    console.error("Failed to initialize mermaid:", error);
  }
};

export function MermaidDiagramViewer({
  diagram,
  className = "",
  onNodeClick,
  showExportButtons = true,
  exportFilename = "diagram",
  enableFullscreen = true,
  enableZoom = true,
}: MermaidDiagramViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const idRef = useRef<string | null>(null);
  const svgRef = useRef<SVGElement | null>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isRendering, setIsRendering] = useState(true);

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Zoom and Pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!diagram || !containerRef.current) return;

    const renderDiagram = async () => {
      try {
        // Clear previous content
        setSvg("");
        setError(null);
        setIsRendering(true);

        // Initialize mermaid lazily
        await initializeMermaid();
        
        // Dynamic import to avoid module-level initialization errors
        const mermaid = (await import("mermaid")).default;

        // Generate unique ID for this diagram
        // Use a stable id: prefer a preserved ref so re-renders don't change it
        if (!idRef.current) {
          // Derive a stable id once on client and store in the top-level ref
          idRef.current = `mermaid-${Math.random().toString(36).slice(2, 11)}`;
        }
        const id = idRef.current as string;

        // Render the diagram
        const { svg: renderedSvg } = await mermaid.render(id, diagram);

        // 🔒 SECURITY: Sanitize SVG to prevent XSS attacks
        const sanitizedSvg = DOMPurify.sanitize(renderedSvg, {
          USE_PROFILES: { svg: true, svgFilters: true },
          ADD_TAGS: ['foreignObject'],  // Allow mermaid features
          FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],  // Block dangerous tags
          FORBID_ATTR: ['onerror', 'onload', 'onclick']  // Block event handlers
        });

        // Set the sanitized SVG
        setSvg(sanitizedSvg);
        setIsRendering(false);

        // Get SVG element reference for export
        setTimeout(() => {
          const svgElement = containerRef.current?.querySelector("svg");
          if (svgElement) {
            svgRef.current = svgElement;

            // Add click handlers to nodes if callback provided
            if (onNodeClick) {
              const nodes = svgElement.querySelectorAll('[id^="flowchart-"]');
              nodes.forEach((node) => {
                const nodeElement = node as HTMLElement;
                nodeElement.style.cursor = "pointer";
                nodeElement.addEventListener("click", () => {
                  const nodeId = nodeElement.id
                    .replace("flowchart-", "")
                    .replace(/-\d+$/, "");
                  onNodeClick(nodeId);
                });
              });
            }
          }
        }, 100);
      } catch (err) {
        try {
          EventLogger.error("Mermaid rendering error");
        } catch (e) {
          // fallback: intentionally no-op to satisfy lint rules
        }
        setError(
          err instanceof Error ? err.message : "Failed to render diagram",
        );
        setIsRendering(false);
      }
    };

    renderDiagram();
  }, [diagram, onNodeClick]);

  // Zoom handlers
  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.5));
  const handleZoomReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!enableZoom) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return; // Don't interfere with text inputs
      }

      // Zoom shortcuts
      if (e.key === "=" || e.key === "+") {
        e.preventDefault();
        handleZoomIn();
      } else if (e.key === "-") {
        e.preventDefault();
        handleZoomOut();
      } else if (e.key === "0") {
        e.preventDefault();
        handleZoomReset();
      }

      // Fullscreen toggle
      if (e.key === " " && !isFullscreen) {
        e.preventDefault();
        setIsFullscreen(true);
      } else if (e.key === "Escape" && isFullscreen) {
        e.preventDefault();
        setIsFullscreen(false);
      }
    };

    if (enableZoom || enableFullscreen) {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [
    enableZoom,
    enableFullscreen,
    isFullscreen,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
  ]);

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

  const handleExport = async (format: "svg" | "png" | "source" | "copy") => {
    setIsExporting(true);
    try {
      const filename = `${exportFilename}.${format === "source" ? "mmd" : format}`;

      switch (format) {
        case "svg":
          exportDiagramAsSVG(svgRef.current, filename);
          break;
        case "png":
          await exportDiagramAsPNG(
            svgRef.current,
            filename.replace(".png", ".png"),
          );
          break;
        case "source":
          downloadMermaidSource(diagram, filename);
          break;
        case "copy":
          await copyMermaidSource(diagram);
          break;
      }

      setShowExportMenu(false);
    } catch (error) {
      console.error("Export failed:", error);
    } finally {
      setIsExporting(false);
    }
  };

  // Render fullscreen overlay
  const renderFullscreen = () => (
    <div className="fixed inset-0 z-50 bg-black/95 backdrop-blur-sm animate-fade-in">
      {/* Fullscreen Header */}
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/80 to-transparent p-4 flex items-center justify-between z-10">
        <div className="text-white">
          <h3 className="text-lg font-semibold">{exportFilename}</h3>
          <p className="text-sm text-foreground-secondary">Press ESC to exit fullscreen</p>
        </div>
        <button
          onClick={() => setIsFullscreen(false)}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-white"
          title="Exit fullscreen (ESC)"
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

      {/* Fullscreen Content */}
      <div className="h-full flex items-center justify-center p-8 pt-20">
        <div
          className="max-w-7xl w-full h-full overflow-auto"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{
            cursor: isPanning ? "grabbing" : enableZoom ? "grab" : "default",
          }}
        >
          <div
            style={{
              transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
              transformOrigin: "center",
              transition: isPanning ? "none" : "transform 0.2s ease-out",
            }}
            className="inline-block"
          >
            <div dangerouslySetInnerHTML={{ __html: svg }} />
          </div>
        </div>
      </div>

      {/* Fullscreen Controls */}
      {enableZoom && (
        <div className="absolute bottom-4 right-4 flex flex-col gap-2 bg-white/10 backdrop-blur rounded-lg p-2">
          <button
            onClick={handleZoomIn}
            className="p-2 rounded bg-white/20 hover:bg-white/30 transition-colors text-white"
            title="Zoom in (+)"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
          </button>
          <span className="text-white text-sm font-medium text-center px-2">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomOut}
            className="p-2 rounded bg-white/20 hover:bg-white/30 transition-colors text-white"
            title="Zoom out (-)"
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
                d="M20 12H4"
              />
            </svg>
          </button>
          <button
            onClick={handleZoomReset}
            className="p-2 rounded bg-white/20 hover:bg-white/30 transition-colors text-white"
            title="Reset zoom (0)"
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      <div className="relative">
        {/* Controls Bar */}
        {!error &&
          svg &&
          (showExportButtons || enableFullscreen || enableZoom) && (
            <div className="absolute top-2 right-2 z-10 flex gap-2">
              {/* Zoom Controls */}
              {enableZoom && (
                <div className="flex items-center gap-1 bg-white dark:bg-background-tertiary rounded-lg shadow-md px-2 py-1">
                  <button
                    onClick={handleZoomOut}
                    className="p-1 hover:bg-background-tertiary rounded transition-colors"
                    title="Zoom out (-)"
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
                    onClick={handleZoomIn}
                    className="p-1 hover:bg-background-tertiary rounded transition-colors"
                    title="Zoom in (+)"
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
                    onClick={handleZoomReset}
                    className="p-1 hover:bg-background-tertiary rounded transition-colors"
                    title="Reset (0)"
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
              )}

              {/* Fullscreen Button */}
              {enableFullscreen && (
                <button
                  onClick={() => setIsFullscreen(true)}
                  className="p-2 bg-background-tertiary rounded-lg shadow-md hover:bg-background-tertiary/70 transition-colors"
                  title="Fullscreen (Space)"
                >
                  <svg
                    className="w-5 h-5 text-foreground-secondary/70 dark:text-foreground-secondary"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                    />
                  </svg>
                </button>
              )}

              {/* Export Button */}
              {showExportButtons && (
                <div className="relative">
                  <button
                    onClick={() => setShowExportMenu(!showExportMenu)}
                    className="p-2 bg-background-tertiary rounded-lg shadow-md hover:bg-background-tertiary/70 transition-colors"
                    title="Export diagram (E)"
                  >
                    <svg
                      className="w-5 h-5 text-foreground-secondary/70 dark:text-foreground-secondary"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>

                  {/* Export Menu */}
                  {showExportMenu && (
                    <div className="absolute top-12 right-0 w-48 bg-white dark:bg-background-tertiary rounded-lg shadow-xl border border-border dark:border-border overflow-hidden animate-scale-in">
                      <button
                        onClick={() => handleExport("png")}
                        disabled={isExporting}
                        className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background-tertiary transition-colors"
                      >
                        Export as PNG
                      </button>
                      <button
                        onClick={() => handleExport("svg")}
                        disabled={isExporting}
                        className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background-tertiary transition-colors"
                      >
                        Export as SVG
                      </button>
                      <button
                        onClick={() => handleExport("source")}
                        disabled={isExporting}
                        className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background-tertiary transition-colors"
                      >
                        Download Source
                      </button>
                      <button
                        onClick={() => handleExport("copy")}
                        disabled={isExporting}
                        className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background-tertiary transition-colors border-t border-border dark:border-border"
                      >
                        Copy Source
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        {/* Loading Skeleton */}
        {isRendering && !error && (
          <div className="animate-pulse p-4 bg-white dark:bg-background-secondary rounded-lg">
            <div className="h-64 bg-background-tertiary rounded mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-background-tertiary rounded w-3/4" />
              <div className="h-4 bg-background-tertiary rounded w-1/2" />
            </div>
          </div>
        )}

        {/* Diagram Container with Zoom/Pan */}
        {!isRendering && (
          <div
            ref={containerRef}
            className={`mermaid-diagram-container overflow-auto p-4 bg-white dark:bg-background-secondary rounded-lg transition-opacity duration-300 ${className}`}
            onMouseDown={enableZoom ? handleMouseDown : undefined}
            onMouseMove={enableZoom ? handleMouseMove : undefined}
            onMouseUp={enableZoom ? handleMouseUp : undefined}
            onMouseLeave={enableZoom ? handleMouseUp : undefined}
            style={{
              cursor: isPanning ? "grabbing" : enableZoom ? "grab" : "default",
              touchAction: "none",
            }}
          >
            <div
              style={{
                transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
                transformOrigin: "center",
                transition: isPanning ? "none" : "transform 0.2s ease-out",
              }}
              className="inline-block"
              dangerouslySetInnerHTML={{ __html: svg }}
            />
          </div>
        )}
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && renderFullscreen()}
    </>
  );
}
