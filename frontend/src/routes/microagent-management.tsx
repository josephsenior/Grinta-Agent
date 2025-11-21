import { queryClient } from "#/query-client-config";
import { GetConfigResponse } from "#/api/forge.types";
import Forge from "#/api/forge";
import { MicroagentManagementContent } from "#/components/features/microagent-management/microagent-management-content";
import { ConversationSubscriptionsProvider } from "#/context/conversation-subscriptions-provider";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";

export const clientLoader = async () => {
  let config = queryClient.getQueryData<GetConfigResponse>(["config"]);
  if (!config) {
    config = await Forge.getConfig();
    queryClient.setQueryData<GetConfigResponse>(["config"], config);
  }

  return null;
};

function MicroagentManagement() {
  return (
    <AuthGuard>
      <AppLayout>
        <div className="flex flex-col h-full min-h-0 space-y-6">
          {/* Page Title: Microagent Management */}
          <div>
            <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
              Repository Guides Management
            </h1>
          </div>

          {/* Microagent Management Content */}
          <div className="flex-1 min-h-0">
            <ConversationSubscriptionsProvider>
              <MicroagentManagementContent />
            </ConversationSubscriptionsProvider>
          </div>
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export default MicroagentManagement;
