import React, { useState, useEffect, useContext } from "react";
import { useTranslation } from "react-i18next";
import { FaStar } from "react-icons/fa";
import { cn } from "#/utils/utils";
import { I18nKey } from "#/i18n/declaration";
import { useSubmitConversationFeedback } from "#/hooks/mutation/use-submit-conversation-feedback";
import { ScrollContext } from "#/context/scroll-context";
import type { ScrollContextType } from "#/context/scroll-context";

// Global timeout duration in milliseconds
const AUTO_SUBMIT_TIMEOUT = 10000;

interface LikertScaleProps {
  eventId?: number;
  initiallySubmitted?: boolean;
  initialRating?: number;
  initialReason?: string;
}

// Helper functions
function getButtonClass({
  rating,
  isSubmitted,
  selectedRating,
}: {
  rating: number;
  isSubmitted: boolean;
  selectedRating: number | null;
}) {
  if (isSubmitted) {
    return selectedRating && selectedRating >= rating
      ? "text-yellow-400 cursor-not-allowed"
      : "text-foreground-secondary opacity-50 cursor-not-allowed";
  }

  return selectedRating && selectedRating >= rating
    ? "text-yellow-400"
    : "text-foreground-secondary hover:text-yellow-200";
}

function buildFeedbackReasons(t: ReturnType<typeof useTranslation>["t"]) {
  return [
    t(I18nKey.FEEDBACK$REASON_MISUNDERSTOOD_INSTRUCTION),
    t(I18nKey.FEEDBACK$REASON_FORGOT_CONTEXT),
    t(I18nKey.FEEDBACK$REASON_UNNECESSARY_CHANGES),
    t(I18nKey.FEEDBACK$REASON_SHOULD_ASK_FIRST),
    t(I18nKey.FEEDBACK$REASON_DIDNT_FINISH_JOB),
    t(I18nKey.FEEDBACK$REASON_OTHER),
  ];
}

function attemptScroll({
  scrollContext,
}: {
  scrollContext?: ScrollContextType;
}) {
  const scrollToBottom = scrollContext?.scrollDomToBottom;
  if (scrollToBottom && scrollContext?.autoScroll) {
    setTimeout(() => scrollToBottom(), 100);
  }
}

function startReasonFlow({
  rating,
  setShowReasons,
  setCountdown,
  setReasonTimeout,
  submitFeedback,
  scrollContext,
}: {
  rating: number;
  setShowReasons: React.Dispatch<React.SetStateAction<boolean>>;
  setCountdown: React.Dispatch<React.SetStateAction<number>>;
  setReasonTimeout: React.Dispatch<React.SetStateAction<NodeJS.Timeout | null>>;
  submitFeedback: (rating: number, reason?: string) => void;
  scrollContext?: ScrollContextType;
}) {
  setShowReasons(true);
  setCountdown(Math.ceil(AUTO_SUBMIT_TIMEOUT / 1000));

  const timeout = setTimeout(() => {
    submitFeedback(rating);
  }, AUTO_SUBMIT_TIMEOUT);

  setReasonTimeout(timeout);
  attemptScroll({ scrollContext });
}

// Hooks
function useCountdownEffect({
  countdown,
  showReasons,
  isSubmitted,
  setCountdown,
}: {
  countdown: number;
  showReasons: boolean;
  isSubmitted: boolean;
  setCountdown: React.Dispatch<React.SetStateAction<number>>;
}) {
  useEffect(() => {
    if (countdown > 0 && showReasons && !isSubmitted) {
      const timer = setTimeout(() => {
        setCountdown((value) => value - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
    return () => {};
  }, [countdown, showReasons, isSubmitted, setCountdown]);
}

function useCleanupTimeout(reasonTimeout: NodeJS.Timeout | null) {
  useEffect(
    () => () => {
      if (reasonTimeout) {
        clearTimeout(reasonTimeout);
      }
    },
    [reasonTimeout],
  );
}

function useAutoScrollOnMount({
  scrollContext,
  isSubmitted,
}: {
  scrollContext?: ScrollContextType;
  isSubmitted: boolean;
}) {
  useEffect(() => {
    if (
      scrollContext?.scrollDomToBottom &&
      scrollContext.autoScroll &&
      !isSubmitted
    ) {
      setTimeout(() => {
        scrollContext.scrollDomToBottom?.();
      }, 100);
    }
  }, [isSubmitted, scrollContext]);
}

function useAutoScrollOnReasons({
  scrollContext,
  showReasons,
}: {
  scrollContext?: ScrollContextType;
  showReasons: boolean;
}) {
  useEffect(() => {
    if (
      scrollContext?.scrollDomToBottom &&
      scrollContext.autoScroll &&
      showReasons
    ) {
      setTimeout(() => {
        scrollContext.scrollDomToBottom?.();
      }, 100);
    }
  }, [scrollContext, showReasons]);
}

// Main hook
function useLikertController({
  eventId,
  initiallySubmitted,
  initialRating,
  initialReason,
}: LikertScaleProps) {
  const { t } = useTranslation();
  const [selectedRating, setSelectedRating] = useState<number | null>(
    initialRating || null,
  );
  const [selectedReason, setSelectedReason] = useState<string | null>(
    initialReason || null,
  );
  const [showReasons, setShowReasons] = useState(false);
  const [reasonTimeout, setReasonTimeout] = useState<NodeJS.Timeout | null>(
    null,
  );
  const [isSubmitted, setIsSubmitted] = useState(initiallySubmitted);
  const [countdown, setCountdown] = useState<number>(0);
  const scrollContext = useContext(ScrollContext);
  const submitConversationFeedback = useSubmitConversationFeedback();

  useEffect(() => setIsSubmitted(initiallySubmitted), [initiallySubmitted]);
  useEffect(() => {
    if (initialRating) {
      setSelectedRating(initialRating);
    }
  }, [initialRating]);
  useEffect(() => {
    if (initialReason) {
      setSelectedReason(initialReason);
    }
  }, [initialReason]);

  const submitFeedback = React.useCallback(
    (rating: number, reason?: string) => {
      submitConversationFeedback.mutate(
        {
          rating,
          eventId,
          reason,
        },
        {
          onSuccess: () => {
            setSelectedReason(reason || null);
            setShowReasons(false);
            setIsSubmitted(true);
          },
        },
      );
    },
    [eventId, submitConversationFeedback],
  );

  const handleRatingClick = React.useCallback(
    (rating: number) => {
      if (isSubmitted) {
        return;
      }

      setSelectedRating(rating);

      if (rating <= 3) {
        startReasonFlow({
          rating,
          setShowReasons,
          setCountdown,
          setReasonTimeout,
          submitFeedback,
          scrollContext,
        });
      } else {
        setShowReasons(false);
        submitFeedback(rating);
      }
    },
    [isSubmitted, scrollContext, submitFeedback],
  );

  const handleReasonClick = React.useCallback(
    (reason: string) => {
      if (selectedRating && reasonTimeout && !isSubmitted) {
        clearTimeout(reasonTimeout);
        setCountdown(0);
        submitFeedback(selectedRating, reason);
      }
    },
    [isSubmitted, reasonTimeout, selectedRating, submitFeedback],
  );

  useCountdownEffect({
    countdown,
    showReasons,
    isSubmitted: isSubmitted ?? false,
    setCountdown,
  });
  useCleanupTimeout(reasonTimeout);
  useAutoScrollOnMount({ scrollContext, isSubmitted: isSubmitted ?? false });
  useAutoScrollOnReasons({ scrollContext, showReasons });

  const feedbackReasons = React.useMemo(() => buildFeedbackReasons(t), [t]);

  return {
    t,
    selectedRating,
    selectedReason,
    showReasons,
    isSubmitted,
    countdown,
    feedbackReasons,
    handleRatingClick,
    handleReasonClick,
  };
}

// Component
function LikertReasons({
  controller,
}: {
  controller: ReturnType<typeof useLikertController>;
}) {
  if (!controller.showReasons || controller.isSubmitted) {
    return null;
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="text-xs text-foreground-secondary">
        {controller.t("Why this rating?")}
        {controller.countdown > 0 && (
          <span className="ml-2 text-foreground">
            {controller.t("Auto-submitting in {{seconds}}s", {
              seconds: controller.countdown,
            })}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {controller.feedbackReasons.map((reason) => (
          <button
            key={reason}
            type="button"
            className="px-3 py-1 text-xs border border-border rounded-full hover:bg-background-secondary"
            onClick={() => controller.handleReasonClick(reason)}
          >
            {reason}
          </button>
        ))}
      </div>
    </div>
  );
}

// Main component
export function LikertScale({
  eventId,
  initiallySubmitted = false,
  initialRating,
  initialReason,
}: LikertScaleProps) {
  const controller = useLikertController({
    eventId,
    initiallySubmitted,
    initialRating,
    initialReason,
  });
  const { t } = controller;

  return (
    <div className="mt-3 flex flex-col gap-1">
      <div className="text-sm text-foreground-secondary mb-1">
        {controller.isSubmitted
          ? t(I18nKey.FEEDBACK$THANK_YOU_FOR_FEEDBACK)
          : t("Rate this response")}
      </div>
      <div className="flex items-center gap-2">
        {[1, 2, 3, 4, 5].map((rating) => (
          <button
            key={rating}
            type="button"
            aria-label={`Rate ${rating} star${rating === 1 ? "" : "s"}`}
            className={cn(
              "transition-colors",
              getButtonClass({
                rating,
                isSubmitted: controller.isSubmitted ?? false,
                selectedRating: controller.selectedRating,
              }),
            )}
            onClick={() => controller.handleRatingClick(rating)}
            disabled={controller.isSubmitted ?? false}
          >
            <FaStar className="w-5 h-5" />
          </button>
        ))}
      </div>

      <LikertReasons controller={controller} />
    </div>
  );
}
