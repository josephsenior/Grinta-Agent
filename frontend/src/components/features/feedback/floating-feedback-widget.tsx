import React, { useState } from "react";
import { useLocation } from "react-router-dom";
import { MessageSquare, X, ThumbsUp, ThumbsDown } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { FeedbackModal } from "./feedback-modal";

/**
 * Floating Feedback Widget
 *
 * A persistent feedback button that appears on all pages (except landing/auth)
 * to make it easy for users to provide feedback during beta.
 */
export function FloatingFeedbackWidget() {
  const { t } = useTranslation();
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackPolarity, setFeedbackPolarity] = useState<
    "positive" | "negative"
  >("positive");

  // Don't show on landing page or auth pages
  const isLandingPage = location.pathname === "/";
  const isAuthPage = location.pathname.startsWith("/auth/");
  const shouldShow = !isLandingPage && !isAuthPage;

  if (!shouldShow) {
    return null;
  }

  const handleFeedbackClick = (polarity: "positive" | "negative") => {
    setFeedbackPolarity(polarity);
    setFeedbackModalOpen(true);
    setIsExpanded(false);
  };

  return (
    <>
      {/* Floating Feedback Button */}
      <div
        className="fixed bottom-6 right-6 z-[9998] flex flex-col items-end gap-3"
        style={{ display: "block" }}
      >
        {/* Expanded Options */}
        {isExpanded && (
          <div className="flex flex-col gap-2 mb-2 animate-slide-up">
            <button
              type="button"
              onClick={() => handleFeedbackClick("positive")}
              className={cn(
                "flex items-center gap-2 px-4 py-3 rounded-xl",
                "bg-gradient-to-r from-emerald-500/90 to-emerald-600/90",
                "backdrop-blur-md border border-emerald-400/30",
                "text-white font-medium text-sm",
                "shadow-lg shadow-emerald-500/20",
                "hover:shadow-xl hover:shadow-emerald-500/30",
                "transition-all duration-200",
                "hover:scale-105 active:scale-95",
              )}
              aria-label="Send positive feedback"
            >
              <ThumbsUp className="w-4 h-4" />
              <span>{t("feedback.positiveFeedback", "Positive Feedback")}</span>
            </button>
            <button
              type="button"
              onClick={() => handleFeedbackClick("negative")}
              className={cn(
                "flex items-center gap-2 px-4 py-3 rounded-xl",
                "bg-gradient-to-r from-red-500/90 to-red-600/90",
                "backdrop-blur-md border border-red-400/30",
                "text-white font-medium text-sm",
                "shadow-lg shadow-red-500/20",
                "hover:shadow-xl hover:shadow-red-500/30",
                "transition-all duration-200",
                "hover:scale-105 active:scale-95",
              )}
              aria-label={t(
                "feedback.sendNegativeFeedback",
                "Send negative feedback",
              )}
            >
              <ThumbsDown className="w-4 h-4" />
              <span>{t("feedback.negativeFeedback", "Negative Feedback")}</span>
            </button>
          </div>
        )}

        {/* Main Feedback Button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className={cn(
              "relative w-14 h-14 rounded-full",
              "bg-gradient-to-br from-brand-500 to-brand-600",
              "backdrop-blur-md border-2 border-white/20",
              "text-white shadow-2xl shadow-brand-500/30",
              "hover:shadow-brand-500/50 hover:scale-110",
              "active:scale-95",
              "transition-all duration-300",
              "flex items-center justify-center",
            )}
            aria-label={isExpanded ? "Close feedback options" : "Open feedback"}
            aria-expanded={isExpanded}
          >
            {/* Pulse animation */}
            <div
              className={cn(
                "absolute inset-0 rounded-full",
                "bg-brand-500/40 animate-ping",
                isExpanded && "hidden",
              )}
              style={{ animationDuration: "2s" }}
            />

            {/* Icon */}
            {isExpanded ? (
              <X className="w-6 h-6 transition-transform duration-200" />
            ) : (
              <MessageSquare className="w-6 h-6 transition-transform duration-200" />
            )}
          </button>

          {/* Tooltip when collapsed and hovered */}
          {!isExpanded && isHovered && (
            <div
              className={cn(
                "absolute right-16 top-1/2 -translate-y-1/2",
                "px-3 py-2 rounded-lg",
                "bg-black/90 backdrop-blur-md border border-white/10",
                "text-white text-sm font-medium whitespace-nowrap",
                "pointer-events-none transition-opacity duration-200",
                "shadow-lg z-50",
              )}
            >
              {t("feedback.shareFeedback", "Share Feedback")}
              <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full">
                <div className="w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-4 border-l-black/90" />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={feedbackModalOpen}
        onClose={() => setFeedbackModalOpen(false)}
        polarity={feedbackPolarity}
      />
    </>
  );
}
