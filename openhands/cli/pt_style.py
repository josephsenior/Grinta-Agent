from prompt_toolkit.styles import Style, merge_styles
from prompt_toolkit.styles.defaults import default_ui_style

COLOR_GOLD = "#FFD700"
COLOR_GREY = "#808080"
COLOR_AGENT_BLUE = "#4682B4"


def get_cli_style() -> Style:
    """Get custom CLI style configuration.

    Creates a merged style combining default UI style with custom colors
    for the OpenHands CLI interface.

    Returns:
        Merged prompt_toolkit Style object
    """
    base = default_ui_style()
    custom = Style.from_dict(
        {
            "gold": COLOR_GOLD,
            "grey": COLOR_GREY,
            "prompt": f"{COLOR_GOLD} bold",
            "completion-menu.completion.current fuzzymatch.outside": "fg:#ffffff bg:#888888",
            "selected": COLOR_GOLD,
            "risk-high": "#FF0000 bold",
        },
    )
    return merge_styles([base, custom])
