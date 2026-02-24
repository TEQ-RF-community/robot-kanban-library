*** Settings ***
Library    kanban_robot.KanbanLibrary

*** Keywords ***
Delete Board If Exists
    [Arguments]    ${name}
    ${boards}=    List Boards
    FOR    ${b}    IN    @{boards}
        IF    '${b["name"]}' == '${name}'
            Delete Board    ${b["key"]}
        END
    END

*** Test Cases ***
Hello Kanban
    Delete Board If Exists    Classroom Board

    ${board}=    Create Board    Classroom Board
    ${card}=     Create Card     title=Learn Robot Framework    board_key=${board}
    Log To Console    Created board ${board} and card ${card}
