import React, { lazy, Suspense } from "react";
import { useLocation } from "react-router-dom";
import { LoadingSpinner } from "../shared/loading-spinner";

// Lazy load all tab components
const EditorTab = lazy(() => import("#/routes/workspace-tab"));
const TerminalTab = lazy(() => import("#/routes/terminal-tab"));
const BrowserTab = lazy(() => import("#/routes/browser-tab"));

interface TabContentProps {
  conversationPath: string;
}

export function TabContent({ conversationPath }: TabContentProps) {
  const location = useLocation();
  const currentPath = location.pathname;

  // Determine which tab is active based on the current path
  const isEditorActive = currentPath === conversationPath;
  const isTerminalActive = currentPath === `${conversationPath}/terminal`;
  const isBrowserActive = currentPath === `${conversationPath}/browser`;

  return (
    <div className="h-full w-full relative">
      {/* Each tab content is always loaded but only visible when active */}
      <Suspense
        fallback={
          <div className="flex items-center justify-center h-full">
            <LoadingSpinner size="large" />
          </div>
        }
      >
        <div
          className={`absolute inset-0 ${isEditorActive ? "block" : "hidden"}`}
        >
          <EditorTab />
        </div>
        <div
          className={`absolute inset-0 ${isTerminalActive ? "block" : "hidden"}`}
        >
          <TerminalTab />
        </div>
        <div
          className={`absolute inset-0 ${isBrowserActive ? "block" : "hidden"}`}
        >
          <BrowserTab />
        </div>
      </Suspense>
    </div>
  );
}
