*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Board And Card Flow
    ${board}=    Create Board    My First Board    default=${True}
    Board Should Exist    ${board}

    ${b_list}=   List Boards
    Log To Console    ${b_list}

    ${c1}=    Create Card    title=Implement Auth    status=To Do         board_key=${board}
    ${c2}=    Create Card    title=Write Docs       status=In Progress    board_key=${board}
    ${c3}=    Create Card    title=Ship Release     status=Done           board_key=${board}

    Card Should Exist In Column    ${c2}    In Progress    board_key=${board}
    Update Card Status To          ${c1}    In Progress
    Card Should Exist In Column    ${c1}    In Progress

    Update Card Title              ${c3}    v0.1.0 Published
    Card Should Have Title         ${c3}    v0.1.0 Published

    Update Card Description        ${c1}    Must support JWT
    Card Should Have Description   ${c1}    Must support JWT

    ${todo}=   List Cards In Status   To Do    ${board}
    Length Should Be    ${todo}    0
    # Alternatively:
    # Should Be Empty     ${todo}
    # ${n}=    Get Length    ${todo}
    # Should Be Equal As Integers    ${n}    0

    ${summary}=    Get Board Summary    ${board}
    Log    ${summary}
