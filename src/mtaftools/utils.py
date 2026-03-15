def clamp16(x: int) -> int:
    """
    Clamp an integer to the range of signed 16-bit PCM.
    Args:
        x (int): The integer to clamp.
    Returns:
        int: The clamped integer.
    """

    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return x
