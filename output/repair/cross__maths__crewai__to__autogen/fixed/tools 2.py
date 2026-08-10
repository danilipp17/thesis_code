"""
Auto-generated AutoGen tool definitions.
"""

import re
from typing import List


def _extract_ints(input: str) -> List[int]:
    """
    Helper to extract integers from an input string.
    Finds all occurrences of integers (including negative numbers).
    """
    if input is None:
        return []
    nums = re.findall(r"-?\d+", input)
    return [int(n) for n in nums]


def add(input: str) -> str:
    """
    add
    This is an addition function that adds 2 numbers together.

    Implementation reference: tools.arithmetic.add
    """
    nums = _extract_ints(input)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return str(a + b)
    raise ValueError("add expects at least two integers in the input string")


def subtract(input: str) -> str:
    """
    subtract
    Subtraction function.

    Implementation reference: tools.arithmetic.subtract
    """
    nums = _extract_ints(input)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return str(a - b)
    raise ValueError("subtract expects at least two integers in the input string")


def multiply(input: str) -> str:
    """
    multiply
    Multiplication function.

    Implementation reference: tools.arithmetic.multiply
    """
    nums = _extract_ints(input)
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        return str(a * b)
    raise ValueError("multiply expects at least two integers in the input string")
