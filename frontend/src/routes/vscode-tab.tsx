import React from "react";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";
import { useVSCodeUrl } from "#/hooks/query/use-vscode-url";
import { LoadingView } from "./vscode-tab/loading-view";
import { ErrorView } from "./vscode-tab/error-view";
import { CrossOriginView } from "./vscode-tab/cross-origin-view";
import { IframeView } from "./vscode-tab/iframe-view";
import { RuntimeInactiveView } from "./vscode-tab/runtime-inactive-view";
import { useVSCodeProtocol } from "./vscode-tab/use-vscode-protocol";
import { hasVSCodeError } from "./vscode-tab/use-vscode-error-check";

function VSCodeTab() {
  const { data, isLoading, error } = useVSCodeUrl();
  const isRuntimeInactive = !useRuntimeIsReady();
  const { isCrossProtocol, iframeError } = useVSCodeProtocol(
    data?.url ?? undefined,
  );

  if (isRuntimeInactive) {
    return <RuntimeInactiveView />;
  }

  if (isLoading) {
    return <LoadingView />;
  }

  if (
    hasVSCodeError(
      error,
      data?.error ?? undefined,
      data?.url ?? undefined,
      iframeError,
    )
  ) {
    return (
      <ErrorView
        error={error}
        dataError={data?.error ?? undefined}
        iframeError={iframeError}
      />
    );
  }

  if (isCrossProtocol && data?.url) {
    return <CrossOriginView url={data.url} />;
  }

  if (data?.url) {
    return <IframeView url={data.url} />;
  }

  return (
    <ErrorView
      error={error}
      dataError={data?.error ?? undefined}
      iframeError={iframeError}
    />
  );
}

// Export the VSCodeTab directly since we're using the provider at a higher level
export default VSCodeTab;
