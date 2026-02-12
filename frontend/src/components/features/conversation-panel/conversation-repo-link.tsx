import { Github } from "lucide-react";
import { RepositorySelection } from "#/api/forge.types";

interface ConversationRepoLinkProps {
  selectedRepository: RepositorySelection;
  variant: "compact" | "default";
}

export function ConversationRepoLink({
  selectedRepository,
  variant = "default",
}: ConversationRepoLinkProps) {
  if (variant === "compact") {
    return (
      <span
        data-testid="conversation-card-selected-repository"
        className="text-xs text-foreground-secondary"
      >
        {selectedRepository.selected_repository}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1">
      {selectedRepository.git_provider === "github" && (
        <Github size={14} className="text-foreground-secondary" />
      )}

      <span
        data-testid="conversation-card-selected-repository"
        className="text-xs text-foreground-secondary"
      >
        {selectedRepository.selected_repository}
      </span>
      <code
        data-testid="conversation-card-selected-branch"
        className="text-xs text-foreground-secondary border border-border rounded px-1 py-0.5 w-fit bg-background-tertiary"
      >
        {selectedRepository.selected_branch}
      </code>
    </div>
  );
}
