
# Kanban Robot Library

A simple, classroom‑friendly **Kanban Board library** for **Robot Framework**, featuring:

- ✔️ SQLite backend (self-contained, no external files needed)
- ✔️ Clear & consistent API for Boards and Cards
- ✔️ Inline documentation suitable for Libdoc
- ✔️ Custom exceptions for teaching error handling
- ✔️ Optional PySide6 GUI for visualizing card movement
- ✔️ Easy installation via `pip install .` or `pip install ".[gui]"`

---

## 🚀 Features

### 🧱 Board Management
- Create Board
- Delete Board
- List Boards
- Make Board Default
- Board Should Exist
- Board Should Not Exist

### 📝 Card Management
- Create Card
- Update Card Title
- Update Card Description
- Update Card Status To
- Delete Card
- List Cards In Status

### 🔍 Queries & Assertions
- Get Card Details
- Get Board Summary
- Card Should Have Title
- Card Should Have Description
- Card Should Exist In Column
- Number Of Cards In Column Should Be

### 🛠 Utilities
- Clear Kanban Database
- Close Kanban Database Connection
- Create Demo Kanban Data

---

## 📦 Building the Library

### Build a pip-installable wheel / sdist
```bash
python -m build
```

---

## 📦 Installation

### Install the library only
```bash
pip install .
```

### Install with optional GUI support
```bash
pip install ".[gui]"
```

### Run the GUI
```bash
kanban-gui
```

---

## 🧪 Example Robot Framework Test
*(Updated for the simplified API)*

```robot
*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Board And Card Flow
    ${board}=    Create Board    My First Board    default=${True}
    Board Should Exist    ${board}

    ${c1}=    Create Card    title=Auth     status=To Do         board_key=${board}
    ${c2}=    Create Card    title=Docs     status=In Progress   board_key=${board}
    ${c3}=    Create Card    title=Release  status=Done          board_key=${board}

    Update Card Status To    ${c1}    In Progress
    Card Should Exist In Column    ${c1}    In Progress    board_key=${board}

    Update Card Description    ${c1}    Must support JWT
    Card Should Have Description    ${c1}    Must support JWT

    ${summary}=    Get Board Summary    board_key=${board}
    Log    ${summary}
```

### 🔑 API Notes
- Always pass board id using:
  ```robot
  board_key=${board}
  ```
- Use consistent status update signature:
  ```robot
  Update Card Status To    ${card_id}    ${status}
  ```
- Use consistent count assertion signature:
  ```robot
  Number Of Cards In Column Should Be    ${expected}    ${status}    board_key=${board}
  ```

---

## 📚 Documentation Generation

Generate keyword documentation using Robot Libdoc:

```bash
python -m robot.libdoc kanban_robot KanbanLibrary.html
```

---

## 📝 License
MIT License — free to use for teaching, demos, internal training, and academic purposes.
