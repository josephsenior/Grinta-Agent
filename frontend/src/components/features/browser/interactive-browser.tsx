import React, { useState, useEffect, useRef } from "react";
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

export function InteractiveBrowser() {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Watch agent's browser URL from Redux
  const agentUrl = useSelector((state: RootState) => state.browser.url);

  // Local state for user's browser
  const [currentUrl, setCurrentUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [corsError, setCorsError] = useState(false);

  // Sync agent's URL to iframe when agent navigates
  useEffect(() => {
    if (agentUrl && agentUrl !== currentUrl) {
      // Check if agent navigated to chrome-error URL - this indicates a navigation failure
      if (agentUrl.includes('chrome-error://') || agentUrl.includes('chromewebdata')) {
        console.log("🚨 Detected chrome-error navigation, this indicates server readiness issue");
        setCorsError(true);
        return;
      }
      
      // Only sync if it's a valid URL
      if (agentUrl.startsWith("http://") || agentUrl.startsWith("https://")) {
        // Convert 0.0.0.0 to localhost for better user experience
        const normalizedUrl = agentUrl.replace(/0\.0\.0\.0/g, "localhost");
        setCurrentUrl(normalizedUrl);
        setCorsError(false);
      }
    }
  }, [agentUrl]);

  // Listen for server-ready events (production-grade auto-navigation from backend)
  useEffect(() => {
    const handleLoadServerUrl = (event: CustomEvent<{ url: string }>) => {
      const { url } = event.detail;
      if (url && (url.startsWith("http://") || url.startsWith("https://"))) {
        const normalizedUrl = url.replace(/0\.0\.0\.0/g, "localhost");
        console.log(`[InteractiveBrowser] Loading server URL: ${normalizedUrl}`);
        setCurrentUrl(normalizedUrl);
        setCorsError(false);
      }
    };

    window.addEventListener(
      "openhands:load-server-url",
      handleLoadServerUrl as EventListener,
    );

    return () => {
      window.removeEventListener(
        "openhands:load-server-url",
        handleLoadServerUrl as EventListener,
      );
    };
  }, []);

  // Check if URL is a localhost application
  const isLocalhostApp = (url: string) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname === 'localhost' || urlObj.hostname === '127.0.0.1';
    } catch {
      return false;
    }
  };

  // Load URL into iframe
  useEffect(() => {
    if (currentUrl && iframeRef.current) {
      setIsLoading(true);
      setCorsError(false);

      // Longer timeout for localhost apps as they might take longer to start
      const timeout = isLocalhostApp(currentUrl) ? 10000 : 5000;
      const loadTimeout = setTimeout(() => {
        setIsLoading(false);
        setCorsError(true);
      }, timeout);

      const handleLoad = () => {
        setIsLoading(false);
        clearTimeout(loadTimeout);
        setCorsError(false);

        // For localhost apps, try to detect if they're actually running
        if (isLocalhostApp(currentUrl)) {
          try {
            const iframeDoc = iframeRef.current?.contentDocument;
            if (iframeDoc) {
              // Check if we got a proper page or an error page
              const body = iframeDoc.body;
              if (body && (body.textContent?.includes('ERR_CONNECTION_REFUSED') || 
                          body.textContent?.includes('This site can\'t be reached'))) {
                setCorsError(true);
              } else {
                setCorsError(false);
              }
            }
          } catch (e) {
            // CORS restriction - but for localhost this might indicate the app isn't running
            setCorsError(true);
          }
        } else {
          // For external sites, CORS restrictions are expected
          try {
            const iframeDoc = iframeRef.current?.contentDocument;
            if (iframeDoc) {
              setCorsError(false);
            }
          } catch (e) {
            // CORS restriction - this is actually expected for most sites
            // We'll show a hint but not treat it as a full error
          }
        }
      };

      const handleError = () => {
        setIsLoading(false);
        clearTimeout(loadTimeout);
        setCorsError(true);
      };

      const iframe = iframeRef.current;
      iframe.addEventListener("load", handleLoad);
      iframe.addEventListener("error", handleError);

      return () => {
        clearTimeout(loadTimeout);
        iframe.removeEventListener("load", handleLoad);
        iframe.removeEventListener("error", handleError);
      };
    }
  }, [currentUrl]);

  const handleRefresh = () => {
    if (iframeRef.current && currentUrl) {
      setIsLoading(true);
      setCorsError(false);
      iframeRef.current.src = currentUrl;
    }
  };

  const handleOpenInNewTab = () => {
    if (currentUrl) {
      window.open(currentUrl, "_blank", "noopener,noreferrer");
    }
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div
      className={cn(
        "h-full w-full flex flex-col bg-background-primary",
        isFullscreen && "fixed inset-0 z-50",
      )}
    >
      {/* Browser Controls - Simplified (Agent-Controlled) */}
      <div className="flex-none bg-background-secondary/95 backdrop-blur-sm border-b border-border/60">
        {/* Simplified Header - No URL Input */}
        <div className="flex items-center gap-3 px-4 py-2.5">
          {/* Agent-Controlled URL Display (Read-Only) */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Globe className="w-4 h-4 text-foreground-secondary flex-shrink-0" />
            <span 
              className="text-sm text-foreground truncate" 
              title={currentUrl || "Agent will navigate here"}
            >
              {currentUrl || "Waiting for agent to build app..."}
            </span>
          </div>
          
          {/* Action Buttons */}
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
        </div>

        {/* CORS/Loading Notice */}
        {corsError && currentUrl && (
          <div className="px-3 pb-2">
            <div className="flex items-center justify-between gap-2 px-3 py-1.5 text-xs bg-error-500/10 border border-error-500/30 rounded-lg text-error-500">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>
                  {agentUrl && (agentUrl.includes('chrome-error://') || agentUrl.includes('chromewebdata'))
                    ? "❌ Navigation failed - server may not be ready. The agent should wait for the server to start before navigating."
                    : isLocalhostApp(currentUrl) 
                      ? "Agent app may not be running or blocked. Click 'Open in new tab' to check."
                      : "This site may block iframe embedding. Click 'Open in new tab' if it doesn't load."
                  }
                </span>
              </div>
              <button
                onClick={handleOpenInNewTab}
                className="px-2 py-1 text-[10px] bg-error-500/20 hover:bg-error-500/30 rounded border border-error-500/40 transition-colors duration-150 flex-shrink-0"
              >
                Open Tab
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Browser Content */}
      <div className="flex-1 min-h-0 relative bg-background-primary">
        {!currentUrl ? (
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
        ) : (
          <>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-background-primary/80 backdrop-blur-sm z-10">
                <div className="flex flex-col items-center gap-3">
                  <RefreshCw className="w-8 h-8 text-violet-500 animate-spin" />
                  <p className="text-sm text-foreground-secondary">Loading page...</p>
                </div>
              </div>
            )}
            <iframe
              ref={iframeRef}
              src={currentUrl}
              title="Interactive Browser"
              className="w-full h-full border-0"
              sandbox={
                isLocalhostApp(currentUrl)
                  ? "allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-presentation allow-top-navigation-by-user-activation allow-downloads allow-modals"
                  : "allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-presentation allow-top-navigation-by-user-activation"
              }
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </>
        )}
      </div>
    </div>
  );
}
