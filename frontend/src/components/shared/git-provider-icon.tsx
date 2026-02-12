import { Github } from "lucide-react";
import { Provider } from "#/types/settings";

interface GitProviderIconProps {
  gitProvider: Provider;
}

export function GitProviderIcon({ gitProvider }: GitProviderIconProps) {
  return (
    <>
      {gitProvider === "github" && <Github size={14} />}
    </>
  );
}
