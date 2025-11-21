import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { MicroagentManagementDefault } from "./microagent-management-default";
import { MicroagentManagementOpeningPr } from "./microagent-management-opening-pr";
import { MicroagentManagementReviewPr } from "./microagent-management-review-pr";
import { MicroagentManagementViewMicroagent } from "./microagent-management-view-microagent";
import { MicroagentManagementError } from "./microagent-management-error";
import { MicroagentManagementConversationStopped } from "./microagent-management-conversation-stopped";

// Helper functions
const isConversationOpeningPr = (
  conversation: NonNullable<
    RootState["microagentManagement"]["selectedMicroagentItem"]
  >["conversation"],
) => {
  if (!conversation) return false;

  const isStarting =
    conversation.status === "STARTING" ||
    conversation.runtime_status === "STATUS$STARTING_RUNTIME";

  const isOpeningPr =
    conversation.status === "RUNNING" &&
    conversation.runtime_status === "STATUS$READY";

  return isStarting || isOpeningPr;
};

const isConversationStopped = (
  conversation: NonNullable<
    RootState["microagentManagement"]["selectedMicroagentItem"]
  >["conversation"],
) => {
  if (!conversation) return false;

  return (
    conversation.status === "STOPPED" ||
    conversation.runtime_status === "STATUS$STOPPED"
  );
};

const resolveMicroagentContent = (
  selectedMicroagentItem: RootState["microagentManagement"]["selectedMicroagentItem"],
) => {
  if (!selectedMicroagentItem) {
    return <MicroagentManagementDefault />;
  }

  if (selectedMicroagentItem.microagent) {
    return <MicroagentManagementViewMicroagent />;
  }

  const { conversation } = selectedMicroagentItem;
  if (!conversation) {
    return <MicroagentManagementDefault />;
  }

  if (conversation.pr_number && conversation.pr_number.length > 0) {
    return <MicroagentManagementReviewPr />;
  }

  if (isConversationOpeningPr(conversation)) {
    return <MicroagentManagementOpeningPr />;
  }

  if (conversation.runtime_status === "STATUS$ERROR") {
    return <MicroagentManagementError />;
  }

  if (isConversationStopped(conversation)) {
    return <MicroagentManagementConversationStopped />;
  }

  return <MicroagentManagementDefault />;
};

// Main component
export function MicroagentManagementMain() {
  const { selectedMicroagentItem } = useSelector(
    (state: RootState) => state.microagentManagement,
  );

  return resolveMicroagentContent(selectedMicroagentItem);
}
