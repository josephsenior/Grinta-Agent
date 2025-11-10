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

  const badges = buildMcpBadges(mcp);
  const stats = buildMcpStats(mcp);
  const configSections = buildConfigSections(mcp);
  const requirements = buildRequirements(mcp);
  const links = buildExternalLinks(mcp);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-background-secondary border border-border rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <ModalHeader mcp={mcp} badges={badges} onClose={onClose} />
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <DescriptionSection
            description={mcp.longDescription || mcp.description}
          />
          <StatsSection stats={stats} />
          <TagsSection tags={mcp.tags} />
          <ConfigurationSection sections={configSections} />
          <ApiKeyRequirement
            requiresApiKey={mcp.config.requiresApiKey ?? false}
            description={mcp.config.apiKeyDescription}
          />
          <RequirementsSection requirements={requirements} />
          <LinksSection links={links} />
        </div>
        <ModalFooter
          isInstalled={isInstalled}
          onInstall={handleInstall}
          onClose={onClose}
        />
      </div>
    </div>
  );
}

type Badge = { label: string; className: string };

type StatDisplay = { label: string; value: string };

type ConfigSection = {
  label: string;
  value: string;
  isBlock?: boolean;
};

type RequirementDisplay = { label: string; value: string };

type LinkDisplay = { label: string; url: string };

function buildMcpBadges(mcp: MCPMarketplaceItem): Badge[] {
  const badges: Badge[] = [];
  if (mcp.featured) {
    badges.push({
      label: "Featured",
      className:
        "px-2 py-0.5 text-xs font-medium bg-brand-500/20 text-brand-400 rounded-full border border-brand-500/30",
    });
  }
  if (mcp.popular) {
    badges.push({
      label: "Popular",
      className:
        "px-2 py-0.5 text-xs font-medium bg-accent-500/20 text-accent-400 rounded-full border border-accent-500/30",
    });
  }
  badges.push({
    label: mcp.type.toUpperCase(),
    className:
      "px-2 py-0.5 text-xs font-medium bg-background-tertiary text-foreground-secondary rounded-full border border-border",
  });
  if (mcp.version) {
    badges.push({
      label: `v${mcp.version}`,
      className:
        "px-2 py-0.5 text-xs font-medium bg-background-tertiary text-foreground-secondary rounded-full border border-border",
    });
  }
  return badges;
}

function buildMcpStats(mcp: MCPMarketplaceItem): StatDisplay[] {
  const stats: StatDisplay[] = [];
  if (mcp.installCount) {
    stats.push({
      label: "Downloads",
      value: mcp.installCount.toLocaleString(),
    });
  }
  if (mcp.rating) {
    stats.push({
      label: "Rating",
      value: `⭐ ${mcp.rating.toFixed(1)} / 5.0`,
    });
  }
  return stats;
}

function buildConfigSections(mcp: MCPMarketplaceItem): ConfigSection[] {
  const sections: ConfigSection[] = [
    {
      label: "Type:",
      value: mcp.type,
    },
  ];

  if (mcp.config.command) {
    sections.push({
      label: "Command:",
      value: mcp.config.command,
    });
  }

  if (mcp.config.args && mcp.config.args.length > 0) {
    sections.push({
      label: "Arguments:",
      value: mcp.config.args.join(" "),
      isBlock: true,
    });
  }

  if (mcp.config.url) {
    sections.push({
      label: "URL:",
      value: mcp.config.url,
    });
  }

  return sections;
}

function buildRequirements(mcp: MCPMarketplaceItem): RequirementDisplay[] {
  if (!mcp.requirements) {
    return [];
  }

  const requirements: RequirementDisplay[] = [];
  if (mcp.requirements.node) {
    requirements.push({ label: "Node.js", value: mcp.requirements.node });
  }
  if (mcp.requirements.python) {
    requirements.push({ label: "Python", value: mcp.requirements.python });
  }
  if (mcp.requirements.os) {
    requirements.push({ label: "OS", value: mcp.requirements.os.join(", ") });
  }
  if (mcp.requirements.other) {
    mcp.requirements.other.forEach((value) => {
      requirements.push({ label: "Other", value });
    });
  }

  return requirements;
}

function buildExternalLinks(mcp: MCPMarketplaceItem): LinkDisplay[] {
  const links: LinkDisplay[] = [];
  if (mcp.homepage) {
    links.push({ label: "Homepage", url: mcp.homepage });
  }
  if (mcp.repository) {
    links.push({ label: "Source Code", url: mcp.repository });
  }
  if (mcp.documentation) {
    links.push({ label: "Documentation", url: mcp.documentation });
  }
  return links;
}

function ModalHeader({
  mcp,
  badges,
  onClose,
}: {
  mcp: MCPMarketplaceItem;
  badges: Badge[];
  onClose: () => void;
}) {
  return (
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
            {badges.map((badge) => (
              <span key={badge.label} className={badge.className}>
                {badge.label}
              </span>
            ))}
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
  );
}

function DescriptionSection({ description }: { description: string }) {
  if (!description) {
    return null;
  }

  return (
    <section>
      <SectionTitle>Description</SectionTitle>
      <p className="text-sm text-foreground-secondary leading-relaxed">
        {description}
      </p>
    </section>
  );
}

function StatsSection({ stats }: { stats: StatDisplay[] }) {
  if (stats.length === 0) {
    return null;
  }

  return (
    <section>
      <SectionTitle>Statistics</SectionTitle>
      <div className="flex gap-6 text-sm">
        {stats.map((stat) => (
          <div key={stat.label}>
            <span className="text-foreground-secondary">{stat.label}: </span>
            <span className="text-foreground font-medium">{stat.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function TagsSection({ tags }: { tags?: string[] }) {
  if (!tags || tags.length === 0) {
    return null;
  }

  return (
    <section>
      <SectionTitle>Tags</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-1 text-xs bg-background-tertiary text-foreground-secondary rounded border border-border"
          >
            {tag}
          </span>
        ))}
      </div>
    </section>
  );
}

function ConfigurationSection({ sections }: { sections: ConfigSection[] }) {
  if (sections.length === 0) {
    return null;
  }

  return (
    <section>
      <SectionTitle>Configuration</SectionTitle>
      <div className="bg-background-tertiary rounded-lg border border-border p-4 space-y-3">
        {sections.map((section) => (
          <div key={section.label}>
            <span className="text-xs text-foreground-secondary">
              {section.label}
            </span>
            <code
              className={`ml-2 text-xs text-foreground font-mono ${
                section.isBlock
                  ? "block bg-background-primary p-2 rounded border border-border mt-1"
                  : ""
              }`}
            >
              {section.value}
            </code>
          </div>
        ))}
      </div>
    </section>
  );
}

function ApiKeyRequirement({
  requiresApiKey,
  description,
}: {
  requiresApiKey: boolean;
  description?: string;
}) {
  if (!requiresApiKey) {
    return null;
  }

  return (
    <section className="bg-warning-500/10 border border-warning-500/20 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">
            API Key Required
          </h4>
          <p className="text-sm text-foreground-secondary">
            {description ||
              "This MCP requires an API key to function. You'll need to configure it after installation."}
          </p>
        </div>
      </div>
    </section>
  );
}

function RequirementsSection({
  requirements,
}: {
  requirements: RequirementDisplay[];
}) {
  if (requirements.length === 0) {
    return null;
  }

  return (
    <section>
      <SectionTitle>Requirements</SectionTitle>
      <div className="text-sm text-foreground-secondary space-y-1">
        {requirements.map((requirement, index) => (
          <div key={`${requirement.label}-${index}`}>
            {requirement.label}: {requirement.value}
          </div>
        ))}
      </div>
    </section>
  );
}

function LinksSection({ links }: { links: LinkDisplay[] }) {
  if (links.length === 0) {
    return null;
  }

  return (
    <section>
      <SectionTitle>Links</SectionTitle>
      <div className="flex flex-col gap-2">
        {links.map((link) => (
          <a
            key={link.label}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-2"
          >
            {link.label}
            <ExternalLink className="w-3 h-3" />
          </a>
        ))}
      </div>
    </section>
  );
}

function ModalFooter({
  isInstalled,
  onInstall,
  onClose,
}: {
  isInstalled: boolean;
  onInstall: () => void;
  onClose: () => void;
}) {
  return (
    <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
      <BrandButton type="button" variant="secondary" onClick={onClose}>
        Close
      </BrandButton>
      <BrandButton
        type="button"
        variant={isInstalled ? "secondary" : "primary"}
        onClick={onInstall}
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
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-semibold text-foreground mb-2">{children}</h3>
  );
}
