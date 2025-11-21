import { useState } from "react";
import type { PromptTemplate, PromptVariable } from "#/types/prompt";
import { PromptCategory } from "#/types/prompt";

export function usePromptFormState(initialData?: PromptTemplate) {
  const [title, setTitle] = useState(initialData?.title || "");
  const [description, setDescription] = useState(
    initialData?.description || "",
  );
  const [category, setCategory] = useState<PromptCategory>(
    initialData?.category || PromptCategory.CUSTOM,
  );
  const [content, setContent] = useState(initialData?.content || "");
  const [variables, setVariables] = useState<PromptVariable[]>(
    initialData?.variables || [],
  );
  const [tags, setTags] = useState<string[]>(initialData?.tags || []);
  const [tagInput, setTagInput] = useState("");
  const [isFavorite, setIsFavorite] = useState(
    initialData?.is_favorite || false,
  );

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setCategory(PromptCategory.CUSTOM);
    setContent("");
    setVariables([]);
    setTags([]);
    setIsFavorite(false);
  };

  return {
    title,
    setTitle,
    description,
    setDescription,
    category,
    setCategory,
    content,
    setContent,
    variables,
    setVariables,
    tags,
    setTags,
    tagInput,
    setTagInput,
    isFavorite,
    setIsFavorite,
    resetForm,
  };
}
