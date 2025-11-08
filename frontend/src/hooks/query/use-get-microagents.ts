import { useQuery } from "@tanstack/react-query";
import { useConversationId } from "../use-conversation-id";
import Forge from "#/api/forge";

export const useGetMicroagents = (microagentDirectory: string) => {
  const { conversationId } = useConversationId();

  return useQuery({
    queryKey: ["files", "microagents", conversationId, microagentDirectory],
    queryFn: () => Forge.getFiles(conversationId!, microagentDirectory),
    enabled: !!conversationId,
    select: (data) =>
      (data || []).map((fileName: any) => {
        const name = typeof fileName === "string" ? fileName : fileName?.path ?? "";
        return name.replace(microagentDirectory, "");
      }),
  });
};
