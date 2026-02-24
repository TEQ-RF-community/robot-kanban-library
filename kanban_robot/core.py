"""
Core Kanban functionality for Robot Framework and the PySide6 GUI.

This module encapsulates:
- A lightweight SQLite data model (boards + cards) with a hardcoded schema.
- CRUD operations with robust validation and custom exception types (not all used).
- Assertions used by Robot Framework keywords.
- Small helper utilities for demo data and resetting the database.

Design Notes:
    * **Hardcoded schema**: No external migration or SQL files are needed for ease of setup
      in a classroom setting.
    * **Per-user DB**: The SQLite database is stored under
      ``~/.kanban_robot/kanban.db`` by default. Override directory with the
      environment variable ``KANBAN_DB_DIR``.
    * **Statuses**: A card can only be in exactly one of: "To Do", "In Progress", "Done".
    * **Consistency**: Foreign keys are enabled and cascade deletes from boards to cards.
    * **Exceptions**: All domain-level errors raise subclasses of :class:`KanbanError`.
      Assertion-style checks raise :class:`AssertionError` so Robot “Should …” keywords behave naturally.

Typical Usage:
    >>> core = KanbanCore()
    >>> b = core.create_board("My Board", make_default=True)
    >>> c = core.create_card("Implement feature X", "details...", "To Do", b)
    >>> core.update_card_status(c, "In Progress")
    >>> core.card_should_exist_in_column(c, "In Progress")
    >>> core.card_should_exist_in_column(c, "In Progress")
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# -----------------------
# Custom Exceptions (some are for future use)
# -----------------------


class ErrorCode:
    """Stable, machine-readable error codes (suitable for logs, JSON, telemetry)."""
    VALIDATION = "validation_error"
    BOARD_NOT_FOUND = "board_not_found"
    CARD_NOT_FOUND = "card_not_found"
    DUPLICATE_NAME = "duplicate_name"
    STATUS_VALIDATION = "status_validation_error"
    STATUS_TRANSITION = "status_transition_error"
    DEFAULT_BOARD_MISSING = "default_board_missing"
    DB_ERROR = "database_error"
    CONCURRENCY = "concurrency_error"
    UNKNOWN = "unknown_error"


@dataclass
class KanbanError(Exception):
    """
    Base exception for all Kanban-related errors.

    Attributes:
        message: Human-friendly message (will be used by __str__).
        code: Machine-friendly error code (see ErrorCode).
        context: Arbitrary context (IDs, names, parameters) to help diagnose issues.
        cause: Optional original exception that triggered this error.
    """
    message: str = "Kanban error."
    code: str = ErrorCode.UNKNOWN
    context: Dict[str, Any] = field(default_factory=dict)
    cause: Optional[BaseException] = None

    def __str__(self) -> str:
        # Include context keys in a stable order for readability
        ctx = ", ".join(f"{k}={self.context[k]!r}" for k in sorted(self.context)) if self.context else ""
        if ctx:
            return f"{self.message} [{self.code}] ({ctx})"
        return f"{self.message} [{self.code}]"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the error for logging/telemetry."""
        return {
            "message": self.message,
            "code": self.code,
            "context": self.context,
            "cause": repr(self.cause) if self.cause else None,
            "type": self.__class__.__name__,
        }


@dataclass
class ValidationError(KanbanError):
    """
    General validation error (bad inputs, empty strings, etc.).

    Common cases:
      - Empty board or card title
      - Type/format mismatch
      - Out-of-range values
    """
    message: str = "Validation failed."
    code: str = ErrorCode.VALIDATION
    field: Optional[str] = None

    def __post_init__(self):
        if self.field and "field" not in self.context:
            self.context["field"] = self.field


@dataclass
class StatusValidationError(KanbanError):
    """
    Invalid status value (not in allowed STATUSES).
    """
    status: str = ""
    allowed: Tuple[str, ...] = tuple()
    message: str = "Invalid status."
    code: str = ErrorCode.STATUS_VALIDATION

    def __post_init__(self):
        self.context.setdefault("status", self.status)
        if self.allowed:
            self.context.setdefault("allowed", list(self.allowed))


@dataclass
class StatusTransitionError(KanbanError):
    """
    Status transition is not allowed given current rules (if any business rule applies).
    """
    card_id: int = 0
    from_status: str = ""
    to_status: str = ""
    message: str = "Status transition is not allowed."
    code: str = ErrorCode.STATUS_TRANSITION

    def __post_init__(self):
        self.context.setdefault("card_id", self.card_id)
        self.context.setdefault("from_status", self.from_status)
        self.context.setdefault("to_status", self.to_status)


@dataclass
class BoardNotFound(KanbanError):
    """Raised when a board with the given key does not exist."""
    board_id: int = 0
    message: str = "Board not found."
    code: str = ErrorCode.BOARD_NOT_FOUND

    def __post_init__(self):
        self.context.setdefault("board_id", self.board_id)


@dataclass
class CardNotFound(KanbanError):
    """Raised when a card with the given key does not exist."""
    card_id: int = 0
    message: str = "Card not found."
    code: str = ErrorCode.CARD_NOT_FOUND

    def __post_init__(self):
        self.context.setdefault("card_id", self.card_id)


@dataclass
class DuplicateNameError(KanbanError):
    """Raised when attempting to create a board whose name already exists (UNIQUE)."""
    name: str = ""
    entity: str = "board"
    message: str = "Duplicate name."
    code: str = ErrorCode.DUPLICATE_NAME

    def __post_init__(self):
        self.context.setdefault("entity", self.entity)
        if self.name:
            self.context.setdefault("name", self.name)


@dataclass
class DefaultBoardMissingError(KanbanError):
    """Raised when an operation requires a default board but none exists."""
    message: str = "No default board is configured."
    code: str = ErrorCode.DEFAULT_BOARD_MISSING


@dataclass
class DatabaseError(KanbanError):
    """Generic database layer error (unexpected sqlite3 errors, etc.)."""
    message: str = "Database operation failed."
    code: str = ErrorCode.DB_ERROR


@dataclass
class ConcurrencyError(KanbanError):
    """Raised when a concurrency/locking rule is violated (future‑proof)."""
    message: str = "Concurrency rule violated."
    code: str = ErrorCode.CONCURRENCY


# -----------------------
# Helpers for exception mapping
# -----------------------

def from_sqlite_integrity_error(err: sqlite3.IntegrityError, entity: str = "board", name: Optional[str] = None) -> KanbanError:
    """
    Map a sqlite3.IntegrityError to a more specific domain error if possible.
    Currently focuses on UNIQUE(name) for boards; extend as needed.

    Args:
        err: The underlying sqlite3.IntegrityError.
        entity: Entity kind, e.g., "board".
        name: Optional known name that triggered the error.

    Returns:
        KanbanError: More specific DuplicateNameError if detected, else DatabaseError.
    """
    # Common pattern in SQLite for UNIQUE constraints includes "UNIQUE constraint failed"
    msg = str(err).lower()
    if "unique" in msg and "name" in msg:
        return DuplicateNameError(name=name or "", entity=entity, cause=err)
    return DatabaseError(message="Integrity constraint failed.", cause=err, context={"raw": str(err)})


# -----------------------
# Constants
# -----------------------

#: Allowed workflow states for a card.
STATUSES = ("To Do", "In Progress", "Done")


# -----------------------
# Helpers
# -----------------------

def _app_dir() -> str:
    """Resolve the per-user application directory for storing the SQLite DB.

    Returns:
        str: A directory path. Defaults to ``~/.kanban_robot``.
             If the environment variable ``KANBAN_DB_DIR`` is set, that path is used.

    Side Effects:
        Ensures the directory exists (creates it if missing).
    """
    root = os.environ.get("KANBAN_DB_DIR")
    if not root:
        home = os.path.expanduser("~")
        root = os.path.join(home, ".kanban_robot")
    os.makedirs(root, exist_ok=True)
    return root


def default_db_path() -> str:
    """Compute the default path to the SQLite database file.

    Returns:
        str: Absolute path to ``kanban.db`` inside the app directory.
    """
    return os.path.join(_app_dir(), "kanban.db")


# -----------------------
# Core class
# -----------------------

class KanbanCore:
    """Encapsulates all database access and Kanban operations.

    Args:
        db_path (str | None): Optional custom file path for the SQLite database.
                              If omitted, defaults to :func:`default_db_path`.

    Attributes:
        db_path (str): Path to the SQLite database file.
        conn (sqlite3.Connection): Open connection with foreign keys enabled.

    Lifecycle:
        Instantiate once and reuse for your session. Call :meth:`close` to close the
        connection. The Robot library manages this lifecycle for you.

    Threading:
        Uses ``check_same_thread=False`` to allow usage from UI threads in the PySide6 GUI.

    Raises:
        KanbanError: For domain-specific errors and validation issues.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or default_db_path()
        # Allow usage across threads (e.g., PySide6 UI thread) for the GUI demo.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._enable_foreign_keys()
        self._init_schema()

    # --- Connection & schema management ---

    def _enable_foreign_keys(self) -> None:
        """Enable foreign key enforcement in SQLite.

        Notes:
            SQLite does not enable foreign keys by default; this PRAGMA is required.
        """
        with self.conn:
            self.conn.execute("PRAGMA foreign_keys = ON")

    def _init_schema(self) -> None:
        """Create tables if they do not exist.

        Tables:
            boards(id PK, name UNIQUE NOT NULL, is_default INTEGER NOT NULL DEFAULT 0)
            cards(id PK, board_id FK NOT NULL, title NOT NULL, description NULL, status CHECK IN STATUSES)
        """
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS boards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_default INTEGER NOT NULL DEFAULT 0
                )
            """)
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL CHECK (status IN ('To Do','In Progress','Done')),
                    FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
                )
            """)

    def close(self) -> None:
        """Close the underlying database connection.

        Safe to call multiple times.
        """
        try:
            self.conn.close()
        except Exception:
            pass

    # --- Validation helpers ---

    @staticmethod
    def _validate_status(status: str) -> None:
        """Ensure the status is one of the allowed values.

        Args:
            status: Candidate status string.

        Raises:
            ValidationError: If the status is not in :data:`STATUSES`.
        """
        if status not in STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Allowed: {', '.join(STATUSES)}"
            )

    def _get_default_board_id(self) -> int:
        """Find or create the default board.

        Returns:
            int: The board key of the current default board.

        Notes:
            If no board is marked default, a new board named "Default" is created and
            set as default.
        """
        row = self.conn.execute(
            "SELECT id FROM boards WHERE is_default=1 LIMIT 1"
        ).fetchone()
        if row:
            return row["id"]
        # Create an initial default board if none exist
        return self.create_board("Default", make_default=True)

    def _ensure_board_exists(self, board_id: int) -> None:
        """Raise if the specified board does not exist."""
        if not self.board_exists(board_id):
            raise BoardNotFound(f"Board key {board_id} not found.")

    def _ensure_card_exists(self, card_id: int) -> None:
        """Raise if the specified card does not exist."""
        row = self.conn.execute("SELECT id FROM cards WHERE id=?", (card_id,)).fetchone()
        if not row:
            raise CardNotFound(f"Card key {card_id} not found.")

    # --- Board Management ---

    def create_board(self, name: str, make_default: bool = True) -> int:
        """Create a board.

        Args:
            name: Board name (must be unique and non-empty).
            make_default: If True, this board becomes the default board.

        Returns:
            int: Newly created board key.

        Raises:
            ValidationError: If the name is empty or whitespace.
            DuplicateNameError: If a board with the same name already exists.
        """
        name = (name or "").strip()
        if not name:
            raise ValidationError("Board name must not be empty.")
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO boards(name, is_default) VALUES(?, 0)", (name,)
                )
                board_id = cur.lastrowid
                if make_default:
                    self.make_board_default(board_id)
                return board_id
        except sqlite3.IntegrityError:
            # UNIQUE(name) constraint violation
            raise DuplicateNameError(f"Board with name '{name}' already exists.")

    def delete_board(self, board_id: int) -> None:
        """Delete a board by key.

        Args:
            board_id: Board key (id).

        Notes:
            Cascades and deletes associated cards.
        """
        self._ensure_board_exists(board_id)
        with self.conn:
            self.conn.execute("DELETE FROM boards WHERE id=?", (board_id,))

    def make_board_default(self, board_id: int) -> None:
        """Mark the specified board as the default board.

        Args:
            board_id: Board key to set as default.

        Behavior:
            Unsets the default flag for all other boards first, then sets it for the target.
        """
        self._ensure_board_exists(board_id)
        with self.conn:
            self.conn.execute("UPDATE boards SET is_default=0")
            self.conn.execute("UPDATE boards SET is_default=1 WHERE id=?", (board_id,))

    def board_exists(self, board_id: int) -> bool:
        """Check if a board exists.

        Args:
            board_id: Board key.

        Returns:
            bool: True if the board exists, else False.
        """
        row = self.conn.execute("SELECT 1 FROM boards WHERE id=?", (board_id,)).fetchone()
        return bool(row)

    def list_boards(self) -> List[Dict[str, Any]]:
        """List all boards.

        Returns:
            List[Dict[str, Any]]: Each dict contains ``key``, ``name``, ``default`` (bool).
        """
        rows = self.conn.execute(
            "SELECT id, name, is_default FROM boards ORDER BY id"
        ).fetchall()
        return [{"key": r["id"], "name": r["name"], "default": bool(r["is_default"])} for r in rows]

    # --- Card Management ---

    def create_card(
            self,
            title: str,
            description: Optional[str] = None,
            status: str = "To Do",
            board_key: Optional[int] = None,
    ) -> int:
        """Create a card.

        Args:
            title: Non-empty card title.
            description: Optional text.
            status: One of :data:`STATUSES`. Defaults to ``"To Do"``.
            board_key: Target board key. If omitted, the default board is used.

        Returns:
            int: Newly created card key.

        Raises:
            ValidationError: If ``title`` is empty or ``status`` is invalid.
            BoardNotFound: If ``board_key`` does not identify an existing board.
        """
        title = (title or "").strip()
        if not title:
            raise ValidationError("Card title must not be empty.")
        self._validate_status(status)
        if board_key is None:
            board_key = self._get_default_board_id()
        self._ensure_board_exists(board_key)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO cards(board_id, title, description, status) VALUES(?, ?, ?, ?)",
                (board_key, title, description, status),
            )
            return cur.lastrowid

    def update_card_status(self, card_id: int, status: str) -> None:
        """Update the status of a card.

        Args:
            card_id: Card key.
            status: New status (must be in :data:`STATUSES`).

        Raises:
            ValidationError: If status is invalid.
            CardNotFound: If the card does not exist.
        """
        self._validate_status(status)
        self._ensure_card_exists(card_id)
        with self.conn:
            self.conn.execute("UPDATE cards SET status=? WHERE id=?", (status, card_id))

    def update_card_title(self, card_id: int, new_title: str) -> None:
        """Update the title of a card.

        Args:
            card_id: Card key.
            new_title: Non-empty new title.

        Raises:
            ValidationError: If new_title is empty.
            CardNotFound: If the card does not exist.
        """
        new_title = (new_title or "").strip()
        if not new_title:
            raise ValidationError("New title must not be empty.")
        self._ensure_card_exists(card_id)
        with self.conn:
            self.conn.execute("UPDATE cards SET title=? WHERE id=?", (new_title, card_id))

    def update_card_description(self, card_id: int, new_description: Optional[str]) -> None:
        """Update the description of a card.

        Args:
            card_id: Card key.
            new_description: New description text or ``None`` to clear.

        Raises:
            CardNotFound: If the card does not exist.
        """
        self._ensure_card_exists(card_id)
        with self.conn:
            self.conn.execute("UPDATE cards SET description=? WHERE id=?", (new_description, card_id))

    def delete_card(self, card_id: int) -> None:
        """Delete a card.

        Args:
            card_id: Card key.

        Raises:
            CardNotFound: If the card does not exist.
        """
        self._ensure_card_exists(card_id)
        with self.conn:
            self.conn.execute("DELETE FROM cards WHERE id=?", (card_id,))

    def list_cards_in_status(self, status: str, board_key: Optional[int] = None) -> List[int]:
        """List card keys for a given status.

        Args:
            status: Column name (must be in :data:`STATUSES`).
            board_key: Board key. If omitted, uses default board.

        Returns:
            List[int]: Sorted list of card keys in the requested column.
        """
        self._validate_status(status)
        if board_key is None:
            board_key = self._get_default_board_id()
        self._ensure_board_exists(board_key)
        rows = self.conn.execute(
            "SELECT id FROM cards WHERE board_id=? AND status=? ORDER BY id",
            (board_key, status),
        ).fetchall()
        return [r["id"] for r in rows]

    def list_cards(self, board_key: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all cards on a board (helper for GUI).

        Args:
            board_key: Board key. If omitted, uses default board.

        Returns:
            List[Dict[str, Any]]: Each dict contains ``key``, ``title``, ``description``, ``status``.
        """
        if board_key is None:
            board_key = self._get_default_board_id()
        self._ensure_board_exists(board_key)
        rows = self.conn.execute(
            "SELECT id, title, description, status FROM cards WHERE board_id=? ORDER BY id",
            (board_key,),
        ).fetchall()
        return [
            {"key": r["id"], "title": r["title"], "description": r["description"], "status": r["status"]}
            for r in rows
        ]

    # --- Querying ---

    def get_card_details(self, card_id: int) -> Dict[str, Any]:
        """Fetch a single card’s details.

        Args:
            card_id: Card key.

        Returns:
            Dict[str, Any]: Keys: ``key``, ``board_key``, ``title``, ``description``, ``status``.

        Raises:
            CardNotFound: If the card does not exist.
        """

        self._ensure_card_exists(card_id)
        row = self.conn.execute(
            "SELECT id, board_id, title, description, status FROM cards WHERE id=?",
            (card_id,),
        ).fetchone()
        return {
            "key": row["id"],
            "board_id": row["board_id"],
            "board_key": row["board_id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
        }

    # --- Utilities ---

    def clear_kanban_database(self) -> None:
        """Remove the database and recreate an empty one.

        This is useful for test suite setup/teardown in Robot.
        """
        self.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Re-initialize a fresh DB at the same path
        self.__init__(self.db_path)

    def create_demo_kanban_data(self) -> None:
        """Populate a demo board with a few cards for classroom use.

        Behavior:
            * Creates a board named "Demo" and makes it the default.
            * Adds one "To Do", one "In Progress", and one "Done" card.
            * Adds a few extra "Backlog item #N" cards in "To Do".
        """
        board_id = self.create_board("Demo", make_default=True)
        self.create_card("Write README", "Draft basic docs", "To Do", board_id)
        self.create_card("Implement CRUD", None, "In Progress", board_id)
        self.create_card("Publish package", "Tag v0.1.0", "Done", board_id)
        for i in range(1, 4):
            self.create_card(f"Backlog item #{i}", None, "To Do", board_id)


    def get_board_summary(self, board_key: Optional[int] = None) -> Dict[str, int]:
        """Count cards per status for a board.

        Args:
            board_key: Board key. If omitted, uses default board.

        Returns:
            Dict[str, int]: Keys: ``"To Do"``, ``"In Progress"``, ``"Done"``, and ``"Total"``.
        """
        if board_key is None:
            board_key = self._get_default_board_id()
        self._ensure_board_exists(board_key)
        counts = {s: 0 for s in STATUSES}
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as c FROM cards WHERE board_id=? GROUP BY status",
            (board_key,),
        ).fetchall()
        for r in rows:
            counts[r["status"]] = r["c"]
        counts["Total"] = sum(counts.values())
        return counts

        # --- Assertions (Robot “Should …” style) ---


    def board_should_exist(self, board_id: int) -> bool:
        """Assert that a board exists.

        Returns:
            bool: True if assertion passes.

        Raises:
            AssertionError: If the board does not exist.
        """
        exists = self.board_exists(board_id)
        if not exists:
            raise AssertionError(f"Expected board {board_id} to exist.")
        return True


    def board_should_not_exist(self, board_id: int) -> bool:
        """Assert that a board does not exist.

        Returns:
            bool: True if assertion passes.

        Raises:
            AssertionError: If the board exists.
        """
        exists = self.board_exists(board_id)
        if exists:
            raise AssertionError(f"Expected board {board_id} not to exist.")
        return True


    def card_should_exist_in_column(
            self, card_id: int, status: str, board_key: Optional[int] = None
    ) -> bool:
        """Assert that a card is in the specified column (and optionally on a board).

        Args:
            card_id: Card key.
            status: Expected status.
            board_key: Optional expected board.

        Returns:
            bool: True if assertion passes.

        Raises:
            AssertionError: If the card is not in the expected column/board.
        """
        self._validate_status(status)
        details = self.get_card_details(card_id)
        if board_key is not None and details["board_key"] != board_key:
            raise AssertionError(f"Card {card_id} not in board {board_key}.")
        if details["status"] != status:
            raise AssertionError(f"Card {card_id} status is '{details['status']}', expected '{status}'.")
        return True


    def card_should_have_title(self, card_id: int, expected_title: str) -> bool:
        """Assert a card title equals the expected value.

        Returns:
            bool: True if assertion passes.

        Raises:
            AssertionError: If the title does not match.
        """
        details = self.get_card_details(card_id)
        if details["title"] != expected_title:
            raise AssertionError(f"Card {card_id} title '{details['title']}' != '{expected_title}'")
        return True


    def card_should_have_description(self, card_id: int, expected_description: str) -> bool:
        """Assert a card description equals the expected value.

        Returns:
            bool: True if assertion passes.

        Raises:
            AssertionError: If the description does not match.
        """
        details = self.get_card_details(card_id)
        if (details["description"] or "") != (expected_description or ""):
            raise AssertionError(
                f"Card {card_id} description '{details['description']}' != '{expected_description}'"
            )
        return True


    def number_of_cards_in_column_should_be(
            self, status: str, expected: int, board_key: Optional[int] = None
    ) -> bool:
        """Assert the number of cards in the given column matches.

        Args:
            status: Column name.
            expected: Expected count.
            board_key: Optional board key.

        Returns:
            bool: True if assertion passes.

        Raises:
            AssertionError: If counts differ.
        """
        self._validate_status(status)
        ids = self.list_cards_in_status(status, board_key)
        n = len(ids)
        if n != expected:
            raise AssertionError(f"Number of cards in '{status}' is {n}, expected {expected}.")
        return True
