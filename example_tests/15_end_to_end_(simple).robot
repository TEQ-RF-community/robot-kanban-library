*** Settings ***
Library    kanban_robot.KanbanLibrary

*** Test Cases ***
Full Kanban Flow Demo
    Clear Kanban Database
    ${board}=    Create Board    Classroom Demo

    ${c1}=    Create Card    title=Plan Lesson        status=To Do        board_key=${board}
    ${c2}=    Create Card    title=Prepare Slides    status=In Progress  board_key=${board}
    ${c3}=    Create Card    title=Teach Class       status=Done         board_key=${board}

    Number Of Cards In Column Should Be    1    To Do        board_key=${board}
    Number Of Cards In Column Should Be    1    In Progress  board_key=${board}
    Number Of Cards In Column Should Be    1    Done         board_key=${board}

    Show Board Columns    board_key=${board}