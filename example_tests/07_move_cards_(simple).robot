*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Move Card Through Workflow
    ${board}=    Create Board    Workflow Demo
    ${card}=     Create Card     title=Move Me    board_key=${board}

    Update Card Status To    ${card}    In Progress
    Card Should Exist In Column    ${card}    In Progress    board_key=${board}

    Update Card Status To    ${card}    Done
    Card Should Exist In Column    ${card}    Done    board_key=${board}