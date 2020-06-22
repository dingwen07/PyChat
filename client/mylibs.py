
def confirm(prompt, default=False):
    """Get confirmation from the console

    Ask the user to confirm some operations through the console.

    Args:
        :param prompt: prompt
        :param default: return value of the method when input value is invalid
    Returns:
        Method returns Boolean value

    """

    print(prompt)
    answer = input('Do you sure? (Y/n) ').lower()
    if answer == 'y':
        return True
    elif answer == 'n':
        return False
    else:
        return default
