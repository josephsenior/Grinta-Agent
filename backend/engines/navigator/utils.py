"""Utilities supporting the browsing agent's HTML parsing and prompt logic."""

import json
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ErrorResponse:
    """Structured error information produced while parsing agent responses."""

    message: str
    reason: str


@dataclass
class NavigatorMetadata:
    """Metadata describing the current browsing agent run state."""

    goal: str
    url: str
    action_space: str
    additional_context: str | None = None
    include_error_prefix: bool = False


@dataclass
class BrowsingPromptFragment:
    """Fragment of a browsing prompt with optional overrides."""

    name: str
    content: str
    fallback: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class PageParser:
    """Parse HTML documents into friendly summaries for the browsing agent."""

    def __init__(self, html: str) -> None:
        """Create a parser for the supplied HTML snippet."""
        self.html = html
        self.soup = BeautifulSoup(html, "html.parser")

    def extract_text(self) -> str:
        """Return the readable text content of the current page."""
        return self.soup.get_text("\n", strip=True)

    def extract_title(self) -> str:
        """Return the page title if present, otherwise an empty string."""
        title = self.soup.find("title")
        return title.text.strip() if title else ""

    def to_dict(self) -> dict[str, str]:
        """Serialise parsed attributes into a dictionary."""
        return {
            "title": self.extract_title(),
            "content": self.extract_text(),
        }


class PromptBuilder:
    """Build prompts for the browsing agent using structured fragments."""

    def __init__(self) -> None:
        """Initialise an empty prompt builder."""
        self.fragments: list[BrowsingPromptFragment] = []

    def add_fragment(self, fragment: BrowsingPromptFragment) -> None:
        """Append a fragment to the prompt."""
        self.fragments.append(fragment)

    def build(self) -> str:
        """Concatenate fragments into a single prompt string."""
        return "\n\n".join(fragment.content for fragment in self.fragments)


def parse_error_response(data: str) -> ErrorResponse:
    """Parse a JSON error response emitted by the browsing agent."""
    parsed = json.loads(data)
    return ErrorResponse(message=parsed["message"], reason=parsed["reason"])
