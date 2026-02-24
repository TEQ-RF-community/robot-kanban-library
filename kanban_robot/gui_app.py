"""
PySide6 GUI for demonstrating the Kanban Robot library.

Features:
    * Board selector; create boards; set default.
    * Three columns (To Do, In Progress, Done).
    * Drag-and-drop cards between columns.
    * Add / Delete cards.
    * Context menu (right-click) to move to any status + Edit...
    * Bottom grid of directional buttons that mirrors the board:
        - To Do → In Progress
        - In Progress ← / → (To Do / Done)
        - Done ← In Progress
    * Per-column counts in bold headers (e.g., "To Do (3)").
    * Keyboard shortcuts:
        - Ctrl+1 / Ctrl+2 / Ctrl+3  -> Move selection to: To Do/In Progress/Done
        - Ctrl+Left / Ctrl+Right    -> Move selection one column left/right
    * Double-click a card to edit title/description.
    * "Create Demo Data" to bootstrap a classroom scenario.
    * Counts shown live and on headers.

Run:
    kanban-gui
"""

from __future__ import annotations

import sys
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QListWidget, QListWidgetItem, QPushButton, QComboBox, QLabel,
    QInputDialog, QMessageBox, QSplitter, QMenu, QAbstractItemView
)

from .core import KanbanCore, STATUSES, ValidationError, KanbanError


STATUS_ORDER: List[str] = list(STATUSES)  # ["To Do", "In Progress", "Done"]


class CardList(QListWidget):
    """Column list with drag-and-drop, context menu, and inline edit via double-click."""
    def __init__(self, status: str, core: KanbanCore, parent=None):
        super().__init__(parent)
        self.status = status
        self.core = core

        # Drag & drop
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

        # Multi-select
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    # --- Drag & drop: persist new status for items now in this list ---
    def dropEvent(self, event):
        super().dropEvent(event)
        for i in range(self.count()):
            it = self.item(i)
            card_id = it.data(Qt.UserRole)
            try:
                self.core.update_card_status(card_id, self.status)
            except ValidationError as e:
                QMessageBox.critical(self, "Error", str(e))
        self.window().refresh_counts()

    # --- Context menu on right-click ---
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # Only enable move actions if something is selected
        selected = self.selectedItems()
        if selected:
            move_menu = menu.addMenu("Move to")
            actions = {}
            for s in STATUS_ORDER:
                act = move_menu.addAction(s)
                actions[act] = s
            edit_act = menu.addAction("Edit…")
        else:
            edit_act = None

        chosen = menu.exec(event.globalPos())
        if not chosen:
            return

        if edit_act and chosen == edit_act:
            # Edit the first selected item
            if selected:
                self.window().edit_card(selected[0])
            return

        if selected:
            # Move to selected status
            move_target = None
            # each chosen move action matches one entry in 'actions'
            for act, status in list(locals().get('actions', {}).items()):
                if chosen == act:
                    move_target = status
                    break
            if move_target:
                self.window().move_selected_to(move_target)

    # --- Inline edit on double click ---
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            return super().mouseDoubleClickEvent(event)
        self.window().edit_card(item)
        return True


class MainWindow(QWidget):
    """Main application window for the Kanban demo with grid controls and add-ons."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanban Board (kanban-robot)")
        self.core = KanbanCore()
        self.delete_all_boards_on_startup()
        self.current_board_id = None
        self.columns: Dict[str, CardList] = {}
        self.header_labels: Dict[str, QLabel] = {}
        self._build_ui()
        self._setup_shortcuts()
        self.load_boards()

    # ---------------- UI ----------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Top bar: board selector and actions
        top = QHBoxLayout()
        self.board_combo = QComboBox()
        self.board_combo.currentIndexChanged.connect(self.on_board_changed)

        btn_new_board = QPushButton("New Board")
        btn_new_board.clicked.connect(self.create_board)

        btn_set_default = QPushButton("Make Default")
        btn_set_default.clicked.connect(self.make_default_board)

        btn_demo = QPushButton("Create Demo Data")
        btn_demo.clicked.connect(self.create_demo)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)

        top.addWidget(QLabel("Board:"))
        top.addWidget(self.board_combo, 1)
        top.addWidget(btn_new_board)
        top.addWidget(btn_set_default)
        top.addWidget(btn_demo)
        top.addWidget(btn_refresh)
        root.addLayout(top)

        # Middle: columns in splitter
        splitter = QSplitter()
        for status in STATUS_ORDER:
            col = QWidget()
            v = QVBoxLayout(col)

            hdr = QLabel(f"<b>{status}</b>")  # counts will be appended later
            hdr.setTextFormat(Qt.RichText)
            hdr.setAlignment(Qt.AlignCenter)
            self.header_labels[status] = hdr

            lst = CardList(status, self.core)
            self.columns[status] = lst

            v.addWidget(hdr)
            v.addWidget(lst, 1)
            splitter.addWidget(col)
        root.addWidget(splitter, 1)

        # Bottom: grid layout with directional controls + general actions
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        # Row 0: Column headers to mirror visually (labels here are static captions)
        cap_todo = QLabel("To Do")
        cap_ip = QLabel("In Progress")
        cap_done = QLabel("Done")
        for cap in (cap_todo, cap_ip, cap_done):
            cap.setAlignment(Qt.AlignCenter)
        grid.addWidget(cap_todo, 0, 0)
        grid.addWidget(cap_ip,   0, 1)
        grid.addWidget(cap_done, 0, 2)

        # Row 1: Movement buttons per column (with arrows)
        # Left column (To Do): can move right → In Progress
        btn_to_ip = QPushButton("To Do → In Progress  ▶")
        btn_to_ip.setToolTip("Move selected cards to In Progress")
        btn_to_ip.clicked.connect(lambda: self.move_selected_to("In Progress"))
        grid.addWidget(btn_to_ip, 1, 0)

        # Middle column (In Progress): can move left ← To Do and right → Done
        row_mid = QHBoxLayout()
        btn_ip_to_todo = QPushButton("◀  To Do")
        btn_ip_to_todo.setToolTip("Move selected cards to To Do")
        btn_ip_to_todo.clicked.connect(lambda: self.move_selected_to("To Do"))

        btn_ip_to_done = QPushButton("Done  ▶")
        btn_ip_to_done.setToolTip("Move selected cards to Done")
        btn_ip_to_done.clicked.connect(lambda: self.move_selected_to("Done"))

        mid_container = QWidget()
        mid_container.setLayout(row_mid)
        row_mid.addWidget(btn_ip_to_todo)
        row_mid.addSpacing(8)
        row_mid.addWidget(btn_ip_to_done)
        grid.addWidget(mid_container, 1, 1)

        # Right column (Done): can move left ← In Progress
        btn_done_to_ip = QPushButton("◀  In Progress")
        btn_done_to_ip.setToolTip("Move selected cards to In Progress")
        btn_done_to_ip.clicked.connect(lambda: self.move_selected_to("In Progress"))
        grid.addWidget(btn_done_to_ip, 1, 2)

        # Row 2: General actions aligned beneath the grid
        actions = QHBoxLayout()
        btn_add = QPushButton("Add Card")
        btn_add.setToolTip("Create a new card in To Do on the current board")
        btn_add.clicked.connect(self.add_card)

        btn_del = QPushButton("Delete Selected")
        btn_del.setToolTip("Delete all selected cards (any column)")
        btn_del.clicked.connect(self.delete_selected)

        btn_counts = QPushButton("Update Counts")
        btn_counts.setToolTip("Recalculate and display counts")
        btn_counts.clicked.connect(self.refresh_counts)

        self.counts_lbl = QLabel("")
        actions.addWidget(btn_add)
        actions.addWidget(btn_del)
        actions.addWidget(btn_counts)
        actions.addStretch(1)
        actions.addWidget(self.counts_lbl)

        root.addLayout(grid)
        root.addLayout(actions)

    def _setup_shortcuts(self) -> None:
        """Keyboard shortcuts for moving selection quickly."""
        # Absolute moves
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.move_selected_to("To Do"))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.move_selected_to("In Progress"))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self.move_selected_to("Done"))

        # Relative moves (← to previous column, → to next column)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=lambda: self.move_selected_relative(-1))
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=lambda: self.move_selected_relative(+1))

    # ---------------- Data / UI sync ----------------

    def load_boards(self) -> None:
        self.board_combo.blockSignals(True)
        self.board_combo.clear()
        boards = self.core.list_boards()
        if not boards:
            self.core.create_board("Default", make_default=True)
            boards = self.core.list_boards()

        default_index = 0
        for b in boards:
            text = f"{b['name']} ({'default' if b['default'] else b['key']})"
            self.board_combo.addItem(text, b["key"])
            if b["default"]:
                default_index = self.board_combo.count() - 1

        self.board_combo.blockSignals(False)
        self.board_combo.setCurrentIndex(default_index)
        self.on_board_changed(default_index)

    def on_board_changed(self, index: int) -> None:
        self.current_board_id = self.board_combo.itemData(index)
        self.refresh()

    def refresh(self) -> None:
        if self.current_board_id is None:
            return
        for status, lst in self.columns.items():
            lst.clear()
        for card in self.core.list_cards(self.current_board_id):
            item = QListWidgetItem(f"#{card['key']}: {card['title']}")
            item.setData(Qt.UserRole, card["key"])
            self.columns[card["status"]].addItem(item)
        self.refresh_counts()

    def refresh_counts(self) -> None:
        summary = self.core.get_board_summary(self.current_board_id)
        # Update bottom counts label
        self.counts_lbl.setText(
            f"To Do: {summary['To Do']}   In Progress: {summary['In Progress']}   "
            f"Done: {summary['Done']}   Total: {summary['Total']}"
        )
        # Update per-column headers with counts
        for status in STATUS_ORDER:
            n = summary.get(status, 0)
            self.header_labels[status].setText(f"<b>{status} ({n})</b>")

    # ---------------- Commands ----------------

    def delete_all_boards_on_startup(self):
        """Delete all boards and recreate a fresh empty database on GUI startup."""
        try:
            # This calls the same method used in your Robot test suite
            self.core.clear_kanban_database()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset database:\n{e}")

    def create_board(self) -> None:
        name, ok = QInputDialog.getText(self, "New Board", "Board name:")
        if not ok or not name.strip():
            return
        try:
            self.core.create_board(name.strip(), make_default=False)
            self.load_boards()
        except KanbanError as e:
            QMessageBox.critical(self, "Error", str(e))

    def make_default_board(self) -> None:
        if self.current_board_id is None:
            return
        try:
            self.core.make_board_default(self.current_board_id)
            self.load_boards()
        except KanbanError as e:
            QMessageBox.critical(self, "Error", str(e))

    def add_card(self) -> None:
        if self.current_board_id is None:
            return
        title, ok = QInputDialog.getText(self, "Add Card", "Title:")
        if not ok or not title.strip():
            return
        desc, _ = QInputDialog.getMultiLineText(self, "Add Card", "Description (optional):")
        try:
            self.core.create_card(title.strip(), desc or None, "To Do", self.current_board_id)
            self.refresh()
        except KanbanError as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self) -> None:
        deleted_any = False
        for status, lst in self.columns.items():
            for item in lst.selectedItems():
                card_id = item.data(Qt.UserRole)
                try:
                    self.core.delete_card(card_id)
                    deleted_any = True
                except KanbanError as e:
                    QMessageBox.critical(self, "Error", str(e))
        if deleted_any:
            self.refresh()

    def move_selected_to(self, target_status: str) -> None:
        """Move all selected cards (across columns) to the target status."""
        if target_status not in STATUS_ORDER:
            QMessageBox.critical(self, "Error", f"Invalid target status: {target_status}")
            return
        selected_ids = []
        for status, lst in self.columns.items():
            for item in lst.selectedItems():
                cid = item.data(Qt.UserRole)
                selected_ids.append(cid)
        if not selected_ids:
            return
        moved_any = False
        for cid in selected_ids:
            try:
                self.core.update_card_status(cid, target_status)
                moved_any = True
            except KanbanError as e:
                QMessageBox.critical(self, "Error", str(e))
        if moved_any:
            self.refresh()

    def move_selected_relative(self, step: int) -> None:
        """Move selection one column left (-1) or right (+1) relative to current status."""
        if step not in (-1, +1):
            return
        selected_ids = []
        # We’ll compute each card's current status to decide its next one
        for status, lst in self.columns.items():
            for item in lst.selectedItems():
                cid = item.data(Qt.UserRole)
                selected_ids.append(cid)

        if not selected_ids:
            return

        moved_any = False
        for cid in selected_ids:
            try:
                details = self.core.get_card_details(cid)
                cur_status = details["status"]
                idx = STATUS_ORDER.index(cur_status)
                new_idx = max(0, min(len(STATUS_ORDER) - 1, idx + step))
                if new_idx != idx:
                    self.core.update_card_status(cid, STATUS_ORDER[new_idx])
                    moved_any = True
            except KanbanError as e:
                QMessageBox.critical(self, "Error", str(e))

        if moved_any:
            self.refresh()

    def edit_card(self, list_item: QListWidgetItem) -> None:
        """Double-click / context Edit… handler: edit title and description of a card."""
        card_id = list_item.data(Qt.UserRole)
        try:
            d = self.core.get_card_details(card_id)
        except KanbanError as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Edit title
        new_title, ok = QInputDialog.getText(self, "Edit Title", "Title:", text=d.get("title") or "")
        if not ok:
            return
        new_title = new_title.strip()
        if not new_title:
            QMessageBox.critical(self, "Error", "Title cannot be empty.")
            return

        # Edit description
        new_desc, ok2 = QInputDialog.getMultiLineText(
            self, "Edit Description", "Description:", text=d.get("description") or ""
        )
        if not ok2:
            return

        try:
            self.core.update_card_title(card_id, new_title)
            self.core.update_card_description(card_id, (new_desc or None))
            self.refresh()
        except KanbanError as e:
            QMessageBox.critical(self, "Error", str(e))

    def create_demo(self) -> None:
        try:
            self.core.create_demo_kanban_data()
            self.load_boards()
        except KanbanError as e:
            QMessageBox.critical(self, "Error", str(e))


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1280, 800)
    w.show()
    sys.exit(app.exec())
