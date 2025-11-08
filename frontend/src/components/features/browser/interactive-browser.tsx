import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useSelector } from "react-redux";
import {
  Globe,
  RefreshCw,
  Maximize2,
  Minimize2,
  ExternalLink,
  AlertCircle,
} from "lucide-react";
import { RootState } from "#/store";
import { cn } from "#/utils/utils";

type InteractiveBrowserController = {
  iframeRef: React.RefObject<HTMLIFrameElement>;
  currentUrl: string;
  isLoading: boolean;
  isFullscreen: boolean;
  corsError: boolean;
  agentUrl: string | null;
  toggleFullscreen: () => void;
  handleRefresh: () => void;
  handleOpenInNewTab: () => void;
  isLocalhostApp: (url: string) => boolean;
};

export function InteractiveBrowser() {
  const controller = useInteractiveBrowserController();

  return (
    <div
      className={cn(
        "h-full w-full flex flex-col bg-background-primary",
        controller.isFullscreen && "fixed inset-0 z-50",
      )}
    >
      <BrowserHeader controller={controller} />
      <BrowserContent controller={controller} />
    </div>
  );
}

function BrowserHeader({ controller }: { controller: InteractiveBrowserController }) {
  return (
    <div className="flex-none bg-background-secondary/95 backdrop-blur-sm border-b border-border/60">
      <HeaderControls controller={controller} />
      <HeaderNotice controller={controller} />
    </div>
  );
}

function HeaderControls({ controller }: { controller: InteractiveBrowserController }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <ReadOnlyUrlDisplay url={controller.currentUrl} />
      <HeaderActionButtons controller={controller} />
    </div>
  );
}

function HeaderActionButtons({ controller }: { controller: InteractiveBrowserController }) {
  const { currentUrl, isLoading, handleRefresh, handleOpenInNewTab, toggleFullscreen, isFullscreen } = controller;

  return (
    <div className="flex items-center gap-1 flex-shrink-0">
      {/* Refresh */}
      <button
        onClick={handleRefresh}
        disabled={!currentUrl}
        className={cn(
          "p-2 rounded-lg transition-all duration-150",
          currentUrl
            ? "text-foreground-secondary hover:text-violet-500 hover:bg-background-tertiary/60"
            : "text-foreground-secondary/50 cursor-not-allowed"
        )}
        title="Refresh preview"
        aria-label="Refresh"
      >
        <RefreshCw
          className={cn("w-4 h-4", isLoading && "animate-spin")}
        />
      </button>

      {/* Open in New Tab */}
      <button
        onClick={handleOpenInNewTab}
        disabled={!currentUrl}
        className={cn(
          "p-2 rounded-lg transition-all duration-150",
          currentUrl
            ? "text-foreground-secondary hover:text-accent-emerald hover:bg-background-tertiary/60"
            : "text-foreground-secondary/50 cursor-not-allowed",
        )}
        title="Open in new tab"
        aria-label="Open in new tab"
      >
        <ExternalLink className="w-4 h-4" />
      </button>

      {/* Fullscreen */}
      <button
        onClick={toggleFullscreen}
        className="p-2 rounded-lg text-foreground-secondary hover:text-accent-sapphire hover:bg-background-tertiary/60 transition-all duration-150"
        title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
        aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
      >
        {isFullscreen ? (
          <Minimize2 className="w-4 h-4" />
        ) : (
          <Maximize2 className="w-4 h-4" />
        )}
      </button>
    </div>
  );
}

function HeaderNotice({ controller }: { controller: InteractiveBrowserController }) {
  const { currentUrl, corsError, agentUrl } = controller;

  return (
    <div className="px-3 pb-2">
      {corsError && currentUrl && (
        <div className="flex items-center justify-between gap-2 px-3 py-1.5 text-xs bg-error-500/10 border border-error-500/30 rounded-lg text-error-500">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              {agentUrl && (agentUrl.includes('chrome-error://') || agentUrl.includes('chromewebdata'))
                ? "❌ Navigation failed - server may not be ready. The agent should wait for the server to start before navigating."
                : controller.isLocalhostApp(currentUrl)
                  ? "Agent app may not be running or blocked. Click 'Open in new tab' to check."
                  : "This site may block iframe embedding. Click 'Open in new tab' if it doesn't load."
              }
            </span>
          </div>
          <button
            onClick={controller.handleOpenInNewTab}
            className="px-2 py-1 text-[10px] bg-error-500/20 hover:bg-error-500/30 rounded border border-error-500/40 transition-colors duration-150 flex-shrink-0"
          >
            Open Tab
          </button>
        </div>
      )}
    </div>
  );
}

function ReadOnlyUrlDisplay({ url }: { url: string }) {
  return (
    <div className="flex items-center gap-2 flex-1 min-w-0">
      <Globe className="w-4 h-4 text-foreground-secondary flex-shrink-0" />
      <span
        className="text-sm text-foreground truncate"
        title={url || "Agent will navigate here"}
      >
        {url || "Waiting for agent to build app..."}
      </span>
    </div>
  );
}

function BrowserContent({ controller }: { controller: InteractiveBrowserController }) {
  if (!controller.currentUrl) {
    return <WaitingForAgent />;
  }

  return (
    <div className="flex-1 min-h-0 relative bg-background-primary">
      <BrowserIframe controller={controller} />
    </div>
  );
}

function WaitingForAgent() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-foreground-secondary p-8">
      <Globe className="w-16 h-16 mb-4 text-foreground-secondary/50" />
      <h3 className="text-lg font-medium text-foreground mb-2">
        App Preview
      </h3>
      <p className="text-sm text-center max-w-md text-foreground-secondary">
        The agent will navigate here when building your app.
        You'll be able to interact with it in real-time!
      </p>
    </div>
  );
}

function LoadingOverlay() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-background-primary/80 backdrop-blur-sm z-10">
      <div className="flex flex-col items-center gap-3">
        <RefreshCw className="w-8 h-8 text-violet-500 animate-spin" />
        <p className="text-sm text-foreground-secondary">Loading page...</p>
      </div>
    </div>
  );
}

function BrowserIframe({ controller }: { controller: InteractiveBrowserController }) {
  const sandbox = controller.isLocalhostApp(controller.currentUrl)
    ? "allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-presentation allow-top-navigation-by-user-activation allow-downloads allow-modals"
    : "allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-presentation allow-top-navigation-by-user-activation";

  return (
    <>
      {controller.isLoading && <LoadingOverlay />}
      <iframe
        ref={controller.iframeRef}
        src={controller.currentUrl}
        title="Interactive Browser"
        className="w-full h-full border-0"
        sandbox={sandbox}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        referrerPolicy="no-referrer-when-downgrade"
      />
    </>
  );
}
