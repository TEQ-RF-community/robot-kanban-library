*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Count Cards In Columns
    ${b}=    Create Board    Counting Demo
    Create Card    title=A    status=To Do        board_key=${b}
    Create Card    title=B    status=To Do        board_key=${b}
    Create Card    title=C    status=In Progress  board_key=${b}

    Number Of Cards In Column Should Be    2    To Do        board_key=${b}
    Number Of Cards In Column Should Be    1    In Progress  board_key=${b}
    Number Of Cards In Column Should Be    0    Done         board_key=${b}
