"""
Some useful utils.
"""

from typing import List, Union

from math import log2, ceil


def int_to_bits(number: int, bits=None) -> List[bool]:
    """Convert integer to list of bits.

    Args:
        number (int): Number to convert.
        bits (int, optional): Number of bits. Defaults to number's bits.

    Returns:
        List[bool]: Resulting list of bits.
    """
    if not bits:
        bits = ceil(log2(number))

    return [(number >> bit) & 1 for bit in range(bits - 1, -1, -1)]
