/**
 * Enhanced node interactions: animations, tooltips, hover effects
 */

import { OrchestrationStep } from "#/hooks/use-metasop-orchestration";

/**
 * Apply live animations to diagram nodes based on step status
 */
export function applyNodeAnimations(
  svgElement: SVGElement,
  steps: OrchestrationStep[],
): void {
  steps.forEach((step) => {
    // Find the node element
    const nodeElements = svgElement.querySelectorAll(`[id*="${step.step_id}"]`);

    nodeElements.forEach((node) => {
      const element = node as HTMLElement;

      // Remove previous animation classes
      element.classList.remove(
        "node-running",
        "node-completed",
        "node-failed",
        "node-pending",
      );

      // Apply animation based on status
      switch (step.status) {
        case "running":
          element.classList.add("node-running");
          break;
        case "success":
          element.classList.add("node-completed");
          // Remove animation after it completes
          setTimeout(() => {
            element.classList.remove("node-completed");
          }, 600);
          break;
        case "failed":
          element.classList.add("node-failed");
          break;
        default:
          element.classList.add("node-pending");
      }
    });
  });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Generate status badge HTML
 */
function getStatusBadge(status: string): string {
  const statusColors: Record<string, string> = {
    running: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    success: "bg-green-500/20 text-green-400 border-green-500/30",
    failed: "bg-red-500/20 text-red-400 border-red-500/30",
    pending: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  };

  const colorClass = statusColors[status] || statusColors.pending;
  const label = status.charAt(0).toUpperCase() + status.slice(1);

  return `<span class="px-2 py-0.5 rounded-full text-xs font-medium border ${colorClass}">${label}</span>`;
}

/**
 * Create and show tooltip on node hover
 */
export function createNodeTooltip(
  step: OrchestrationStep,
  anchorElement: HTMLElement,
): HTMLElement {
  const tooltip = document.createElement("div");
  tooltip.className =
    "absolute z-50 bg-background-secondary dark:bg-background-tertiary text-white px-4 py-3 rounded-lg shadow-2xl text-sm max-w-xs animate-scale-in border border-border";

  // Format timestamp
  const timeStr = step.timestamp
    ? new Date(step.timestamp).toLocaleTimeString()
    : "";

  // Build tooltip content
  tooltip.innerHTML = `
    <div class="space-y-2">
      <div class="flex items-center justify-between gap-3">
        <strong class="text-base">${escapeHtml(step.role)}</strong>
        ${getStatusBadge(step.status)}
      </div>
      
      ${
        step.step_id
          ? `
        <div class="text-xs text-foreground-secondary">
          ID: <span class="text-foreground-secondary">${escapeHtml(step.step_id)}</span>
        </div>
      `
          : ""
      }
      
      ${
        timeStr
          ? `
        <div class="text-xs text-foreground-secondary">
          Time: <span class="text-foreground-secondary">${timeStr}</span>
        </div>
      `
          : ""
      }
      
      ${
        step.error
          ? `
        <div class="text-xs text-error-500 mt-2 p-2 bg-error-500/10 rounded border border-error-500/20">
          ⚠️ ${escapeHtml(step.error)}
        </div>
      `
          : ""
      }
      
      ${
        step.artifact
          ? `
        <div class="text-xs text-foreground-secondary mt-2">
          <span class="text-success-500">✓</span> Artifact available
        </div>
      `
          : ""
      }
    </div>
  `;

  // Position tooltip
  const rect = anchorElement.getBoundingClientRect();
  tooltip.style.position = "fixed";
  tooltip.style.left = `${rect.left + rect.width / 2}px`;
  tooltip.style.top = `${rect.bottom + 8}px`;
  tooltip.style.transform = "translateX(-50%)";

  // Adjust if tooltip goes off-screen
  document.body.appendChild(tooltip);
  const tooltipRect = tooltip.getBoundingClientRect();

  if (tooltipRect.right > window.innerWidth) {
    tooltip.style.left = `${window.innerWidth - tooltipRect.width - 10}px`;
    tooltip.style.transform = "none";
  }

  if (tooltipRect.bottom > window.innerHeight) {
    tooltip.style.top = `${rect.top - tooltipRect.height - 8}px`;
  }

  return tooltip;
}

/**
 * Attach tooltip handlers to nodes
 */
export function attachNodeTooltips(
  svgElement: SVGElement,
  steps: OrchestrationStep[],
): void {
  steps.forEach((step) => {
    const nodeElements = svgElement.querySelectorAll(`[id*="${step.step_id}"]`);

    nodeElements.forEach((node) => {
      const element = node as HTMLElement;
      let tooltip: HTMLElement | null = null;
      let hideTimeout: number | undefined;

      element.addEventListener("mouseenter", () => {
        // Clear any pending hide
        if (hideTimeout) window.clearTimeout(hideTimeout);

        // Create tooltip
        tooltip = createNodeTooltip(step, element);
        if (tooltip) {
          tooltip.addEventListener("mouseenter", () => {
            if (hideTimeout) window.clearTimeout(hideTimeout);
          });

          tooltip.addEventListener("mouseleave", () => {
            if (tooltip) {
              tooltip.remove();
              tooltip = null;
            }
          });
        }
      });

      element.addEventListener("mouseleave", () => {
        // Delay hiding to allow moving to tooltip
        hideTimeout = window.setTimeout(() => {
          if (tooltip) {
            tooltip.remove();
            tooltip = null;
          }
        }, 100);
      });
    });
  });
}

/**
 * Add hover highlight effect to nodes
 */
export function attachNodeHighlight(svgElement: SVGElement): void {
  const nodes = svgElement.querySelectorAll('[id^="flowchart-"]');

  nodes.forEach((node) => {
    const element = node as HTMLElement;

    element.addEventListener("mouseenter", () => {
      // Brighten on hover
      element.style.filter = "brightness(1.15)";
      element.style.transition = "filter 0.2s ease-in-out";
    });

    element.addEventListener("mouseleave", () => {
      // Reset
      element.style.filter = "";
    });
  });
}

/**
 * Apply all enhancements at once
 */
export function applyAllNodeEnhancements(
  svgElement: SVGElement,
  steps: OrchestrationStep[],
  onNodeClick?: (stepId: string) => void,
): void {
  // Apply animations
  applyNodeAnimations(svgElement, steps);

  // Attach tooltips
  attachNodeTooltips(svgElement, steps);

  // Add highlight effect
  attachNodeHighlight(svgElement);

  // Add click handlers
  if (onNodeClick) {
    steps.forEach((step) => {
      const nodeElements = svgElement.querySelectorAll(
        `[id*="${step.step_id}"]`,
      );

      nodeElements.forEach((node) => {
        const element = node as HTMLElement;
        element.style.cursor = "pointer";

        element.addEventListener("click", () => {
          onNodeClick(step.step_id);
        });
      });
    });
  }
}
