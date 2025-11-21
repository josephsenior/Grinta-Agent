import { useLocation } from "react-router-dom";

export function useSidebarVisibility() {
  const location = useLocation();

  const isConversationPage = location.pathname.startsWith("/conversations/");
  const isLandingPage = location.pathname === "/";
  const isAuthPage = location.pathname.startsWith("/auth/");
  const showSidebar = !isLandingPage && !isConversationPage && !isAuthPage;
  const hasHeader = showSidebar;

  return {
    showSidebar,
    hasHeader,
  };
}
