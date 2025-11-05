import React, { Suspense, lazy } from "react";

// Lazy load route components
const Home = lazy(() => import("../routes/home"));
const Conversation = lazy(() => import("../routes/conversation"));
const Settings = lazy(() => import("../routes/settings"));

// Loading component for routes
function RouteLoading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-border border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-foreground-secondary/70">Loading...</p>
      </div>
    </div>
  );
}

// Route wrapper with lazy loading
export const LazyRoute: React.FC<{ route: string }> = ({ route }) => {
  const renderRoute = () => {
    switch (route) {
      case "home":
        return <Home />;
      case "conversation":
        return <Conversation />;
      case "settings":
        return <Settings />;
      default:
        return <Home />;
    }
  };

  return <Suspense fallback={<RouteLoading />}>{renderRoute()}</Suspense>;
};
