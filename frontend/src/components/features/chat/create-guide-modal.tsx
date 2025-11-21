import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { FaCircleInfo } from "react-icons/fa6";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { BrandButton } from "../settings/brand-button";
import { I18nKey } from "#/i18n/declaration";
import XIcon from "#/icons/x.svg?react";
import { cn, getPR, getPRShort } from "#/utils/utils";
import { BadgeInput } from "#/components/shared/inputs/badge-input";
import { useActiveConversation } from "#/hooks/query/use-active-conversation";
import { useCreateConversationAndSubscribeMultiple } from "#/hooks/use-create-conversation-and-subscribe-multiple";
import { Provider } from "#/types/settings";
import { queryClient } from "#/query-client-config";
import { displaySuccessToast } from "#/utils/custom-toast-handlers";

interface CreateGuideModalProps {
  onClose: () => void;
  guideToEdit?: {
    name: string;
    path?: string;
  } | null;
}

export function CreateGuideModal({
  onClose,
  guideToEdit = null,
}: CreateGuideModalProps) {
  const { t } = useTranslation();
  const { data: conversation } = useActiveConversation();
  const { createConversationAndSubscribe, isPending } =
    useCreateConversationAndSubscribeMultiple();

  const [triggers, setTriggers] = useState<string[]>([]);
  const [query, setQuery] = useState<string>("");

  const selectedRepository = conversation?.selected_repository;
  const gitProvider = (conversation?.git_provider as Provider) || "github";

  const isUpdate = Boolean(guideToEdit);

  // TODO: Load existing guide content when editing
  // For now, we'll just use the form fields

  const modalTitle = useMemo(() => {
    if (isUpdate) {
      return "Update Repository Guide";
    }
    if (selectedRepository) {
      return `Add Guide to ${selectedRepository}`;
    }
    return "Create Repository Guide";
  }, [isUpdate, selectedRepository]);

  const modalDescription = useMemo(() => {
    if (isUpdate) {
      return "Update the guide instructions and triggers for this repository.";
    }
    return "Create a new guide that provides instructions for working with this repository. Guides are stored in the .Forge/microagents folder.";
  }, [isUpdate]);

  const handleConfirm = () => {
    if (!query.trim() || !selectedRepository) {
      return;
    }

    const repositoryName = selectedRepository;
    const isGitLab = gitProvider === "gitlab";
    const pr = getPR(isGitLab);
    const prShort = getPRShort(isGitLab);

    const conversationInstructions = isUpdate
      ? `Update the repository guide for ${repositoryName} by following the steps below:

- Step 1: Update the guide. This is the path of the guide: ${guideToEdit?.path || ""} (The updated guide must be in the .Forge/microagents folder and should be able to perform the described task when triggered). This is the updated instructions about what the guide should do: ${query.trim()}. ${
          triggers.length > 0
            ? `This is the triggers of the guide: ${triggers.join(", ")}`
            : "Please be noted that the guide doesn't have any triggers."
        }

- Step 2: Create a new branch for the repository ${repositoryName}, must avoid duplicated branches.

- Step 3: Please push the changes to your branch and create a ${pr}. Please create a meaningful branch name that describes the changes. If a ${pr} template exists in the repository, please follow it when creating the ${prShort} description.`
      : `Create a repository guide for ${repositoryName} by following the steps below:

- Step 1: Create a markdown file inside the .Forge/microagents folder with the name of the guide (The guide must be created in the .Forge/microagents folder and should be able to perform the described task when triggered). This is the instructions about what the guide should do: ${query.trim()}. ${
          triggers.length > 0
            ? `This is the triggers of the guide: ${triggers.join(", ")}`
            : "Please be noted that the guide doesn't have any triggers."
        }

- Step 2: Create a new branch for the repository ${repositoryName}, must avoid duplicated branches.

- Step 3: Please push the changes to your branch and create a ${pr}. Please create a meaningful branch name that describes the changes. If a ${pr} template exists in the repository, please follow it when creating the ${prShort} description.`;

    const createGuide = {
      repo: repositoryName,
      git_provider: gitProvider,
      title: query.trim(),
    };

    createConversationAndSubscribe({
      query: conversationInstructions,
      conversationInstructions,
      repository: {
        name: repositoryName,
        gitProvider,
      },
      createMicroagent: createGuide,
      onSuccessCallback: () => {
        // Invalidate guides query
        const [owner, repo] = repositoryName.split("/");
        queryClient.invalidateQueries({
          queryKey: ["repository", "microagents", owner, repo],
        });

        displaySuccessToast(
          isUpdate
            ? "Guide update started! Check the conversation for progress."
            : "Guide creation started! Check the conversation for progress.",
        );

        onClose();
      },
    });
  };

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleConfirm();
  };

  return (
    <ModalBackdrop onClose={onClose}>
      <ModalBody className="items-start rounded-[12px] p-6 min-w-[611px]">
        <div className="flex flex-col gap-2 w-full">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <h2 className="text-white text-xl font-medium">{modalTitle}</h2>
              <a
                href="https://docs.all-hands.dev/usage/prompting/microagents-overview#microagents-overview"
                target="_blank"
                rel="noopener noreferrer"
              >
                <FaCircleInfo className="text-primary" />
              </a>
            </div>
            <button type="button" onClick={onClose} className="cursor-pointer">
              <XIcon width={24} height={24} color="#F9FBFE" />
            </button>
          </div>
          <span className="text-white text-sm font-normal">
            {modalDescription}
          </span>
        </div>
        <form
          data-testid="create-guide-modal"
          onSubmit={onSubmit}
          className="flex flex-col gap-6 w-full"
        >
          <label
            htmlFor="query-input"
            className="flex flex-col gap-2 w-full text-sm font-normal"
          >
            {t("guides.create.whatShouldGuideDo", "What should this guide do?")}
            <textarea
              required
              data-testid="query-input"
              name="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t(
                "guides.create.descriptionPlaceholder",
                "Describe what this guide should help with (e.g., 'How to build and test this project', 'Deployment procedures', etc.)",
              )}
              rows={6}
              className={cn(
                "bg-background-glass backdrop-blur-xl border border-border-glass w-full rounded-xl p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary resize-none transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
                "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
              )}
            />
          </label>
          <label
            htmlFor="trigger-input"
            className="flex flex-col gap-2.5 w-full text-sm"
          >
            <div className="flex items-center gap-2">
              {t("guides.create.addTriggers", "Add Triggers (Optional)")}
              <a
                href="https://docs.all-hands.dev/usage/prompting/microagents-keyword"
                target="_blank"
                rel="noopener noreferrer"
              >
                <FaCircleInfo className="text-primary" />
              </a>
            </div>
            <BadgeInput
              name="trigger-input"
              value={triggers}
              placeholder={t(
                "guides.create.triggerPlaceholder",
                "Type trigger and press space",
              )}
              onChange={setTriggers}
            />
            <span className="text-xs text-white/60 font-normal">
              {t(
                "guides.create.triggersDescription",
                "Keywords that will automatically load this guide when mentioned in conversations.",
              )}
            </span>
          </label>
        </form>
        <div
          className="flex items-center justify-end gap-2 w-full"
          onClick={(event) => event.stopPropagation()}
        >
          <BrandButton
            type="button"
            variant="secondary"
            onClick={onClose}
            testId="cancel-button"
          >
            {t(I18nKey.BUTTON$CANCEL)}
          </BrandButton>
          <BrandButton
            type="button"
            variant="primary"
            onClick={handleConfirm}
            testId="confirm-button"
            isDisabled={!query.trim() || isPending}
          >
            {isPending ? t(I18nKey.HOME$LOADING) : "Create Guide"}
          </BrandButton>
        </div>
      </ModalBody>
    </ModalBackdrop>
  );
}
