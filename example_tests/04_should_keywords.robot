*** Settings ***
Library    kanban_robot.KanbanLibrary

*** Test Cases ***
Cards Should Exist And Have Properties
    ${board}=    Create Board    Assertions Demo
    ${card}=     Create Card     title=Check This Card    description=Hello    status=To Do    board_key=${board}

    Card Should Exist In Column    ${card}    To Do    ${board}
    Card Should Have Title         ${card}    Check This Card
    Card Should Have Description   ${card}    Hello
