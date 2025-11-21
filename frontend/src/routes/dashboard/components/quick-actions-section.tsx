import { Sparkles, MessageSquare, FileText, DollarSign } from "lucide-react";
import { QuickActionButton } from "./quick-action-button";

interface QuickActionsSectionProps {
  onCreateConversation: () => void;
  onViewAllConversations: () => void;
  onViewAnalytics: () => void;
  onViewBilling: () => void;
  balance: number | undefined;
  quickActionsRef: React.RefObject<HTMLDivElement | null>;
}

export function QuickActionsSection({
  onCreateConversation,
  onViewAllConversations,
  onViewAnalytics,
  onViewBilling,
  balance,
  quickActionsRef,
}: QuickActionsSectionProps) {
  return (
    <div ref={quickActionsRef} className="space-y-3">
      <QuickActionButton
        icon={Sparkles}
        title="New Conversation"
        description="Start a new AI-powered conversation"
        onClick={onCreateConversation}
        variant="primary"
      />
      <QuickActionButton
        icon={MessageSquare}
        title="View All"
        description="See all your conversations"
        onClick={onViewAllConversations}
      />
      <QuickActionButton
        icon={FileText}
        title="View Analytics"
        description="See detailed usage and performance metrics"
        onClick={onViewAnalytics}
      />
      {balance !== undefined && (
        <QuickActionButton
          icon={DollarSign}
          title="Manage Billing"
          description="Add credits and manage subscription"
          onClick={onViewBilling}
        />
      )}
    </div>
  );
}
