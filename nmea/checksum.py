"""
Handle NMEA checksums.
"""


def add(sentence: str) -> str:
    """
    Add a checksum to the given sentence.

    For example:
        >>> checksum_add("$GPVTG,2.95,T,,M,16.1,N,29.8,K")
        "$GPVTG,2.95,T,,M,16.1,N,29.8,K*5B"

    """
    if '*' in sentence:
        raise ValueError(f"Sentence already has a checksum: {sentence!r}")
    checksum = calculate(sentence)
    return f"{sentence}*{checksum:X}"


def calculate(sentence: str) -> int:
    """
    Calculate single-byte checksum of the given NMEA message.
    """
    # Drop sentence delimiters and any existing checksum
    inner, _, _ = sentence.partition('*')
    inner = inner[1:]

    # Calculate checksum
    inner_bytes = inner.encode('ascii', errors='strict')
    checksum = 0
    for b in inner_bytes:
        checksum ^= b
    return checksum


def verify(sentence: str) -> bool:
    """
    Raise exception if checksum of given message is invalid.

    The checksum is a hex byte at the end of a message after an asterix. It is
    calculated by taking the XOR of all the bytes between, but not including,
    the starting and ending characters '$' and '*'.

    Raises:
        ValueError:
            If no checksum found, of if checksum verification failed.

    Returns:
        True if no exception is raised.
    """
    sentence = sentence.strip()
    sentence, _, expected = sentence.partition('*')
    if not expected:
        raise ValueError(f"Given sentence has no checksum: {sentence!r}")

    expected = expected.upper()
    calculated = f"{calculate(sentence):X}"

    if expected != calculated:
        raise ValueError(
            'Checksum in sentence does not match that calculated: '
            f'0x{expected} != 0x{calculated}')

    return True
