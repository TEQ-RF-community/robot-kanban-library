*** Settings ***
Library    kanban_robot.KanbanLibrary
Library    Collections

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection


*** Test Cases ***
Create And Use Board And Cards
    ${board}=    Create Board    My Board    default=${True}
    Board Should Exist    ${board}

    ${card1}=    Create Card    title=Plan sprint             description=Scope features    status=To Do          board_key=${board}
    ${card2}=    Create Card    title=Implement feature A     status=In Progress            board_key=${board}
    ${card3}=    Create Card    title=Write docs              description=API docs         status=Done            board_key=${board}

    Card Should Have Title          ${card1}
    Card Should Have Description    ${card3}

    ${todo_ids}=    List Cards In Status    To Do    board_key=${board}
    Log    To Do IDs: ${todo_ids}

    Number Of Cards In Column Should Be    1    To Do    board_key=${board}

    Update Card Status To    ${card2}    Done
    Number Of Cards In Column Should Be    2    Done    board_key=${board}

    ${summary}=    Get Board Summary    board_key=${board}
    Log    Summary: ${summary}

    Delete Card    ${card1}
    Number Of Cards In Column Should Be    0    To Do    board_key=${board}


Default Board Behavior
    ${b1}=    Create Board    Team A    default=${True}
    ${b2}=    Create Board    Team B    default=${False}

    Make Board Default    ${b2}

    ${c}=    Create Card    title=Unassigned task
    ${details}=    Get Card Details    ${c}
    ${board_id}=   Get From Dictionary    ${details}    board_id
    Should Be Equal As Integers    ${board_id}    ${b2}


List And Delete Boards
    ${boards}=    List Boards
    Log    Boards: ${boards}

    FOR    ${item}    IN    @{boards}
        Log    ${item}
    END

    ${first}=        Get From List         ${boards}    0
    ${first_key}=    Get From Dictionary   ${first}     key
    Delete Board               ${first_key}
    Board Should Not Exist     ${first_key}