import { SuggestionItem, type Suggestion } from "./suggestion-item";

interface SuggestionsProps {
  suggestions: Suggestion[];
  onSuggestionClick: (value: string) => void;
}

export function Suggestions({
  suggestions,
  onSuggestionClick,
}: SuggestionsProps) {
  return (
    <ul data-testid="suggestions" className="flex flex-col gap-4 w-full">
      {suggestions.map((suggestion) => (
        <SuggestionItem
          key={String(suggestion.value)}
          suggestion={suggestion}
          onClick={onSuggestionClick}
        />
      ))}
    </ul>
  );
}
