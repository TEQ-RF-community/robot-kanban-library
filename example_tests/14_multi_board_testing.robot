*** Settings ***
Library    kanban_robot.KanbanLibrary

*** Test Cases ***
Default Board Behavior
    Clear Kanban Database

    ${default}=    Create Board    Main
    ${other}=      Create Board    Secondary    default=False

    ${card}=       Create Card    title=Hello
    # Goes to the default board
    Card Should Exist In Column    ${card}    To Do    ${default}
