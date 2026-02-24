"""
Simplified Kanban Robot Framework library.

This version assumes standardized usage in .robot files:
- Always pass board_key using a named argument if needed
- Use consistent positional ordering for all keywords
- No argument overloading or inference
- No positional board ID allowed
- No flexible argument swapping

Example calling conventions (required for this simplified library):

    # Create board
    ${board}=    Create Board    My Board    default=${True}

    # Create card
    ${cid}=      Create Card    title=Task A    description=Hello    status=To Do    board_key=${board}

    # Update card status
    Update Card Status To    ${cid}    In Progress

    # Assertions
    Card Should Exist In Column    ${cid}    To Do    board_key=${board}

    # Column count
    Number Of Cards In Column Should Be    1    To Do    board_key=${board}

This greatly simplifies the Python implementation.
"""

from __future__ import annotations

from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from .core import KanbanCore, ValidationError, STATUSES


# ----------------------------------------------------------------------
# Helper
# ----------------------------------------------------------------------

def _resolve_board_key(board_key: int | None, core: KanbanCore) -> int:
    """
    Resolve board key:

    - If board_key provided → use it.
    - Otherwise → use default board.
    """
    if board_key is not None:
        return int(board_key)

    boards = core.list_boards()
    default = next((b for b in boards if b.get("default")), None)
    if not default:
        raise AssertionError("No default board exists and no board_key was provided.")

    return int(default["key"])


# ----------------------------------------------------------------------
# Main Library Class
# ----------------------------------------------------------------------

@library(scope="GLOBAL", version=" 0.1.0")
class KanbanLibrary:
    """Kanban board library for Robot Framework (simplified version)."""

    def __init__(self, db_path: str = None):
        """Initialize the Kanban system."""
        self.core = KanbanCore(db_path)

    # ------------------------------------------------------------------
    # Board Management
    # ------------------------------------------------------------------

    @keyword("Create Board", tags=("Board Management",))
    def create_board(self, name: str, default: bool = True) -> int:
        """Create a board and optionally mark it as default."""
        return self.core.create_board(name, make_default=bool(default))

    @keyword("Delete Board", tags=("Board Management",))
    def delete_board(self, key: int) -> None:
        """Delete a board."""
        self.core.delete_board(int(key))

    @keyword("List Boards", tags=("Board Management",))
    def list_boards(self):
        """Return all boards as dictionaries."""
        return self.core.list_boards()

    @keyword("Board Should Exist", tags=("Board Management", "Assertions"))
    def board_should_exist(self, key: int) -> bool:
        """Assert a board exists."""
        return self.core.board_should_exist(int(key))

    @keyword("Board Should Not Exist", tags=("Board Management", "Assertions"))
    def board_should_not_exist(self, key: int) -> bool:
        """Assert a board does not exist."""
        return self.core.board_should_not_exist(int(key))

    @keyword("Make Board Default", tags=("Board Management",))
    def make_board_default(self, key: int) -> None:
        """Mark a board as the default board."""
        self.core.make_board_default(int(key))

    # ------------------------------------------------------------------
    # Card Management
    # ------------------------------------------------------------------

    @keyword("Create Card", tags=("Card Management",))
    def create_card(
        self,
        title: str,
        description: str = None,
        status: str = "To Do",
        board_key: int = None,
    ) -> int:
        """Create a new card."""
        board = _resolve_board_key(board_key, self.core)
        return self.core.create_card(title, description, status, board)

    @keyword("Update Card Status To", tags=("Card Management",))
    def update_card_status_to(self, key: int, status: str) -> None:
        """
        Update card status.

        Expected usage (required):
            Update Card Status To    ${key}    ${status}
        """
        self.core.update_card_status(int(key), str(status))

    @keyword("Update Card Title", tags=("Card Management",))
    def update_card_title(self, key: int, new_title: str) -> None:
        """Update a card's title."""
        self.core.update_card_title(int(key), new_title)

    @keyword("Update Card Description", tags=("Card Management",))
    def update_card_description(self, key: int, new_description: str = None) -> None:
        """Update a card's description."""
        self.core.update_card_description(int(key), new_description)

    @keyword("Delete Card", tags=("Card Management",))
    def delete_card(self, key: int) -> None:
        """Delete a card."""
        self.core.delete_card(int(key))

    @keyword("List Cards In Status", tags=("Card Management", "Querying"))
    def list_cards_in_status(self, status: str, board_key: int = None):
        """Return card IDs in a given column."""
        board = _resolve_board_key(board_key, self.core)
        return self.core.list_cards_in_status(status, board)

    # ------------------------------------------------------------------
    # Querying & Assertions
    # ------------------------------------------------------------------

    @keyword("Get Card Details", tags=("Querying",))
    def get_card_details(self, key: int):
        """Return full card details as a dictionary."""
        return self.core.get_card_details(int(key))

    @keyword("Get Board Summary", tags=("Querying",))
    def get_board_summary(self, board_key: int = None):
        """Return counts per column and total."""
        board = _resolve_board_key(board_key, self.core)
        return self.core.get_board_summary(board)

    @keyword("Card Should Exist In Column", tags=("Assertions",))
    def card_should_exist_in_column(self, key: int, status: str, board_key: int = None):
        """Assert a card exists in a column."""
        board = _resolve_board_key(board_key, self.core)
        return self.core.card_should_exist_in_column(int(key), status, board)

    @keyword("Card Should Have Title", tags=("Assertions",))
    def card_should_have_title(self, key: int, expected: str = None) -> bool:
        """Assert title exists or matches expected."""
        details = self.core.get_card_details(int(key))
        title = (details["title"] or "").strip()

        if expected is None:
            if not title:
                raise AssertionError(f"Card {key} has no title.")
            return True

        if title != expected:
            raise AssertionError(
                f"Card {key} title '{title}' != '{expected}'"
            )
        return True

    @keyword("Card Should Have Description", tags=("Assertions",))
    def card_should_have_description(self, key: int, expected: str = None) -> bool:
        """Assert description exists or matches expected."""
        details = self.core.get_card_details(int(key))
        desc = (details["description"] or "").strip()

        if expected is None:
            if not desc:
                raise AssertionError(f"Card {key} has no description.")
            return True

        if desc != (expected or ""):
            raise AssertionError(
                f"Card {key} description '{desc}' != '{expected or ''}'"
            )
        return True

    @keyword("Number Of Cards In Column Should Be", tags=("Assertions",))
    def number_of_cards_in_column_should_be(
        self,
        expected: int,
        status: str,
        board_key: int = None,
    ) -> bool:
        """
        Assert number of cards in a column.

        Expected usage:
            Number Of Cards In Column Should Be    1    To Do    board_key=${board}
        """
        board = _resolve_board_key(board_key, self.core)
        return self.core.number_of_cards_in_column_should_be(str(status), int(expected), board)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @keyword("Clear Kanban Database", tags=("Utilities",))
    def clear_kanban_database(self) -> None:
        """Remove and recreate database."""
        self.core.clear_kanban_database()

    @keyword("Close Kanban Database Connection", tags=("Utilities",))
    def close_kanban_database_connection(self) -> None:
        """Close SQLite connection."""
        self.core.close()

    @keyword("Create Demo Kanban Data", tags=("Utilities",))
    def create_demo_kanban_data(self) -> None:
        """Create example data."""
        self.core.create_demo_kanban_data()

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    @keyword("Show Board Columns", tags=("Visualization",))
    def show_board_columns(self, board_key: int = None) -> None:
        """Print column → card listing for a board."""
        bi = BuiltIn()
        def echo(msg: str): bi.log_to_console(msg)

        board = _resolve_board_key(board_key, self.core)

        echo("")
        for status in STATUSES:
            cards = self.core.list_cards_in_status(status, board)
            echo(f"{status}:")
            if not cards:
                echo("  (empty)")
            else:
                for cid in cards:
                    d = self.core.get_card_details(cid)
                    echo(f"  #{cid}: {d['title']}")
        echo("")
