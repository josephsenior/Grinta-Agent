import { useCallback } from "react";

export function useTagManagement(
  tags: string[],
  setTags: (tags: string[]) => void,
  tagInput: string,
  setTagInput: (input: string) => void,
) {
  const addTag = useCallback(() => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput("");
    }
  }, [tagInput, tags, setTags, setTagInput]);

  const removeTag = useCallback(
    (tag: string) => {
      setTags(tags.filter((t) => t !== tag));
    },
    [tags, setTags],
  );

  return {
    addTag,
    removeTag,
  };
}
