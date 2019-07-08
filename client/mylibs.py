
def confirm(msg):
    """Get confirmation from the console

    Ask the user to confirm some operations through the console.

    Args:
        msg: String, store the message will be displayed in the console
    Returns:
        Method returns Boolean value
    """

    print(msg)
    answer = input('Do you sure? (Y/n) ')
    if answer == 'Y' or answer == 'y':
        return 1
    else:
        return 0
