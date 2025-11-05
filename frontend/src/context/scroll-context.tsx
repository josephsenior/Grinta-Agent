import React, { createContext, useContext, ReactNode, RefObject } from "react";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";

interface ScrollContextType {
  scrollRef: RefObject<HTMLDivElement | null>;
  autoScroll: boolean;
  setAutoScroll: (value: boolean) => void;
  scrollDomToBottom: () => void;
  hitBottom: boolean;
  setHitBottom: (value: boolean) => void;
  onChatBodyScroll: (e: HTMLElement) => void;
}

export const ScrollContext = createContext<ScrollContextType | undefined>(
  undefined,
);

interface ScrollProviderProps {
  children: ReactNode;
  value?: ScrollContextType;
}

export function ScrollProvider({ children, value }: ScrollProviderProps) {
  const scrollHook = useScrollToBottom(React.useRef<HTMLDivElement>(null));

  // Use provided value or default to the hook
  const contextValue = value || scrollHook;

  return (
    <ScrollContext.Provider value={contextValue}>
      {children}
    </ScrollContext.Provider>
  );
}

export function useScrollContext() {
  const context = useContext(ScrollContext);
  if (context === undefined) {
    // Return a default context instead of throwing an error
    // This prevents crashes when the component is rendered outside ScrollProvider
    return {
      scrollRef: { current: null },
      autoScroll: true,
      setAutoScroll: () => {},
      scrollDomToBottom: () => {},
      hitBottom: true,
      setHitBottom: () => {},
      onChatBodyScroll: () => {},
    };
  }
  return context;
}
