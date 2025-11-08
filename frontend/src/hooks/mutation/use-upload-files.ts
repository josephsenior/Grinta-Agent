import { useMutation } from "@tanstack/react-query";
import Forge from "#/api/forge";

export const useUploadFiles = () =>
  useMutation({
    mutationKey: ["upload-files"],
    mutationFn: (variables: { conversationId: string; files: File[] }) =>
      Forge.uploadFiles(variables.conversationId!, variables.files),
    onSuccess: async () => {},
    meta: {
      disableToast: true,
    },
  });
