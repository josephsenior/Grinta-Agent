import { X, ExternalLink, Download, Check, AlertCircle } from "lucide-react";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";
import { BrandButton } from "#/components/features/settings/brand-button";

interface MCPMarketplaceDetailsModalProps {
  mcp: MCPMarketplaceItem;
  isInstalled: boolean;
  onInstall: (mcp: MCPMarketplaceItem) => void;
  onClose: () => void;
}

export function MCPMarketplaceDetailsModal({
  mcp,
  isInstalled,
  onInstall,
  onClose,
}: MCPMarketplaceDetailsModalProps) {
  const handleInstall = () => {
    onInstall(mcp);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-background-secondary border border-border rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div className="flex items-start gap-4 flex-1">
            <div className="w-16 h-16 flex items-center justify-center text-4xl bg-background-tertiary rounded-lg border border-border flex-shrink-0">
              {mcp.icon || "📦"}
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-2xl font-bold text-foreground mb-1">
                {mcp.name}
              </h2>
              <p className="text-sm text-foreground-secondary mb-2">
                by {mcp.author}
              </p>
              <div className="flex flex-wrap gap-2">
                {mcp.featured && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-brand-500/20 text-brand-400 rounded-full border border-brand-500/30">
                    Featured
                  </span>
                )}
                {mcp.popular && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-accent-500/20 text-accent-400 rounded-full border border-accent-500/30">
                    Popular
                  </span>
                )}
                <span className="px-2 py-0.5 text-xs font-medium bg-background-tertiary text-foreground-secondary rounded-full border border-border">
                  {mcp.type.toUpperCase()}
                </span>
                {mcp.version && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-background-tertiary text-foreground-secondary rounded-full border border-border">
                    v{mcp.version}
                  </span>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-foreground-secondary hover:text-foreground transition-colors p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-2">
              Description
            </h3>
            <p className="text-sm text-foreground-secondary leading-relaxed">
              {mcp.longDescription || mcp.description}
            </p>
          </div>

          {/* Stats */}
          {(mcp.installCount || mcp.rating) && (
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-2">
                Statistics
              </h3>
              <div className="flex gap-6 text-sm">
                {mcp.installCount && (
                  <div>
                    <span className="text-foreground-secondary">
                      Downloads:{" "}
                    </span>
                    <span className="text-foreground font-medium">
                      {mcp.installCount.toLocaleString()}
                    </span>
                  </div>
                )}
                {mcp.rating && (
                  <div>
                    <span className="text-foreground-secondary">Rating: </span>
                    <span className="text-foreground font-medium">
                      ⭐ {mcp.rating.toFixed(1)} / 5.0
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tags */}
          {mcp.tags && mcp.tags.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-2">
                Tags
              </h3>
              <div className="flex flex-wrap gap-2">
                {mcp.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 text-xs bg-background-tertiary text-foreground-secondary rounded border border-border"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Configuration */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-2">
              Configuration
            </h3>
            <div className="bg-background-tertiary rounded-lg border border-border p-4 space-y-3">
              <div>
                <span className="text-xs text-foreground-secondary">Type:</span>
                <code className="ml-2 text-xs text-foreground font-mono">
                  {mcp.type}
                </code>
              </div>
              {mcp.config.command && (
                <div>
                  <span className="text-xs text-foreground-secondary">
                    Command:
                  </span>
                  <code className="ml-2 text-xs text-foreground font-mono">
                    {mcp.config.command}
                  </code>
                </div>
              )}
              {mcp.config.args && mcp.config.args.length > 0 && (
                <div>
                  <span className="text-xs text-foreground-secondary block mb-1">
                    Arguments:
                  </span>
                  <code className="text-xs text-foreground font-mono block bg-background-primary p-2 rounded border border-border">
                    {mcp.config.args.join(" ")}
                  </code>
                </div>
              )}
              {mcp.config.url && (
                <div>
                  <span className="text-xs text-foreground-secondary">
                    URL:
                  </span>
                  <code className="ml-2 text-xs text-foreground font-mono break-all">
                    {mcp.config.url}
                  </code>
                </div>
              )}
            </div>
          </div>

          {/* Requirements */}
          {mcp.config.requiresApiKey && (
            <div className="bg-warning-500/10 border border-warning-500/20 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-foreground mb-1">
                    API Key Required
                  </h4>
                  <p className="text-sm text-foreground-secondary">
                    {mcp.config.apiKeyDescription ||
                      "This MCP requires an API key to function. You'll need to configure it after installation."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Requirements */}
          {mcp.requirements && (
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-2">
                Requirements
              </h3>
              <div className="text-sm text-foreground-secondary space-y-1">
                {mcp.requirements.node && (
                  <div>Node.js: {mcp.requirements.node}</div>
                )}
                {mcp.requirements.python && (
                  <div>Python: {mcp.requirements.python}</div>
                )}
                {mcp.requirements.os && (
                  <div>OS: {mcp.requirements.os.join(", ")}</div>
                )}
                {mcp.requirements.other &&
                  mcp.requirements.other.map((req, i) => <div key={i}>{req}</div>)}
              </div>
            </div>
          )}

          {/* Links */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-2">
              Links
            </h3>
            <div className="flex flex-col gap-2">
              {mcp.homepage && (
                <a
                  href={mcp.homepage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-2"
                >
                  Homepage
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {mcp.repository && (
                <a
                  href={mcp.repository}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-2"
                >
                  Source Code
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {mcp.documentation && (
                <a
                  href={mcp.documentation}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-2"
                >
                  Documentation
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
          <BrandButton type="button" variant="secondary" onClick={onClose}>
            Close
          </BrandButton>
          <BrandButton
            type="button"
            variant={isInstalled ? "secondary" : "primary"}
            onClick={handleInstall}
            isDisabled={isInstalled}
          >
            {isInstalled ? (
              <>
                <Check className="w-4 h-4" />
                <span>Installed</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Install</span>
              </>
            )}
          </BrandButton>
        </div>
      </div>
    </div>
  );
}

