/**
 * Global Backup & Restore Settings Page
 */

import React, { useState } from "react";
import { Download, Upload, Database, CheckCircle, AlertCircle, AlertTriangle } from "lucide-react";
import { useToast, ToastContainer } from "#/components/shared/toast";

function BackupSettingsScreen() {
  const toast = useToast();
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      const response = await fetch("/api/global-export/");
      
      if (!response.ok) {
        throw new Error("Export failed");
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Forge_backup_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success("Successfully exported all data!");
    } catch (error) {
      console.error("Export error:", error);
      toast.error("Failed to export data. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      setIsImporting(true);

      try{
        const text = await file.text();
        const data = JSON.parse(text);

        const response = await fetch("/api/global-export/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          throw new Error("Import failed");
        }

        const results = await response.json();
        const totalImported = Object.values(results).reduce(
          (sum: number, r: any) => sum + r.imported,
          0,
        );
        const totalUpdated = Object.values(results).reduce(
          (sum: number, r: any) => sum + r.updated,
          0,
        );

        toast.success(
          `Successfully imported ${totalImported} new items and updated ${totalUpdated} existing items!`,
        );

        // Reload the page after a short delay to reflect changes
        setTimeout(() => window.location.reload(), 2000);
      } catch (error) {
        console.error("Import error:", error);
        toast.error("Failed to import data. Please check the file format.");
      } finally {
        setIsImporting(false);
      }
    };

    input.click();
  };

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Backup & Restore
        </h1>
        <p className="text-foreground-secondary mt-1">
          Export and import all your data in one place
        </p>
      </div>


      {/* Export Section */}
      <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-primary/10 rounded-lg">
            <Download className="w-6 h-6 text-primary" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Export Your Data
            </h2>
            <p className="text-foreground-secondary text-sm mb-4">
              Download a complete backup of all your memories, prompts, code snippets,
              and conversation templates. This file can be used to restore your data
              or transfer it to another system.
            </p>
            <div className="p-3 bg-background rounded border border-violet-500/20 mb-4">
              <h3 className="text-sm font-medium text-foreground mb-2">
                What's included:
              </h3>
              <ul className="text-sm text-foreground-secondary space-y-1">
                <li>• All saved memories</li>
                <li>• Custom prompts and templates</li>
                <li>• Code snippets library</li>
                <li>• Conversation templates</li>
              </ul>
            </div>
            <button
              type="button"
              onClick={handleExport}
              disabled={isExporting}
              className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              {isExporting ? "Exporting..." : "Export All Data"}
            </button>
          </div>
        </div>
      </div>

      {/* Import Section */}
      <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-blue-500/10 rounded-lg">
            <Upload className="w-6 h-6 text-blue-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Import Your Data
            </h2>
            <p className="text-foreground-secondary text-sm mb-4">
              Restore your data from a previous backup or import data from another
              system. Existing items with the same ID will be updated.
            </p>
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded mb-4">
              <p className="text-sm text-yellow-400 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Important:</strong> Importing will merge with your existing data.
                  Items with matching IDs will be updated. Make sure you have a current
                  backup before importing.
                </span>
              </p>
            </div>
            <button
              type="button"
              onClick={handleImport}
              disabled={isImporting}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Upload className="w-4 h-4" />
              {isImporting ? "Importing..." : "Import Data"}
            </button>
          </div>
        </div>
      </div>

      {/* Info Section */}
      <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-foreground-secondary/10 rounded-lg">
            <Database className="w-6 h-6 text-foreground-secondary" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Backup Best Practices
            </h2>
            <ul className="text-sm text-foreground-secondary space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-primary mt-1">•</span>
                <span>
                  <strong>Regular Backups:</strong> Export your data regularly to avoid
                  losing important work.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary mt-1">•</span>
                <span>
                  <strong>Secure Storage:</strong> Store backups in a secure location
                  like cloud storage or encrypted drives.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary mt-1">•</span>
                <span>
                  <strong>Test Restores:</strong> Periodically test importing your backups
                  to ensure they work correctly.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary mt-1">•</span>
                <span>
                  <strong>Version Control:</strong> Keep multiple backup versions with
                  dated filenames.
                </span>
              </li>
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

