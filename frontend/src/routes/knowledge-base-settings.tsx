import React from "react";
import { KnowledgeBaseManager } from "#/components/features/knowledge-base/knowledge-base-manager";

export default function KnowledgeBaseSettings() {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <KnowledgeBaseManager />
    </React.Suspense>
  );
}
