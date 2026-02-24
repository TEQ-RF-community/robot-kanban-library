*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Visual Flow Demo (Console)
    ${board}=    Create Board    Classroom Board    default=${True}

    ${c1}=       Create Card     title=Card A    status=To Do    board_key=${board}
    ${c2}=       Create Card     title=Card B    status=To Do    board_key=${board}

    Show Board Columns           board_key=${board}

    Log To Console    \n-- Moving Card A to In Progress --
    Update Card Status To    ${c1}    In Progress
    Show Board Columns           board_key=${board}

    Log To Console    \n-- Moving Card A to Done, Card B to In Progress --
    Update Card Status To        ${c1}    Done
    Update Card Status To        ${c2}    In Progress
    Show Board Columns           board_key=${board}

    Log To Console    \n-- Moving Card B to Done --
    Update Card Status To        ${c2}    Done
    Show Board Columns           board_key=${board}
