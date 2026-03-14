def clamp16(x):
    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return x
