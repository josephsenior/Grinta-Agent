import React from "react";
import { Trash2, Edit2, FileText, Upload } from "lucide-react";
import { Card, CardContent } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import type { KnowledgeBaseCollection } from "#/types/knowledge-base";

interface KBCollectionCardProps {
  collection: KnowledgeBaseCollection;
  onEdit?: (collection: KnowledgeBaseCollection) => void;
  onDelete?: (collectionId: string) => void;
  onUploadDocument?: (collectionId: string) => void;
  onViewDocuments?: (collectionId: string) => void;
}

export function KBCollectionCard({
  collection,
  onEdit,
  onDelete,
  onUploadDocument,
  onViewDocuments,
}: KBCollectionCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-200">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-foreground mb-1">
              {collection.name}
            </h3>
            {collection.description && (
              <p className="text-sm text-foreground-secondary">
                {collection.description}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onEdit(collection)}
                title="Edit collection"
              >
                <Edit2 className="w-4 h-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onDelete(collection.id)}
                title="Delete collection"
                className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-foreground-secondary" />
            <span className="text-sm text-foreground-secondary">
              {collection.document_count} {collection.document_count === 1 ? "document" : "documents"}
            </span>
          </div>
          <div className="text-sm text-foreground-secondary">
            {collection.total_size_mb.toFixed(2)} MB
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-foreground-secondary mb-4">
          <span>Created {formatDate(collection.created_at)}</span>
          <span>Updated {formatDate(collection.updated_at)}</span>
        </div>

        <div className="flex gap-2">
          {onViewDocuments && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewDocuments(collection.id)}
              className="flex-1"
            >
              <FileText className="w-4 h-4 mr-2" />
              View Documents
            </Button>
          )}
          {onUploadDocument && (
            <Button
              size="sm"
              onClick={() => onUploadDocument(collection.id)}
              className="flex-1"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

