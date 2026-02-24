*** Settings ***
Library    kanban_robot.KanbanLibrary

Suite Setup     Clear Kanban Database
Suite Teardown  Close Kanban Database Connection

*** Test Cases ***
Show Board In Console
    ${b}=    Create Demo Kanban Data
    Show Board Columns    ${b}
