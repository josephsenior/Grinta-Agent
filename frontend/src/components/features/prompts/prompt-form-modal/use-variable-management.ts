import { useCallback } from "react";
import type { PromptVariable } from "#/types/prompt";

export function useVariableManagement(
  variables: PromptVariable[],
  setVariables: (vars: PromptVariable[]) => void,
  content: string,
  setContent: (content: string) => void,
) {
  const addVariable = useCallback(() => {
    setVariables([
      ...variables,
      { name: "", description: "", default_value: "", required: true },
    ]);
  }, [variables, setVariables]);

  const updateVariable = useCallback(
    (index: number, field: keyof PromptVariable, value: string | boolean) => {
      const updated = [...variables];
      updated[index] = { ...updated[index], [field]: value };
      setVariables(updated);
    },
    [variables, setVariables],
  );

  const removeVariable = useCallback(
    (index: number) => {
      setVariables(variables.filter((_, i) => i !== index));
    },
    [variables, setVariables],
  );

  const insertVariable = useCallback(
    (varName: string) => {
      setContent(`${content}{{${varName}}}`);
    },
    [content, setContent],
  );

  return {
    addVariable,
    updateVariable,
    removeVariable,
    insertVariable,
  };
}
