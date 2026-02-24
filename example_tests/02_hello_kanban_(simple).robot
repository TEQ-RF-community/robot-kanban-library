*** Settings ***
Library    kanban_robot.KanbanLibrary
Suite Setup    Clear Kanban Database

*** Test Cases ***
Hello Kanban
    ${board}=    Create Board    Classroom Board
    ${card}=     Create Card     title=Learn Robot Framework    board_key=${board}
    Log To Console    Created board ${board} and card ${card}
