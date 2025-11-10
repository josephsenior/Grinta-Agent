import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch, useSelector } from "react-redux";
import { MicroagentManagementSidebar } from "./microagent-management-sidebar";
import { MicroagentManagementMain } from "./microagent-management-main";
import { MicroagentManagementUpsertMicroagentModal } from "./microagent-management-upsert-microagent-modal";
import { RootState } from "#/store";
import {
  setAddMicroagentModalVisible,
  setUpdateMicroagentModalVisible,
  setLearnThisRepoModalVisible,
} from "#/state/microagent-management-slice";
import { useCreateConversationAndSubscribeMultiple } from "#/hooks/use-create-conversation-and-subscribe-multiple";
import {
  LearnThisRepoFormData,
  MicroagentFormData,
} from "#/types/microagent-management";
import { AgentState } from "#/types/agent-state";
import { getPR, getProviderName, getPRShort } from "#/utils/utils";
import {
  isForgeEvent,
  isAgentStateChangeObservation,
  isFinishAction,
} from "#/types/core/guards";
import { GitRepository } from "#/types/git";
import { queryClient } from "#/query-client-config";
import { Provider } from "#/types/settings";
import { MicroagentManagementLearnThisRepoModal } from "./microagent-management-learn-this-repo-modal";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";
import { getFirstPRUrl } from "#/utils/parse-pr-url";
import { I18nKey } from "#/i18n/declaration";
import { useUserProviders } from "#/hooks/use-user-providers";

// Handle error events
const isErrorEvent = (evt: unknown): evt is { error: true; message: string } =>
  typeof evt === "object" &&
  evt !== null &&
  "error" in evt &&
  evt.error === true;

const isAgentStatusError = (evt: unknown): boolean =>
  isForgeEvent(evt) &&
  isAgentStateChangeObservation(evt) &&
  evt.extras.agent_state === AgentState.ERROR;

const shouldInvalidateConversationsList = (currentSocketEvent: unknown) => {
  const hasError =
    isErrorEvent(currentSocketEvent) || isAgentStatusError(currentSocketEvent);
  const hasStateChanged =
    isForgeEvent(currentSocketEvent) &&
    isAgentStateChangeObservation(currentSocketEvent);
  const hasFinished =
    isForgeEvent(currentSocketEvent) && isFinishAction(currentSocketEvent);

  return hasError || hasStateChanged || hasFinished;
};

const getConversationInstructions = (
  repositoryName: string,
  formData: MicroagentFormData,
  pr: string,
  prShort: string,
  gitProvider: Provider,
) => `Create a microagent for the repository ${repositoryName} by following the steps below:

- Step 1: Create a markdown file inside the .Forge/microagents folder with the name of the microagent (The microagent must be created in the .Forge/microagents folder and should be able to perform the described task when triggered). This is the instructions about what the microagent should do: ${formData.query}. ${
  formData.triggers && formData.triggers.length > 0
    ? `This is the triggers of the microagent: ${formData.triggers.join(", ")}`
    : "Please be noted that the microagent doesn't have any triggers."
}

- Step 2: Create a new branch for the repository ${repositoryName}, must avoid duplicated branches.

- Step 3: Please push the changes to your branch on ${getProviderName(gitProvider)} and create a ${pr}. Please create a meaningful branch name that describes the changes. If a ${pr} template exists in the repository, please follow it when creating the ${prShort} description.
`;

const getUpdateConversationInstructions = (
  repositoryName: string,
  formData: MicroagentFormData,
  pr: string,
  prShort: string,
  gitProvider: Provider,
) => `Update the microagent for the repository ${repositoryName} by following the steps below:


- Step 1: Update the microagent. This is the path of the microagent: ${formData.microagentPath} (The updated microagent must be in the .Forge/microagents folder and should be able to perform the described task when triggered). This is the updated instructions about what the microagent should do: ${formData.query}. ${
  formData.triggers && formData.triggers.length > 0
    ? `This is the triggers of the microagent: ${formData.triggers.join(", ")}`
    : "Please be noted that the microagent doesn't have any triggers."
}

- Step 2: Create a new branch for the repository ${repositoryName}, must avoid duplicated branches.

- Step 3: Please push the changes to your branch on ${getProviderName(gitProvider)} and create a ${pr}. Please create a meaningful branch name that describes the changes. If a ${pr} template exists in the repository, please follow it when creating the ${prShort} description.
`;

export function MicroagentManagementContent() {
  const width = useWindowWidth();

  const {
    addMicroagentModalVisible,
    updateMicroagentModalVisible,
    selectedRepository,
    learnThisRepoModalVisible,
  } = useSelector((state: RootState) => state.microagentManagement);

  const { providers } = useUserProviders();

  const { t } = useTranslation();

  const dispatch = useDispatch();

  const { createConversationAndSubscribe, isPending } =
    useCreateConversationAndSubscribeMultiple();

  const microagentHandlers = useMicroagentHandlers({
    selectedRepository,
    dispatch,
    createConversationAndSubscribe,
    t,
  });

  const modals = (
    <MicroagentModals
      addVisible={addMicroagentModalVisible}
      updateVisible={updateMicroagentModalVisible}
      learnVisible={learnThisRepoModalVisible}
      onConfirmUpsert={microagentHandlers.handleUpsertMicroagent}
      onConfirmLearn={microagentHandlers.handleLearnThisRepoConfirm}
      onCancelUpsert={microagentHandlers.hideUpsertMicroagentModal}
      onCancelLearn={microagentHandlers.hideLearnThisRepoModal}
      isLoading={isPending}
    />
  );

  const providersAreSet = providers.length > 0;

  if (width < 1024) {
    return (
      <div className="w-full h-full flex flex-col gap-6">
        <div className="w-full rounded-lg border border-[#525252] bg-[#24272E] max-h-[494px] min-h-[494px]">
          {providersAreSet && (
            <MicroagentManagementSidebar
              isSmallerScreen
              providers={providers}
            />
          )}
        </div>
        <div className="w-full rounded-lg border border-[#525252] bg-[#24272E] flex-1 min-h-[494px]">
          <MicroagentManagementMain />
        </div>
        {modals}
      </div>
    );
  }

  return (
    <div className="w-full h-full flex rounded-lg border border-[#525252] bg-[#24272E] overflow-hidden">
      {providersAreSet && <MicroagentManagementSidebar providers={providers} />}
      <div className="flex-1">
        <MicroagentManagementMain />
      </div>
      {modals}
    </div>
  );
}

function useWindowWidth() {
  const [width, setWidth] = useState(() => window.innerWidth);

  useEffect(() => {
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return width;
}

function getRepositoryNameFromSelection(
  selectedRepository: RootState["microagentManagement"]["selectedRepository"],
) {
  if (selectedRepository && typeof selectedRepository === "object") {
    return (selectedRepository as GitRepository).full_name;
  }
  return "";
}

function maybeNotifyAgentRunning(
  socketEvent: unknown,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (
    isForgeEvent(socketEvent) &&
    isAgentStateChangeObservation(socketEvent) &&
    socketEvent.extras.agent_state === AgentState.RUNNING
  ) {
    displaySuccessToast(
      t(I18nKey.MICROAGENT_MANAGEMENT$OPENING_PR_TO_CREATE_MICROAGENT),
    );
  }
}

function maybeNotifyMissingPullRequest(
  socketEvent: unknown,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (!isForgeEvent(socketEvent) || !isFinishAction(socketEvent)) {
    return;
  }

  const prUrl = getFirstPRUrl(socketEvent.args.final_thought || "");
  if (!prUrl) {
    displaySuccessToast(t(I18nKey.MICROAGENT_MANAGEMENT$PR_NOT_CREATED));
  }
}

function maybeNotifyMicroagentError(
  socketEvent: unknown,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (isErrorEvent(socketEvent) || isAgentStatusError(socketEvent)) {
    displayErrorToast(
      t(I18nKey.MICROAGENT_MANAGEMENT$ERROR_CREATING_MICROAGENT),
    );
  }
}

function maybeInvalidateMicroagentConversations(
  socketEvent: unknown,
  repositoryName: string,
  invalidate: (repoName: string) => void,
) {
  if (shouldInvalidateConversationsList(socketEvent)) {
    invalidate(repositoryName);
  }
}

function useMicroagentHandlers({
  selectedRepository,
  dispatch,
  createConversationAndSubscribe,
  t,
}: {
  selectedRepository: RootState["microagentManagement"]["selectedRepository"];
  dispatch: ReturnType<typeof useDispatch>;
  createConversationAndSubscribe: ReturnType<
    typeof useCreateConversationAndSubscribeMultiple
  >["createConversationAndSubscribe"];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const hideUpsertMicroagentModal = React.useCallback(
    (isUpdate: boolean = false) => {
      if (isUpdate) {
        dispatch(setUpdateMicroagentModalVisible(false));
      } else {
        dispatch(setAddMicroagentModalVisible(false));
      }
    },
    [dispatch],
  );

  const hideLearnThisRepoModal = React.useCallback(() => {
    dispatch(setLearnThisRepoModalVisible(false));
  }, [dispatch]);

  const invalidateConversationsList = React.useCallback(
    (repositoryName: string) => {
      queryClient.invalidateQueries({
        queryKey: [
          "conversations",
          "search",
          repositoryName,
          "microagent_management",
        ],
      });
    },
    [],
  );

  const handleMicroagentEvent = React.useCallback(
    (socketEvent: unknown) => {
      const repositoryName = getRepositoryNameFromSelection(selectedRepository);

      maybeNotifyAgentRunning(socketEvent, t);
      maybeNotifyMissingPullRequest(socketEvent, t);
      maybeNotifyMicroagentError(socketEvent, t);
      maybeInvalidateMicroagentConversations(
        socketEvent,
        repositoryName,
        invalidateConversationsList,
      );
    },
    [invalidateConversationsList, selectedRepository, t],
  );

  const handleUpsertMicroagent = React.useCallback(
    (formData: MicroagentFormData, isUpdate: boolean = false) => {
      if (!selectedRepository || typeof selectedRepository !== "object") {
        return;
      }

      const repository = selectedRepository as GitRepository;
      const repositoryName = repository.full_name;
      const gitProvider = repository.git_provider;

      const isGitLab = gitProvider === "gitlab";
      const pr = getPR(isGitLab);
      const prShort = getPRShort(isGitLab);

      const conversationInstructions = isUpdate
        ? getUpdateConversationInstructions(
            repositoryName,
            formData,
            pr,
            prShort,
            gitProvider,
          )
        : getConversationInstructions(
            repositoryName,
            formData,
            pr,
            prShort,
            gitProvider,
          );

      const createMicroagent = {
        repo: repositoryName,
        git_provider: gitProvider,
        title: formData.query,
      };

      createConversationAndSubscribe({
        query: conversationInstructions,
        conversationInstructions,
        repository: {
          name: repositoryName,
          gitProvider,
        },
        createMicroagent,
        onSuccessCallback: () => {
          invalidateConversationsList(repositoryName);

          const [owner, repo] = repositoryName.split("/");
          queryClient.invalidateQueries({
            queryKey: ["repository-microagents", owner, repo],
          });

          hideUpsertMicroagentModal(isUpdate);
        },
        onEventCallback: handleMicroagentEvent,
      });
    },
    [
      createConversationAndSubscribe,
      handleMicroagentEvent,
      hideUpsertMicroagentModal,
      invalidateConversationsList,
      selectedRepository,
    ],
  );

  const handleLearnThisRepoConfirm = React.useCallback(
    (formData: LearnThisRepoFormData) => {
      if (!selectedRepository || typeof selectedRepository !== "object") {
        return;
      }

      const repository = selectedRepository as GitRepository;
      const repositoryName = repository.full_name;
      const gitProvider = repository.git_provider;

      const createMicroagent = {
        repo: repositoryName,
        git_provider: gitProvider,
        title: formData.query,
      };

      createConversationAndSubscribe({
        query: formData.query,
        conversationInstructions: formData.query,
        repository: {
          name: repositoryName,
          gitProvider,
        },
        createMicroagent,
        onSuccessCallback: () => {
          hideLearnThisRepoModal();
        },
      });
    },
    [
      createConversationAndSubscribe,
      hideLearnThisRepoModal,
      selectedRepository,
    ],
  );

  return {
    handleUpsertMicroagent,
    handleLearnThisRepoConfirm,
    hideUpsertMicroagentModal,
    hideLearnThisRepoModal,
  } as const;
}

function MicroagentModals({
  addVisible,
  updateVisible,
  learnVisible,
  onConfirmUpsert,
  onConfirmLearn,
  onCancelUpsert,
  onCancelLearn,
  isLoading,
}: {
  addVisible: boolean;
  updateVisible: boolean;
  learnVisible: boolean;
  onConfirmUpsert: (formData: MicroagentFormData, isUpdate?: boolean) => void;
  onConfirmLearn: (formData: LearnThisRepoFormData) => void;
  onCancelUpsert: (isUpdate?: boolean) => void;
  onCancelLearn: () => void;
  isLoading: boolean;
}) {
  return (
    <>
      {(addVisible || updateVisible) && (
        <MicroagentManagementUpsertMicroagentModal
          onConfirm={(formData) => onConfirmUpsert(formData, updateVisible)}
          onCancel={() => onCancelUpsert(updateVisible)}
          isLoading={isLoading}
          isUpdate={updateVisible}
        />
      )}
      {learnVisible && (
        <MicroagentManagementLearnThisRepoModal
          onCancel={onCancelLearn}
          onConfirm={onConfirmLearn}
          isLoading={isLoading}
        />
      )}
    </>
  );
}

const isCompactLayout = (width: number) => width < 1024;

const renderCompactLayout = ({
  providersAreSet,
  providers,
  modals,
}: {
  providersAreSet: boolean;
  providers: ReturnType<typeof useUserProviders>["providers"];
  modals: React.ReactNode;
}) => (
  <div className="w-full h-full flex flex-col gap-6">
    <div className="w-full rounded-lg border border-[#525252] bg-[#24272E] max-h-[494px] min-h-[494px]">
      {providersAreSet && (
        <MicroagentManagementSidebar isSmallerScreen providers={providers} />
      )}
    </div>
    <div className="w-full rounded-lg border border-[#525252] bg-[#24272E] flex-1 min-h-[494px]">
      <MicroagentManagementMain />
    </div>
    {modals}
  </div>
);

const renderDesktopLayout = ({
  providersAreSet,
  providers,
  modals,
}: {
  providersAreSet: boolean;
  providers: ReturnType<typeof useUserProviders>["providers"];
  modals: React.ReactNode;
}) => (
  <div className="w-full h-full flex rounded-lg border border-[#525252] bg-[#24272E] overflow-hidden">
    {providersAreSet && <MicroagentManagementSidebar providers={providers} />}
    <div className="flex-1">
      <MicroagentManagementMain />
    </div>
    {modals}
  </div>
);
