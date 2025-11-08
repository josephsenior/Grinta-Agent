import { useTranslation } from "react-i18next";
import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Spinner } from "@heroui/react";
import { MicroagentManagementMicroagentCard } from "./microagent-management-microagent-card";
import { MicroagentManagementLearnThisRepo } from "./microagent-management-learn-this-repo";
import { useRepositoryMicroagents } from "#/hooks/query/use-repository-microagents";
import { useMicroagentManagementConversations } from "#/hooks/query/use-microagent-management-conversations";
import { GitRepository } from "#/types/git";
import { RootState } from "#/store";
import { setSelectedMicroagentItem } from "#/state/microagent-management-slice";
import { cn } from "#/utils/utils";
import { I18nKey } from "#/i18n/declaration";

interface MicroagentManagementRepoMicroagentsProps {
  repository: GitRepository;
}

export function MicroagentManagementRepoMicroagents({
  repository,
}: MicroagentManagementRepoMicroagentsProps) {
  const controller = useRepoMicroagentsController({ repository });
  const { t } = useTranslation();

  if (controller.isLoading) {
    return (
      <div className="pb-4 flex justify-center">
        <Spinner size="sm" data-testid="loading-spinner" />
      </div>
    );
  }

  // If there's an error with microagents, show the learn this repo component
  if (controller.isError) {
    return (
      <div>
        <MicroagentManagementLearnThisRepo repository={repository} />
      </div>
    );
  }

  const numberOfMicroagents = controller.microagents.length;
  const numberOfConversations = controller.conversations.length;
  const totalItems = numberOfMicroagents + numberOfConversations;
  const hasMicroagents = numberOfMicroagents > 0;
  const hasConversations = numberOfConversations > 0;

  return (
    <div>
      {totalItems === 0 && (
        <MicroagentManagementLearnThisRepo repository={repository} />
      )}
      {/* Render microagents */}
      {hasMicroagents && (
        <div className="flex flex-col">
          <span className="text-md text-white font-medium leading-5 mb-4">
            {t(I18nKey.MICROAGENT_MANAGEMENT$EXISTING_MICROAGENTS)}
          </span>
          {controller.microagents.map((microagent) => (
            <div key={microagent.name} className="pb-4 last:pb-0">
              <MicroagentManagementMicroagentCard
                microagent={microagent}
                repository={repository}
              />
            </div>
          ))}
        </div>
      )}

      {/* Render conversations */}
      {hasConversations && (
        <div className={cn("flex flex-col", hasMicroagents && "mt-4")}>
          <span className="text-md text-white font-medium leading-5 mb-4">
            {t(I18nKey.COMMON$IN_PROGRESS)}
          </span>
          {controller.conversations.map((conversation) => (
            <div key={conversation.conversation_id} className="pb-4 last:pb-0">
              <MicroagentManagementMicroagentCard
                conversation={conversation}
                repository={repository}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function useRepoMicroagentsController({
  repository,
}: {
  repository: GitRepository;
}) {
  const { selectedMicroagentItem } = useSelector(
    (state: RootState) => state.microagentManagement,
  );
  const dispatch = useDispatch();
  const repositoryName = repository.full_name;
  const [owner, repo] = repositoryName.split("/");

  const microagentQuery = useRepositoryMicroagents(owner, repo, true);
  const conversationsQuery = useMicroagentManagementConversations(
    repositoryName,
    undefined,
    1000,
    true,
  );

  useEffect(() => {
    const conversations = conversationsQuery.data ?? [];
    const selectedConversation = selectedMicroagentItem?.conversation;
    if (!conversations.length || !selectedConversation) {
      return;
    }

    const latestSelectedConversation = conversations.find(
      (conversation) =>
        conversation.conversation_id === selectedConversation.conversation_id,
    );

    if (latestSelectedConversation) {
      dispatch(
        setSelectedMicroagentItem({
          microagent: null,
          conversation: latestSelectedConversation,
        }),
      );
    }
  }, [conversationsQuery.data, dispatch, selectedMicroagentItem]);

  useEffect(() => {
    return () => {
      dispatch(
        setSelectedMicroagentItem({
          microagent: null,
          conversation: null,
        }),
      );
    };
  }, [dispatch]);

  return {
    microagents: microagentQuery.data ?? [],
    conversations: conversationsQuery.data ?? [],
    isLoading: microagentQuery.isLoading || conversationsQuery.isLoading,
    isError: microagentQuery.isError || conversationsQuery.isError,
  };
}
