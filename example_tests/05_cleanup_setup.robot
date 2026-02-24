*** Settings ***
Library     kanban_robot.KanbanLibrary
Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Suite Setup Creates A Clean Database
    ${board}=    Create Board    Test Setup Demo
    Board Should Exist    ${board}
