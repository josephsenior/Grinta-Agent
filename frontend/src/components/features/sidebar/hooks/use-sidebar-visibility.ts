import { useLocation } from "react-router-dom";

export function useSidebarVisibility() {
  const location = useLocation();

  const isConversationPage = location.pathname.startsWith("/conversations/");
  const isAuthPage = location.pathname.startsWith("/auth/");
  const showSidebar = !isConversationPage && !isAuthPage;
  const hasHeader = showSidebar;

  return {
    showSidebar,
    hasHeader,
  };
}
