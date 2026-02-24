
# Kanban Robot Library

A simple, classroom‑friendly **Kanban Board library** for **Robot Framework**, featuring:

- ✔️ SQLite backend (self-contained, no external files)
- ✔️ CRUD operations for Boards & Cards
- ✔️ Inline documentation suitable for Libdoc
- ✔️ Custom exceptions for test demonstrations
- ✔️ Optional PySide6 GUI for card movement
- ✔️ Easy installation via `pip install .` or `pip install ".[gui]"`


## 🚀 Features

### 🧱 Board Management
- Create Board
- Delete Board
- List Boards
- Make Board Default
- Board Should Exist / Should Not Exist

### 📝 Card Management
- Create Card
- Update Title / Description
- Update Card Status To
- Delete Card
- List Cards In Status

### 🔍 Queries & Assertions
- Get Card Details
- Get Board Summary
- Card Should Have Title / Description
- Card Should Exist In Column
- Number Of Cards In Column Should Be

### 🛠 Utilities
- Clear Kanban Database
- Close Kanban Database Connection
- Create Demo Kanban Data

---

## 📦 Building the Library

### Build the pip-installable library
```bash
python -m build
```

---

## 📦 Installation

### Install library only
```bash
pip install .
```

### Install with GUI support
```bash
pip install ".[gui]"
```

### Run GUI
```bash
kanban-gui
```

---

## 🧪 Example Robot Framework Test

```robot
*** Settings ***
Library    kanban_robot

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Board And Card Flow
    ${board}=    Create Board    My First Board    default=${True}
    Board Should Exist    ${board}

    ${c1}=    Create Card    title=Auth     status=To Do         boardkey=${board}
    ${c2}=    Create Card    title=Docs     status=In Progress   boardkey=${board}
    ${c3}=    Create Card    title=Release  status=Done          boardkey=${board}

    Update Card Status To   ${c1}    In Progress
    Card Should Exist In Column    ${c1}    In Progress

    Update Card Description        ${c1}    Must support JWT
    Card Should Have Description   ${c1}    Must support JWT

    ${summary}=    Get Board Summary    ${board}
    Log    ${summary}
```

---

## 📚 Documentation Generation

### Robot Framework Libdoc
```bash
python -m robot.libdoc kanban_robot KanbanLibrary.html
```

---

## 📝 License
MIT License — feel free to use this library for teaching, demos, or internal training.

