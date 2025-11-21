import { useLocation } from "react-router-dom";

/**
 * Hook to check if the current page is the Terms of Service acceptance page.
 *
 * @returns {boolean} True if the current page is the TOS acceptance page, false otherwise.
 */
export const useIsOnTosPage = (overridePathname?: string): boolean => {
  const location = useLocation();
  const pathname = overridePathname ?? location.pathname;
  return pathname === "/accept-tos";
};
