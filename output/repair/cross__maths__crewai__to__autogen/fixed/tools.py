"""
Auto-generated AutoGen tool definitions.
"""

import json
import re
from typing import Any, Dict, Tuple, Union


def _extract_numbers_from_str(s: str) -> Tuple[float, float]:
    # Find numbers like -12, 3.4, 5
    nums = re.findall(r"-?\d+\.?\d*", s)
    if len(nums) >= 2:
        a = float(nums[0])
        b = float(nums[1])
        return a, b
    raise ValueError("Could not extract two numbers from string input")


def _get_two_numbers(input_data: Union[str, Dict[str, Any]]) -> Tuple[float, float]:
    # If dict-like, try common keys first
    if isinstance(input_data, dict):
        # Common key names
        for keys in (("a", "b"), ("x", "y"), ("num1", "num2"), ("n1", "n2")):
            if keys[0] in input_data and keys[1] in input_data:
                return float(input_data[keys[0]]), float(input_data[keys[1]])
        # Otherwise take first two numeric values
        numeric_vals = []
        for v in input_data.values():
            try:
                numeric_vals.append(float(v))
            except Exception:
                continue
        if len(numeric_vals) >= 2:
            return numeric_vals[0], numeric_vals[1]
        # If there is a single field that's a string expression, try to parse it
        for v in input_data.values():
            if isinstance(v, str):
                try:
                    return _extract_numbers_from_str(v)
                except Exception:
                    continue
        raise ValueError("Could not find two numeric values in dict input")

    # If a string, try to parse as JSON first
    if isinstance(input_data, str):
        s = input_data.strip()
        # try json
        try:
            parsed = json.loads(s)
            return _get_two_numbers(parsed)
        except Exception:
            # fallback to regex extraction
            return _extract_numbers_from_str(s)

    raise ValueError("Unsupported input type for parsing numbers")


def add(input: str) -> str:
    """
    add
    This is an addition function that adds 2 numbers together.

    Implementation reference: tools.arithmetic.add
    """
    try:
        a, b = _get_two_numbers(input)
        result = a + b
        # return integer if both are ints
        if result.is_integer():
            return str(int(result))
        return str(result)
    except Exception as e:
        # Provide an informative error string so the framework / LLM can see it
        return f"Error in add: {e}"


def subtract(input: str) -> str:
    """
    subtract
    Subtraction function.

    Implementation reference: tools.arithmetic.subtract
    """
    try:
        a, b = _get_two_numbers(input)
        result = a - b
        if result.is_integer():
            return str(int(result))
        return str(result)
    except Exception as e:
        return f"Error in subtract: {e}"


def multiply(input: str) -> str:
    """
    multiply
    Multiplication function.

    Implementation reference: tools.arithmetic.multiply
    """
    try:
        a, b = _get_two_numbers(input)
        result = a * b
        if result.is_integer():
            return str(int(result))
        return str(result)
    except Exception as e:
        return f"Error in multiply: {e}"
