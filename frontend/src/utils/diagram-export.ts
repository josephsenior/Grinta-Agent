/**
 * Utilities for exporting Mermaid diagrams as PNG, SVG, or source code
 */

/**
 * Download a string as a file
 */
function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export Mermaid diagram as SVG
 */
export function exportDiagramAsSVG(
  svgElement: SVGElement | null,
  filename: string = "diagram.svg",
) {
  if (!svgElement) {
    throw new Error("No SVG element found");
  }

  // Clone the SVG to avoid modifying the original
  const clonedSvg = svgElement.cloneNode(true) as SVGElement;

  // Add XML namespace if not present
  if (!clonedSvg.getAttribute("xmlns")) {
    clonedSvg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  }

  // Serialize the SVG
  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(clonedSvg);

  // Download as file
  downloadFile(svgString, filename, "image/svg+xml");
}

/**
 * Export Mermaid diagram as PNG
 */
export async function exportDiagramAsPNG(
  svgElement: SVGElement | null,
  filename: string = "diagram.png",
  scale: number = 2, // Higher scale = better quality
): Promise<void> {
  if (!svgElement) {
    throw new Error("No SVG element found");
  }

  return new Promise((resolve, reject) => {
    try {
      // Get SVG dimensions
      let width = 0;
      let height = 0;
      if (
        svgElement &&
        "getBBox" in svgElement &&
        typeof (svgElement as SVGGraphicsElement).getBBox === "function"
      ) {
        const svgGraphics = svgElement as SVGGraphicsElement;
        const bbox = svgGraphics.getBBox();
        width = bbox.width;
        height = bbox.height;
      } else {
        // Fallback: estimate from bounding client rect
        const rect = (svgElement as Element)?.getBoundingClientRect?.();
        width = rect?.width ?? 0;
        height = rect?.height ?? 0;
      }

      // Create canvas
      const canvas = document.createElement("canvas");
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext("2d");

      if (!ctx) {
        reject(new Error("Could not get canvas context"));
        return;
      }

      // Scale context for better quality
      ctx.scale(scale, scale);

      // Set white background
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);

      // Serialize SVG
      const serializer = new XMLSerializer();
      const svgString = serializer.serializeToString(svgElement);

      // Create image from SVG
      const img = new Image();
      const blob = new Blob([svgString], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);

      img.onload = () => {
        // Draw image to canvas
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);

        // Convert canvas to PNG and download
        canvas.toBlob((pngBlob) => {
          if (pngBlob) {
            const pngUrl = URL.createObjectURL(pngBlob);
            const link = document.createElement("a");
            link.href = pngUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(pngUrl);
            resolve();
          } else {
            reject(new Error("Failed to create PNG blob"));
          }
        }, "image/png");
      };

      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Failed to load SVG image"));
      };

      img.src = url;
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Export Mermaid source code to clipboard
 */
export async function copyMermaidSource(mermaidCode: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(mermaidCode);
  } catch (error) {
    // Fallback for older browsers
    const textarea = document.createElement("textarea");
    textarea.value = mermaidCode;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }
}

/**
 * Download Mermaid source code as .mmd file
 */
export function downloadMermaidSource(
  mermaidCode: string,
  filename: string = "diagram.mmd",
) {
  downloadFile(mermaidCode, filename, "text/plain");
}

/**
 * Copy SVG to clipboard (useful for pasting into design tools)
 */
export async function copySVGToClipboard(
  svgElement: SVGElement | null,
): Promise<void> {
  if (!svgElement) {
    throw new Error("No SVG element found");
  }

  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svgElement);

  try {
    await navigator.clipboard.writeText(svgString);
  } catch (error) {
    throw new Error("Failed to copy SVG to clipboard");
  }
}

/**
 * Get file size estimate for display purposes
 */
export function estimateFileSize(svgElement: SVGElement | null): string {
  if (!svgElement) return "0 KB";

  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svgElement);
  const sizeInBytes = new Blob([svgString]).size;

  if (sizeInBytes < 1024) {
    return `${sizeInBytes} B`;
  }
  if (sizeInBytes < 1024 * 1024) {
    return `${(sizeInBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`;
}
