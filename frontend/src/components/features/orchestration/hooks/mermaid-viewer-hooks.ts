import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DOMPurify from "dompurify";
import EventLogger from "#/utils/event-logger";
import { ensureMermaid } from "../mermaid-helpers";
import { logger } from "#/utils/logger";

interface UseMermaidDiagramOptions {
  diagram: string;
  onNodeClick?: (nodeId: string) => void;
}

interface UseMermaidDiagramResult {
  containerRef: React.RefObject<HTMLDivElement | null>;
  svgRef: React.MutableRefObject<SVGElement | null>;
  svg: string;
  error: string | null;
  isRendering: boolean;
}

const SANITIZE_OPTIONS = {
  USE_PROFILES: { svg: true, svgFilters: true },
  ADD_TAGS: ["foreignObject"] as string[],
  FORBID_TAGS: ["script", "iframe", "object", "embed"] as string[],
  FORBID_ATTR: ["onerror", "onload", "onclick"] as string[],
};

export function useMermaidDiagram({
  diagram,
  onNodeClick,
}: UseMermaidDiagramOptions): UseMermaidDiagramResult {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGElement | null>(null);
  const idRef = useRef<string>(
    `mermaid-${Math.random().toString(36).slice(2, 11)}`,
  );
  const listenersRef = useRef<Array<() => void>>([]);

  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);

  const cleanupListeners = useCallback(() => {
    listenersRef.current.forEach((cleanup) => cleanup());
    listenersRef.current = [];
  }, []);

  const resetRenderingState = useCallback(() => {
    setSvg("");
    setError(null);
    setIsRendering(false);
  }, []);

  const logMermaidError = useCallback(() => {
    try {
      EventLogger.error("Mermaid rendering error");
    } catch (eventLoggerError) {
      logger.warn("Mermaid rendering failed", eventLoggerError);
    }
  }, []);

  const attachNodeClickHandlers = useCallback(
    (svgElement: SVGElement | null) => {
      if (!svgElement || !onNodeClick) {
        return;
      }

      const nodes = svgElement.querySelectorAll('[id^="flowchart-"]');
      nodes.forEach((node) => {
        const element = node as HTMLElement;
        element.style.cursor = "pointer";
        const handler = () => {
          const nodeId = element.id
            .replace("flowchart-", "")
            .replace(/-\d+$/, "");
          onNodeClick(nodeId);
        };
        element.addEventListener("click", handler);
        listenersRef.current.push(() =>
          element.removeEventListener("click", handler),
        );
      });
    },
    [onNodeClick],
  );

  useEffect(() => {
    cleanupListeners();
  }, [diagram, onNodeClick, cleanupListeners]);

  useEffect(() => {
    if (!diagram) {
      resetRenderingState();
      return undefined;
    }

    let isCancelled = false;

    const render = async () => {
      try {
        setIsRendering(true);
        setError(null);
        setSvg("");

        const mermaid = await ensureMermaid();
        const { svg: rendered } = await mermaid.render(idRef.current, diagram);
        if (isCancelled) return;

        const sanitized = DOMPurify.sanitize(rendered, SANITIZE_OPTIONS);
        setSvg(sanitized);
        setIsRendering(false);

        requestAnimationFrame(() => {
          if (isCancelled) {
            return;
          }
          const svgElement = containerRef.current?.querySelector("svg") ?? null;
          svgRef.current = svgElement;

          attachNodeClickHandlers(svgElement);
        });
      } catch (err) {
        if (!isCancelled) {
          logMermaidError();
          setError(
            err instanceof Error ? err.message : "Failed to render diagram",
          );
          setIsRendering(false);
        }
      }
    };

    render();

    return () => {
      isCancelled = true;
      cleanupListeners();
    };
  }, [
    attachNodeClickHandlers,
    cleanupListeners,
    diagram,
    logMermaidError,
    resetRenderingState,
  ]);

  return { containerRef, svgRef, svg, error, isRendering };
}

interface ZoomPanOptions {
  enabled: boolean;
}

interface ZoomPanResult {
  zoom: number;
  pan: { x: number; y: number };
  isPanning: boolean;
  zoomIn: () => void;
  zoomOut: () => void;
  reset: () => void;
  handleMouseDown: (event: React.MouseEvent) => void;
  handleMouseMove: (event: React.MouseEvent) => void;
  handleMouseUp: () => void;
  cursor: string;
  transformStyle: React.CSSProperties;
}

export function useZoomPan({ enabled }: ZoomPanOptions): ZoomPanResult {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });

  const clampZoom = useCallback(
    (value: number) => Math.min(Math.max(value, 0.5), 3),
    [],
  );

  const zoomIn = useCallback(() => {
    if (!enabled) return;
    setZoom((value) => clampZoom(value + 0.2));
  }, [enabled, clampZoom]);

  const zoomOut = useCallback(() => {
    if (!enabled) return;
    setZoom((value) => clampZoom(value - 0.2));
  }, [enabled, clampZoom]);

  const reset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const handleMouseDown = useCallback(
    (event: React.MouseEvent) => {
      if (!enabled) return;
      setIsPanning(true);
      panStart.current = { x: event.clientX, y: event.clientY };
    },
    [enabled],
  );

  const handleMouseMove = useCallback(
    (event: React.MouseEvent) => {
      if (!enabled || !isPanning) return;
      setPan((previous) => {
        const dx = event.clientX - panStart.current.x;
        const dy = event.clientY - panStart.current.y;
        panStart.current = { x: event.clientX, y: event.clientY };
        return { x: previous.x + dx, y: previous.y + dy };
      });
    },
    [enabled, isPanning],
  );

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  const transformStyle = useMemo<React.CSSProperties>(
    () => ({
      transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
      transformOrigin: "center",
      transition: isPanning ? "none" : "transform 0.2s ease-out",
    }),
    [zoom, pan.x, pan.y, isPanning],
  );

  return {
    zoom,
    pan,
    isPanning,
    zoomIn,
    zoomOut,
    reset,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    cursor: (() => {
      if (isPanning) return "grabbing";
      if (enabled) return "grab";
      return "default";
    })(),
    transformStyle,
  };
}

interface FullscreenShortcutsOptions {
  enableZoom: boolean;
  enableFullscreen: boolean;
  isFullscreen: boolean;
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
  enterFullscreen: () => void;
  exitFullscreen: () => void;
}

// Helper functions - defined before use
function shouldIgnoreKeyboardTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement
  );
}

function processZoomShortcut(
  event: KeyboardEvent,
  actions: { zoomIn: () => void; zoomOut: () => void; resetZoom: () => void },
): boolean {
  switch (event.key) {
    case "=":
    case "+":
      event.preventDefault();
      actions.zoomIn();
      return true;
    case "-":
      event.preventDefault();
      actions.zoomOut();
      return true;
    case "0":
      event.preventDefault();
      actions.resetZoom();
      return true;
    default:
      return false;
  }
}

function processFullscreenShortcut(
  event: KeyboardEvent,
  options: {
    isFullscreen: boolean;
    enterFullscreen: () => void;
    exitFullscreen: () => void;
  },
): void {
  if (event.key === " " && !options.isFullscreen) {
    event.preventDefault();
    options.enterFullscreen();
  } else if (event.key === "Escape" && options.isFullscreen) {
    event.preventDefault();
    options.exitFullscreen();
  }
}

export function useFullscreenShortcuts({
  enableZoom,
  enableFullscreen,
  isFullscreen,
  zoomIn,
  zoomOut,
  resetZoom,
  enterFullscreen,
  exitFullscreen,
}: FullscreenShortcutsOptions): void {
  const zoomHandlers = useMemo(
    () => ({ zoomIn, zoomOut, resetZoom }),
    [zoomIn, zoomOut, resetZoom],
  );

  useEffect(() => {
    if (!enableZoom && !enableFullscreen) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (shouldIgnoreKeyboardTarget(event.target)) {
        return;
      }

      if (enableZoom && processZoomShortcut(event, zoomHandlers)) {
        return;
      }

      if (enableFullscreen) {
        processFullscreenShortcut(event, {
          isFullscreen,
          enterFullscreen,
          exitFullscreen,
        });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    enableZoom,
    enableFullscreen,
    isFullscreen,
    zoomHandlers,
    enterFullscreen,
    exitFullscreen,
  ]);
}
