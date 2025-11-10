import React from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { I18nKey } from "#/i18n/declaration";
import { getTrajectory } from "#/services/trajectory-service";
import { downloadTrajectory } from "#/utils/download-trajectory";

/**
 * Custom hook to handle feedback and action operations
 * Separates feedback logic from UI components
 */
export function useChatFeedbackActions() {
  const { t } = useTranslation();
  const params = useParams<{ conversationId: string }>();

  const [feedbackPolarity, setFeedbackPolarity] = React.useState<
    "positive" | "negative"
  >("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);

  const onClickShareFeedbackActionButton = React.useCallback(
    async (polarity: "positive" | "negative") => {
      setFeedbackModalIsOpen(true);
      setFeedbackPolarity(polarity);
    },
    [],
  );

  const onClickExportTrajectoryButton = React.useCallback(async () => {
    if (!params.conversationId) {
      displayErrorToast(t(I18nKey.CONVERSATION$DOWNLOAD_ERROR));
      return;
    }

    try {
      const data = await getTrajectory(params.conversationId);
      await downloadTrajectory(
        params.conversationId ?? t(I18nKey.CONVERSATION$UNKNOWN),
        data,
      );
    } catch (error) {
      console.error("Failed to export trajectory:", error);
      displayErrorToast(t(I18nKey.CONVERSATION$DOWNLOAD_ERROR));
    }
  }, [params.conversationId, t]);

  return {
    feedbackPolarity,
    setFeedbackPolarity,
    feedbackModalIsOpen,
    setFeedbackModalIsOpen,
    onClickShareFeedbackActionButton,
    onClickExportTrajectoryButton,
  };
}
