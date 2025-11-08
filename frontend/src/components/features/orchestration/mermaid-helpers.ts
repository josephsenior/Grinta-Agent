type MermaidModule = typeof import("mermaid").default;

let cachedMermaid: MermaidModule | null = null;
let initializationPromise: Promise<MermaidModule> | null = null;

const MERMAID_CONFIG = {
  startOnLoad: false,
  theme: "dark",
  securityLevel: "strict" as const,
  fontFamily: "ui-sans-serif, system-ui, sans-serif",
  themeVariables: {
    primaryColor: "#8b5cf6",
    primaryTextColor: "#e5e7eb",
    primaryBorderColor: "#7c3aed",
    lineColor: "#6b7280",
    secondaryColor: "#1f2937",
    tertiaryColor: "#111827",
    background: "#000000",
    mainBkg: "#1f2937",
    secondBkg: "#374151",
    border1: "#4b5563",
    border2: "#6b7280",
    note: "#374151",
    noteBorder: "#6b7280",
    noteBkg: "#1f2937",
    noteText: "#e5e7eb",
    text: "#e5e7eb",
    critical: "#ef4444",
    done: "#10b981",
    active: "#8b5cf6",
    grid: "#374151",
    nodeBorder: "#6b7280",
    clusterBkg: "#1f2937",
    clusterBorder: "#4b5563",
    titleColor: "#e5e7eb",
    edgeLabelBackground: "#1f2937",
    actorBorder: "#6b7280",
    actorBkg: "#374151",
    actorTextColor: "#e5e7eb",
    actorLineColor: "#6b7280",
    signalColor: "#e5e7eb",
    signalTextColor: "#111827",
    labelBoxBkgColor: "#374151",
    labelBoxBorderColor: "#6b7280",
    labelTextColor: "#e5e7eb",
    loopTextColor: "#e5e7eb",
    activationBorderColor: "#6b7280",
    activationBkgColor: "#374151",
    sequenceNumberColor: "#111827",
  },
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: "basis" as const,
  },
};

export async function ensureMermaid(): Promise<MermaidModule> {
  if (cachedMermaid) {
    return cachedMermaid;
  }

  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = import("mermaid")
    .then((module) => {
      const mermaid = module.default;
      mermaid.initialize(MERMAID_CONFIG);
      cachedMermaid = mermaid;
      return mermaid;
    })
    .catch((error) => {
      cachedMermaid = null;
      initializationPromise = null;
      throw error;
    });

  return initializationPromise;
}

export function resetMermaidCache(): void {
  cachedMermaid = null;
  initializationPromise = null;
}


