import React from "react";
import ReactJsonView from "@microlink/react-json-view";
import { useTranslation } from "react-i18next";
import { MCPObservation } from "#/types/core/observations";
import { hasExtras } from "#/types/core/guards";
import { JSON_VIEW_THEME } from "#/utils/constants";

interface MCPObservationContentProps {
  event: MCPObservation;
}

export function MCPObservationContent({ event }: MCPObservationContentProps) {
  const { t } = useTranslation();

  // Parse the content as JSON if possible
  let outputData: unknown = event.content;
  if (typeof event.content === "string") {
    try {
      outputData = JSON.parse(event.content);
    } catch {
      outputData = event.content;
    }
  }

  const extras = hasExtras(event) ? event.extras : ({} as Record<string, unknown>);
  const maybeArgs = (typeof extras === "object" && extras !== null && "arguments" in extras) ? (extras as Record<string, unknown>)["arguments"] : undefined;
  const hasArguments = Boolean(maybeArgs && typeof maybeArgs === "object" && Object.keys(maybeArgs as Record<string, unknown>).length > 0);

  return (
    <div className="flex flex-col gap-4">
      {/* Arguments section */}
      {hasArguments && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground-secondary">
              {t("MCP_OBSERVATION$ARGUMENTS")}
            </h3>
          </div>
          <div className="p-3 bg-background-secondary rounded-md overflow-auto text-foreground-secondary max-h-[200px] shadow-inner">
            <ReactJsonView
              name={false}
              src={typeof maybeArgs === "object" && maybeArgs !== null ? (maybeArgs as Record<string, unknown>) : {}}
              theme={JSON_VIEW_THEME}
              collapsed={1}
              displayDataTypes={false}
            />
          </div>
        </div>
      )}

      {/* Output section */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground-secondary">
            {t("MCP_OBSERVATION$OUTPUT")}
          </h3>
        </div>
        <div className="p-3 bg-background-secondary rounded-md overflow-auto text-foreground-secondary max-h-[300px] shadow-inner">
          {typeof outputData === "object" && outputData !== null ? (
            <ReactJsonView
              name={false}
              src={outputData}
              theme={JSON_VIEW_THEME}
              collapsed={1}
              displayDataTypes={false}
            />
          ) : (
            <pre className="whitespace-pre-wrap">
              {t("OBSERVATION$MCP_NO_OUTPUT", {
                defaultValue: String(event.content || "").trim() || "",
              })}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
