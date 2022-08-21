"""
Utilites for internal usage
"""

from typing import List


def int_to_bits(number: int, bits: int) -> List[bool]:
    """Convert integer to list of bits.

    Args:
        number (int): Number to convert
        bits (int): Number of bits

    Returns:
        List[bool]: Converter number
    """
    return [(number >> bit) & 1 for bit in range(bits - 1, -1, -1)]
