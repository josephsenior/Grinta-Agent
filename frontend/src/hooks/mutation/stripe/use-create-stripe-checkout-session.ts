import { useMutation } from "@tanstack/react-query";
import Forge from "#/api/forge";

export const useCreateStripeCheckoutSession = () =>
  useMutation({
    mutationFn: async (variables: { amount: number }) => {
      const redirectUrl = await Forge.createCheckoutSession(variables.amount);
      window.location.href = redirectUrl;
    },
  });
