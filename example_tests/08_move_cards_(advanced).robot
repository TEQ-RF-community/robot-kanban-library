*** Settings ***
Library    kanban_robot.KanbanLibrary
Library    Collections

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Keywords ***
Move Card Through Workflow
    [Arguments]    ${card_id}    ${board_id}

    Card Should Exist In Column    ${card_id}    To Do    board_key=${board_id}

    Update Card Status To          ${card_id}    In Progress
    Card Should Exist In Column    ${card_id}    In Progress    board_key=${board_id}

    Update Card Status To          ${card_id}    Done
    Card Should Exist In Column    ${card_id}    Done    board_key=${board_id}


*** Test Cases ***
Move Single Card Through ToDo_InProgress_Done
    ${board}=    Create Board    My Team Board    default=${True}
    Board Should Exist    ${board}

    ${card}=     Create Card    title=Ticket-1: Basic flow    description=Move across all columns    status=To Do    board_key=${board}
    Card Should Have Title          ${card}
    Card Should Exist In Column     ${card}    To Do    board_key=${board}

    Move Card Through Workflow      ${card}    ${board}

    ${summary}=    Get Board Summary    board_key=${board}
    Log    Summary after move: ${summary}


Move Multiple Cards Through Workflow
    ${board}=    Create Board    Team Kanban    default=${True}

    @{titles}=    Create List    Ticket-2: Setup    Ticket-3: Implement    Ticket-4: Review

    @{card_ids}=    Create List
    FOR    ${t}    IN    @{titles}
        ${cid}=    Create Card    title=${t}    description=Auto-created for flow test    status=To Do    board_key=${board}
        Append To List    ${card_ids}    ${cid}
    END

    Number Of Cards In Column Should Be    3    To Do    board_key=${board}

    FOR    ${cid}    IN    @{card_ids}
        Move Card Through Workflow    ${cid}    ${board}
    END

    Number Of Cards In Column Should Be    0    To Do         board_key=${board}
    Number Of Cards In Column Should Be    0    In Progress   board_key=${board}
    Number Of Cards In Column Should Be    3    Done          board_key=${board}


Default Board Card Flow
    ${b_default}=    Create Board    Default Board    default=${True}
    ${cid}=          Create Card     title=Ticket-5: Uses default board

    ${details}=      Get Card Details    ${cid}
    ${board_id}=     Get From Dictionary    ${details}    board_id

    Move Card Through Workflow    ${cid}    ${board_id}