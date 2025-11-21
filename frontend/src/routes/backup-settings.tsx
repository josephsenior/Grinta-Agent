import React, { useMemo, useState } from "react";
import { Download, Upload, Database, AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useToast, ToastContainer } from "#/components/shared/toast";

type ImportSummaryEntry = {
  imported?: number;
  updated?: number;
};

type ImportSummaryResponse = Record<string, ImportSummaryEntry>;

function BackupSettingsScreen() {
  const { t } = useTranslation("settings");
  const toast = useToast();
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  const exportFeatureKeys = useMemo(
    () => [
      {
        key: "backupSettings.features.memories",
        defaultMessage: "All saved memories",
      },
      {
        key: "backupSettings.features.prompts",
        defaultMessage: "Custom prompts and templates",
      },
      {
        key: "backupSettings.features.snippets",
        defaultMessage: "Code snippets library",
      },
      {
        key: "backupSettings.features.conversations",
        defaultMessage: "Conversation templates",
      },
    ],
    [],
  );

  const bestPracticeItems = useMemo(
    () => [
      {
        titleKey: "backupSettings.bestPractices.regularBackups.title",
        titleDefault: "Regular Backups",
        descriptionKey: "backupSettings.bestPractices.regularBackups.body",
        descriptionDefault:
          "Export your data regularly to avoid losing important work.",
      },
      {
        titleKey: "backupSettings.bestPractices.secureStorage.title",
        titleDefault: "Secure Storage",
        descriptionKey: "backupSettings.bestPractices.secureStorage.body",
        descriptionDefault:
          "Store backups in a secure location like cloud storage or encrypted drives.",
      },
      {
        titleKey: "backupSettings.bestPractices.testRestores.title",
        titleDefault: "Test Restores",
        descriptionKey: "backupSettings.bestPractices.testRestores.body",
        descriptionDefault:
          "Periodically test importing your backups to ensure they work correctly.",
      },
      {
        titleKey: "backupSettings.bestPractices.versionControl.title",
        titleDefault: "Version Control",
        descriptionKey: "backupSettings.bestPractices.versionControl.body",
        descriptionDefault:
          "Keep multiple backup versions with dated filenames.",
      },
    ],
    [],
  );

  const handleExport = async () => {
    setIsExporting(true);

    try {
      const response = await fetch("/api/global-export/");

      if (!response.ok) {
        throw new Error("export-failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const dateSuffix = new Date().toISOString().split("T")[0];
      a.download = `forge-backup-${dateSuffix}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast.success(
        t("backupSettings.export.success", "Successfully exported all data!"),
      );
    } catch {
      toast.error(
        t(
          "backupSettings.export.error",
          "Failed to export data. Please try again.",
        ),
      );
    } finally {
      setIsExporting(false);
    }
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";

    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) {
        return;
      }

      setIsImporting(true);

      try {
        const text = await file.text();
        const data = JSON.parse(text) as ImportSummaryResponse;

        const response = await fetch("/api/global-export/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          throw new Error("import-failed");
        }

        const results = (await response.json()) as ImportSummaryResponse;

        const totals = Object.values(results).reduce<{
          imported: number;
          updated: number;
        }>(
          (accumulator, entry) => ({
            imported: accumulator.imported + (entry.imported ?? 0),
            updated: accumulator.updated + (entry.updated ?? 0),
          }),
          { imported: 0, updated: 0 },
        );

        toast.success(
          t("backupSettings.import.success", {
            imported: totals.imported,
            updated: totals.updated,
            defaultValue:
              "Successfully imported {{imported}} new items and updated {{updated}} existing items!",
          }),
        );

        window.setTimeout(() => {
          window.location.reload();
        }, 2000);
      } catch {
        toast.error(
          t(
            "backupSettings.import.error",
            "Failed to import data. Please check the file format.",
          ),
        );
      } finally {
        setIsImporting(false);
      }
    };

    input.click();
  };

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
      <div className="w-full">
        <h1 className="text-2xl font-semibold text-foreground w-full">
          {t("backupSettings.title", "Backup & Restore")}
        </h1>
        <p className="text-foreground-secondary mt-1 w-full">
          {t(
            "backupSettings.subtitle",
            "Export and import all your data in one place",
          )}
        </p>
      </div>

      {/* Export Section */}
      <div className="p-5 bg-black/60 border border-white/10 rounded-2xl">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-white/5 rounded-lg">
            <Download className="w-6 h-6 text-foreground-tertiary" />
          </div>
          <div className="flex-1 w-full">
            <h2 className="text-lg font-semibold text-foreground mb-2 w-full">
              {t("backupSettings.export.heading", "Export Your Data")}
            </h2>
            <p className="text-foreground-secondary text-sm mb-4 w-full">
              {t(
                "backupSettings.export.description",
                "Download a complete backup of all your memories, prompts, code snippets, and conversation templates. This file can be used to restore your data or transfer it to another system.",
              )}
            </p>
            <div className="p-3 bg-black/60 rounded border border-white/10 mb-4 w-full">
              <h3 className="text-sm font-medium text-foreground mb-2 w-full">
                {t("backupSettings.export.included", "What's included:")}
              </h3>
              <ul className="list-disc pl-5 text-sm text-foreground-secondary space-y-1">
                {exportFeatureKeys.map((item) => (
                  <li key={item.key}>{t(item.key, item.defaultMessage)}</li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              onClick={handleExport}
              disabled={isExporting}
              className="flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              {isExporting
                ? t("backupSettings.export.inProgress", "Exporting...")
                : t("backupSettings.export.button", "Export All Data")}
            </button>
          </div>
        </div>
      </div>

      {/* Import Section */}
      <div className="p-5 bg-black/60 border border-white/10 rounded-2xl">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-white/5 rounded-lg">
            <Upload className="w-6 h-6 text-foreground-tertiary" />
          </div>
          <div className="flex-1 w-full">
            <h2 className="text-lg font-semibold text-foreground mb-2 w-full">
              {t("backupSettings.import.heading", "Import Your Data")}
            </h2>
            <p className="text-foreground-secondary text-sm mb-4 w-full">
              {t(
                "backupSettings.import.description",
                "Restore your data from a previous backup or import data from another system. Existing items with the same ID will be updated.",
              )}
            </p>
            <div className="p-3 bg-white/5 border border-white/10 rounded-xl mb-4">
              <p className="text-sm text-foreground-secondary flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>
                    {t("backupSettings.import.warningTitle", "Important:")}
                  </strong>{" "}
                  {t(
                    "backupSettings.import.warningBody",
                    "Importing will merge with your existing data. Items with matching IDs will be updated. Make sure you have a current backup before importing.",
                  )}
                </span>
              </p>
            </div>
            <button
              type="button"
              onClick={handleImport}
              disabled={isImporting}
              className="flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Upload className="w-4 h-4" />
              {isImporting
                ? t("backupSettings.import.inProgress", "Importing...")
                : t("backupSettings.import.button", "Import Data")}
            </button>
          </div>
        </div>
      </div>

      {/* Info Section */}
      <div className="p-5 bg-black/60 border border-white/10 rounded-2xl">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-foreground-secondary/10 rounded-lg">
            <Database className="w-6 h-6 text-foreground-secondary" />
          </div>
          <div className="flex-1 w-full">
            <h2 className="text-lg font-semibold text-foreground mb-2 w-full">
              {t(
                "backupSettings.bestPractices.heading",
                "Backup Best Practices",
              )}
            </h2>
            <ul className="space-y-3">
              {bestPracticeItems.map((item) => (
                <li key={item.titleKey} className="flex items-start gap-2">
                  <span className="text-foreground-tertiary mt-1">•</span>
                  <span>
                    <strong>{`${t(item.titleKey, item.titleDefault)}:`}</strong>{" "}
                    {t(item.descriptionKey, item.descriptionDefault)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Toast notifications */}
      <ToastContainer toasts={toast.toasts} onRemove={toast.removeToast} />
    </div>
  );
}

export default BackupSettingsScreen;
