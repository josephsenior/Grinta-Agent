import React from "react";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { PromptVariable } from "#/types/prompt";

interface VariablesSectionProps {
  variables: PromptVariable[];
  onAddVariable: () => void;
  onUpdateVariable: (
    index: number,
    field: keyof PromptVariable,
    value: string | boolean,
  ) => void;
  onRemoveVariable: (index: number) => void;
  onInsertVariable: (varName: string) => void;
}

function VariableItem({
  variable,
  index,
  onUpdate,
  onRemove,
  onInsert,
}: {
  variable: PromptVariable;
  index: number;
  onUpdate: (
    index: number,
    field: keyof PromptVariable,
    value: string | boolean,
  ) => void;
  onRemove: (index: number) => void;
  onInsert: (varName: string) => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="p-3 bg-background border border-border rounded">
      <div className="grid grid-cols-2 gap-3 mb-2">
        <input
          type="text"
          value={variable.name}
          onChange={(e) => onUpdate(index, "name", e.target.value)}
          placeholder={t("PROMPTS$VARIABLE_NAME")}
          className="px-2 py-1 bg-background-secondary border border-border rounded text-sm text-foreground focus:outline-none focus:border-border-active"
        />
        <input
          type="text"
          value={variable.default_value || ""}
          onChange={(e) => onUpdate(index, "default_value", e.target.value)}
          placeholder={t("PROMPTS$DEFAULT_VALUE")}
          className="px-2 py-1 bg-background-secondary border border-border rounded text-sm text-foreground focus:outline-none focus:border-border-active"
        />
      </div>
      <div className="flex items-center justify-between">
        <input
          type="text"
          value={variable.description || ""}
          onChange={(e) => onUpdate(index, "description", e.target.value)}
          placeholder={t("PROMPTS$VARIABLE_DESCRIPTION")}
          className="flex-1 px-2 py-1 bg-background-secondary border border-border rounded text-sm text-foreground focus:outline-none focus:border-border-active mr-2"
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onInsert(variable.name)}
            className="px-2 py-1 text-xs text-primary hover:text-primary-dark"
            disabled={!variable.name}
          >
            {t("PROMPTS$INSERT")}
          </button>
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="p-1 text-red-500 hover:text-red-600"
            aria-label="Remove variable"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function VariablesSection({
  variables,
  onAddVariable,
  onUpdateVariable,
  onRemoveVariable,
  onInsertVariable,
}: VariablesSectionProps) {
  const { t } = useTranslation();

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <label className="block text-sm font-medium text-foreground">
          {t("PROMPTS$VARIABLES")}
        </label>
        <button
          type="button"
          onClick={onAddVariable}
          className="flex items-center gap-1 px-2 py-1 text-xs text-primary hover:text-primary-dark"
        >
          <Plus className="w-3 h-3" />
          {t("PROMPTS$ADD_VARIABLE")}
        </button>
      </div>

      <div className="space-y-3">
        {variables.map((variable, index) => (
          <VariableItem
            key={index}
            variable={variable}
            index={index}
            onUpdate={onUpdateVariable}
            onRemove={onRemoveVariable}
            onInsert={onInsertVariable}
          />
        ))}
      </div>
    </div>
  );
}
