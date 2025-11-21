import React from "react";
import ReactJsonView from "@microlink/react-json-view";
import { MCPObservation } from "#/types/core/observations";
import { hasExtras } from "#/types/core/guards";
import { JSON_VIEW_THEME } from "#/utils/constants";

function parseObservationOutput(content: unknown) {
  if (typeof content !== "string") {
    return content;
  }

  try {
    return JSON.parse(content);
  } catch {
    return content;
  }
}

function extractObservationArguments(event: MCPObservation) {
  const extras = hasExtras(event) ? event.extras : {};
  if (!extras || typeof extras !== "object" || !("arguments" in extras)) {
    return { argumentsObject: {}, hasArguments: false } as const;
  }

  const args = (extras as Record<string, unknown>).arguments;
  if (!args || typeof args !== "object") {
    return { argumentsObject: {}, hasArguments: false } as const;
  }

  const castedArgs = args as Record<string, unknown>;
  return {
    argumentsObject: castedArgs,
    hasArguments: Object.keys(castedArgs).length > 0,
  } as const;
}

function useMcpObservationData(event: MCPObservation) {
  return React.useMemo(() => {
    const output = parseObservationOutput(event.content);
    const { argumentsObject, hasArguments } =
      extractObservationArguments(event);

    return {
      output,
      argumentsObject,
      hasArguments,
      fallbackText: String(event.content || "").trim(),
    } as const;
  }, [event]);
}

function ArgumentsSection({
  argumentsObject,
  label,
}: {
  argumentsObject: Record<string, unknown>;
  label: string;
}) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground-secondary">
          {label}
        </h3>
      </div>
      <div className="p-3 bg-background-secondary rounded-md overflow-auto text-foreground-secondary max-h-[200px] shadow-inner">
        <ReactJsonView
          name={false}
          src={argumentsObject}
          theme={JSON_VIEW_THEME}
          collapsed={1}
          displayDataTypes={false}
        />
      </div>
    </section>
  );
}

function OutputSection({
  output,
  fallback,
  label,
}: {
  output: unknown;
  fallback: string;
  label: string;
}) {
  const isRenderableObject = typeof output === "object" && output !== null;

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground-secondary">
          {label}
        </h3>
      </div>
      <div className="p-3 bg-background-secondary rounded-md overflow-auto text-foreground-secondary max-h-[300px] shadow-inner">
        {isRenderableObject ? (
          <ReactJsonView
            name={false}
            src={output as Record<string, unknown>}
            theme={JSON_VIEW_THEME}
            collapsed={1}
            displayDataTypes={false}
          />
        ) : (
          <pre className="whitespace-pre-wrap">{fallback}</pre>
        )}
      </div>
    </section>
  );
}

export function MCPObservationContent({ event }: { event: MCPObservation }) {
  const { output, argumentsObject, hasArguments, fallbackText } =
    useMcpObservationData(event);

  return (
    <div className="flex flex-col gap-4">
      {hasArguments && (
        <ArgumentsSection argumentsObject={argumentsObject} label="Arguments" />
      )}
      <OutputSection output={output} fallback={fallbackText} label="Output" />
    </div>
  );
}
