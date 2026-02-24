*** Settings ***
Library           kanban_robot.KanbanLibrary
Test Template     Status Should Be Created Correctly
Suite Setup       Setup Test Board
Suite Teardown    Close Kanban Database Connection

*** Variables ***
${BOARD}    None

*** Keywords ***
Setup Test Board
    Clear Kanban Database
    ${board}=    Create Board    Template Board
    Set Suite Variable    ${BOARD}    ${board}

*** Test Cases ***
Card A    A    To Do
Card B    B    In Progress
Card C    C    Done

*** Keywords ***
Status Should Be Created Correctly
    [Arguments]    ${title}    ${status}
    ${c}=    Create Card    title=${title}    status=${status}    board_key=${BOARD}
    Card Should Exist In Column    ${c}    ${status}    ${BOARD}
