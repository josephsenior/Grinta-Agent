import { useMutation } from "@tanstack/react-query";
import Forge from "#/api/forge";

export const useGetTrajectory = () =>
  useMutation({
    mutationFn: (cid: string) => Forge.getTrajectory(cid),
  });
