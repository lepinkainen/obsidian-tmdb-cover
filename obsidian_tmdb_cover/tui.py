"""Interactive TUI for selecting TMDB results using Textual."""

from typing import Optional, Dict, Any
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Button, Static, Label
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.message import Message


class StopProcessing(Exception):
    """Exception raised when user wants to stop processing entirely."""

    pass


class ResultCard(Static):
    """A card displaying information about a movie/TV show result."""

    def __init__(
        self,
        result: Dict[str, Any],
        index: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.result = result
        self.index = index
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        media_type = self.result.get("media_type", "unknown")
        title = self.result.get("title") or self.result.get("name", "Unknown")
        release_date = self.result.get("release_date") or self.result.get(
            "first_air_date", ""
        )
        year = release_date[:4] if release_date else "Unknown"
        overview = self.result.get("overview", "No description available")
        vote_average = self.result.get("vote_average", 0)

        # Truncate overview if too long
        if len(overview) > 150:
            overview = overview[:147] + "..."

        type_emoji = "🎬" if media_type == "movie" else "📺"
        type_label = "Movie" if media_type == "movie" else "TV Show"

        yield Label(f"{type_emoji} {type_label}", classes="media-type")
        yield Label(f"{title} ({year})", classes="title")
        yield Label(f"⭐ {vote_average:.1f}/10", classes="rating")
        yield Label(overview, classes="overview")

    def on_click(self) -> None:
        """Handle click event."""
        self.post_message(self.Selected(self.result))

    class Selected(Message):
        """Message sent when a result card is selected."""

        def __init__(self, result: Dict[str, Any]) -> None:
            super().__init__()
            self.result = result


class SelectionScreen(ModalScreen[Optional[Dict[str, Any]]]):
    """Modal screen for selecting a TMDB result."""

    CSS = """
    SelectionScreen {
        align: center middle;
    }

    #selection-container {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    #title-label {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #results-container {
        height: auto;
        max-height: 25;
        margin-bottom: 1;
    }

    ResultCard {
        height: auto;
        margin-bottom: 1;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    ResultCard:focus {
        background: $primary-background;
        border: thick $accent;
    }

    ResultCard:hover {
        background: $boost;
    }

    ResultCard .media-type {
        color: $accent;
        text-style: bold;
    }

    ResultCard .title {
        color: $text;
        text-style: bold;
        margin-bottom: 1;
    }

    ResultCard .rating {
        color: $warning;
    }

    ResultCard .overview {
        color: $text-muted;
        margin-top: 1;
    }

    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("q", "cancel", "Quit", show=False),
        Binding("up", "focus_previous", "Previous", show=False),
        Binding("down", "focus_next", "Next", show=False),
        Binding("k", "focus_previous", show=False),
        Binding("j", "focus_next", show=False),
    ]

    def __init__(
        self,
        title: str,
        results: list[Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.results = results
        self.selected_result: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="selection-container"):
            yield Label(
                f"Multiple results found for: {self.title_text}",
                id="title-label",
            )
            with VerticalScroll(id="results-container"):
                for i, result in enumerate(self.results):
                    yield ResultCard(result, i)
            with Container(id="button-container"):
                yield Button("Skip", variant="warning", id="skip-button")
                yield Button("Stop Processing", variant="error", id="stop-button")

    def on_mount(self) -> None:
        """Focus first result card when mounted."""
        cards = list(self.query(ResultCard))
        if cards:
            cards[0].focus()

    def on_result_card_selected(self, message: ResultCard.Selected) -> None:
        """Handle result card selection."""
        self.dismiss(message.result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "skip-button":
            self.dismiss(None)
        elif event.button.id == "stop-button":
            raise StopProcessing("User requested to stop processing")

    def action_cancel(self) -> None:
        """Cancel selection."""
        self.dismiss(None)


class TMDBSelectorApp(App[Optional[Dict[str, Any]]]):
    """Textual app for selecting TMDB results."""

    def __init__(
        self,
        title: str,
        results: list[Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.results = results

    def on_mount(self) -> None:
        """Mount the selection screen."""
        self.push_screen(
            SelectionScreen(self.title_text, self.results),
            callback=self.handle_selection,
        )

    def handle_selection(self, result: Optional[Dict[str, Any]]) -> None:
        """Handle the selection result."""
        self.exit(result)


def select_tmdb_result(
    title: str, results: list[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Display an interactive TUI for selecting a TMDB result.

    Args:
        title: The search title
        results: List of TMDB search results

    Returns:
        Selected result dict or None if skipped
    """
    app = TMDBSelectorApp(title, results)
    return app.run()
