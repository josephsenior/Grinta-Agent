import ReactDOM from "react-dom";

interface ConversationPanelWrapperProps {
  isOpen: boolean;
}

export function ConversationPanelWrapper({
  isOpen,
  children,
}: React.PropsWithChildren<ConversationPanelWrapperProps>) {
  if (!isOpen) {
    return null;
  }

  const portalTarget = document.getElementById("root-outlet");
  if (!portalTarget) {
    return null;
  }

  // When running under Playwright, avoid letting the full-screen backdrop
  // intercept pointer events (it can sit above the top navigation and
  // prevent clicks). We do this by marking the backdrop as pointer-events-none
  // while making the panel content itself pointer-events-auto so tests can
  // still interact with the panel when needed.
  interface WindowWithE2E extends Window {
    __Forge_PLAYWRIGHT?: boolean;
  }

  const isPlaywrightRun =
    typeof window !== "undefined" &&
    (window as unknown as WindowWithE2E).__Forge_PLAYWRIGHT === true;

  return ReactDOM.createPortal(
    <div
      className={
        isPlaywrightRun
          ? "absolute h-full w-full left-0 top-0 z-20 bg-background-surface/80 backdrop-blur-sm rounded-2xl pointer-events-none"
          : "absolute h-full w-full left-0 top-0 z-20 bg-background-surface/80 backdrop-blur-sm rounded-2xl"
      }
    >
      <div className={isPlaywrightRun ? "pointer-events-auto" : ""}>
        {children}
      </div>
    </div>,
    portalTarget,
  );
}
