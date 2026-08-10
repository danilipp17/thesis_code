"""
Auto-generated AutoGen tool definitions.
"""

from typing import Any, Dict
import json
import re

# Import the real implementations
from tools.arithmetic import add as _add_impl
from tools.arithmetic import subtract as _subtract_impl
from tools.arithmetic import multiply as _multiply_impl


def _extract_numbers_from_obj(obj: Any):
    """
    Given various input shapes (str, dict, list, numbers), try to extract two numeric operands.
    Returns tuple (a, b). Raises ValueError if not found.
    """
    # If it's already numbers or dict-like
    if isinstance(obj, (int, float)):
        return obj, None
    if isinstance(obj, dict):
        # Common keys
        for k1, k2 in (("a", "b"), ("x", "y"), ("num1", "num2"), ("first", "second")):
            if k1 in obj and k2 in obj:
                return obj[k1], obj[k2]
        # If dict values contain numbers, take first two
        nums = [v for v in obj.values() if isinstance(v, (int, float))]
        if len(nums) >= 2:
            return nums[0], nums[1]
    if isinstance(obj, (list, tuple)):
        nums = [v for v in obj if isinstance(v, (int, float))]
        if len(nums) >= 2:
            return nums[0], nums[1]
    if isinstance(obj, str):
        s = obj.strip()
        # Try JSON
        try:
            parsed = json.loads(s)
            return _extract_numbers_from_obj(parsed)
        except Exception:
            pass
        # Find numbers in the string
        found = re.findall(r"-?\d+\.?\d*", s)
        if len(found) >= 2:
            a = float(found[0])
            b = float(found[1])
            # convert to int if possible
            if a.is_integer():
                a = int(a)
            if b.is_integer():
                b = int(b)
            return a, b
    raise ValueError(f"Could not extract two numeric operands from input: {obj!r}")


def add(input: Any) -> str:
    """
    add
    This is an addition function that adds 2 numbers together.

    Implementation reference: tools.arithmetic.add
    """
    try:
        a, b = _extract_numbers_from_obj(input)
        if b is None:
            raise ValueError("Need two operands for addition")
        result = _add_impl(int(a), int(b))
        return str(result)
    except Exception as e:
        # Return an error string that the calling system can inspect
        return f"ERROR in add: {e}"


def subtract(input: Any) -> str:
    """
    subtract
    Subtraction function.

    Implementation reference: tools.arithmetic.subtract
    """
    try:
        a, b = _extract_numbers_from_obj(input)
        if b is None:
            raise ValueError("Need two operands for subtraction")
        result = _subtract_impl(int(a), int(b))
        return str(result)
    except Exception as e:
        return f"ERROR in subtract: {e}"


def multiply(input: Any) -> str:
    """
    multiply
    Multiplication function.

    Implementation reference: tools.arithmetic.multiply
    """
    try:
        a, b = _extract_numbers_from_obj(input)
        if b is None:
            raise ValueError("Need two operands for multiplication")
        result = _multiply_impl(int(a), int(b))
        return str(result)
    except Exception as e:
        return f"ERROR in multiply: {e}"
