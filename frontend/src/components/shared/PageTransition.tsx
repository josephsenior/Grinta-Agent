import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { prefersReducedMotion } from "#/utils/animation-utils";

/**
 * Smooth page transitions between routes
 */
export function PageTransition({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const location = useLocation();
  const [displayLocation, setDisplayLocation] = useState(location);
  const [transitionStage, setTransitionStage] = useState("fadeIn");
  const reducedMotion = prefersReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      setDisplayLocation(location);
      return;
    }

    if (location !== displayLocation) {
      setTransitionStage("fadeOut");
    }
  }, [location, displayLocation, reducedMotion]);

  useEffect(() => {
    if (reducedMotion) {
      return (): void => {
        // No cleanup needed
      };
    }

    if (transitionStage === "fadeOut") {
      const timeout = setTimeout(() => {
        setDisplayLocation(location);
        setTransitionStage("fadeIn");
      }, 200);

      return (): void => {
        clearTimeout(timeout);
      };
    }

    return (): void => {
      // No cleanup needed
    };
  }, [transitionStage, location, reducedMotion]);

  if (reducedMotion) {
    return children as React.ReactElement;
  }

  return (
    <div
      className={`
        ${transitionStage === "fadeOut" ? "animate-fade-out" : "animate-fade-in"}
      `}
      style={{
        animation:
          transitionStage === "fadeOut"
            ? "fadeOut 0.2s ease-in forwards"
            : "fadeIn 0.3s ease-out forwards",
      }}
    >
      {children}
    </div>
  );
}

// Add to index.css
export const pageTransitionStyles = `
@keyframes fadeOut {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-10px);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
`;
