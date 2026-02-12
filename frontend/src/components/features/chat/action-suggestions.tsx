import posthog from "#/utils/posthog";
import React, { useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { gsap } from "gsap";
import { SuggestionItem } from "#/components/features/suggestions/suggestion-item";
import { I18nKey } from "#/i18n/declaration";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";

interface ActionSuggestionsProps {
  onSuggestionsClick: (value: string) => void;
}

export function ActionSuggestions({
  onSuggestionsClick,
}: ActionSuggestionsProps) {
  const { t } = useTranslation();
  const { data: conversation } = useActiveConversation();

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(containerRef.current.children, { opacity: 1, x: 0 });
      return;
    }

    // Stagger animation for suggestion buttons
    const buttons = Array.from(
      containerRef.current.querySelectorAll("[data-suggestion-item]"),
    ) as HTMLElement[];
    if (buttons.length > 0) {
      gsap.set(buttons, { opacity: 0, x: -20 });
      gsap.to(buttons, {
        opacity: 1,
        x: 0,
        duration: 0.4,
        stagger: 0.08,
        ease: "power2.out",
      });
    }
  }, [conversation?.selected_repository]);

  // We are simplifying the UI to focus on Chat, Files, and Terminal.
  // Git provider-related actions like PRs and pushes are removed for now.
  return (
    <div className="flex flex-col gap-2 mb-2">
      {/* Action suggestions are currently disabled to simplify the interface */}
    </div>
  );
}
