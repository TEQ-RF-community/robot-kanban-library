*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Smoke
    ${board}=    Create Board    My Board    default=${True}
    ${c1}=       Create Card     title=Task A    status=To Do    board_key=${board}
    Number Of Cards In Column Should Be    1    To Do    board_key=${board}
