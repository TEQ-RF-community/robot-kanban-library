*** Settings ***
Library    kanban_robot.KanbanLibrary
Suite Setup    Clear Kanban Database

*** Test Cases ***
Invalid Status Should Fail
    ${b}=    Create Board    Negative Demo
    ${c}=    Create Card     title=Test    board_key=${b}

    TRY
        Update Card Status To    ${c}    InvalidStatus
        FAIL    Updating to invalid status should have failed
    EXCEPT
        Log To Console    Invalid status correctly raised an error
    END
