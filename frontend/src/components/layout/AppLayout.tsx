import React from "react";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  // Sidebar is now handled by the main layout's Sidebar component
  // This component just wraps the content
  return (
    <div className="w-full px-6 py-6">
      <div className="max-w-[1920px] mx-auto">
        {/* Page Content */}
        {children}
      </div>
    </div>
  );
}
