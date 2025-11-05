import { QueryCache, MutationCache, QueryClient } from "@tanstack/react-query";
import i18next from "i18next";
import { AxiosError } from "axios";
import { I18nKey } from "#/i18n/declaration";
import { retrieveAxiosErrorMessage } from "./utils/retrieve-axios-error-message";
import { displayErrorToast } from "./utils/custom-toast-handlers";

const handle401Error = (error: AxiosError, queryClient: QueryClient) => {
  if (error?.response?.status === 401 || error?.status === 401) {
    queryClient.invalidateQueries({ queryKey: ["user", "authenticated"] });
  }
};

const shownErrors = new Set<string>();
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      const isAuthQuery =
        query.queryKey[0] === "user" && query.queryKey[1] === "authenticated";
      if (!isAuthQuery) {
        handle401Error(error, queryClient);
      }

      if (!query.meta?.disableToast) {
        const errorMessage = retrieveAxiosErrorMessage(error);

        if (!shownErrors.has(errorMessage || "")) {
          // Prefer using i18next.t with defaultValue so translation tooling recognizes the fallback
          displayErrorToast(
            i18next.t(I18nKey.ERROR$GENERIC, { defaultValue: errorMessage }),
          );
          shownErrors.add(errorMessage || "");

          setTimeout(() => {
            shownErrors.delete(errorMessage);
          }, 3000);
        }
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _, __, mutation) => {
      handle401Error(error, queryClient);

      if (!mutation?.meta?.disableToast) {
        const message = retrieveAxiosErrorMessage(error);
        displayErrorToast(
          i18next.t(I18nKey.ERROR$GENERIC, { defaultValue: message }),
        );
      }
    },
  }),
});
