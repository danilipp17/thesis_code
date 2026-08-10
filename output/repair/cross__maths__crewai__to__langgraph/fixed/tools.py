"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool
from typing import Any


@tool
def add(**kwargs) -> str:
    """add
    This is an addition function that adds 2 numbers together.
    Accepts either named args 'a' and 'b' or an 'input' string like "40,12".
    """
    a = kwargs.get("a")
    b = kwargs.get("b")
    if a is None or b is None:
        inp = kwargs.get("input")
        if isinstance(inp, str):
            # try comma or space separated
            parts = [p.strip() for p in inp.replace(",", " ").split() if p.strip()]
            if len(parts) >= 2:
                try:
                    a = float(parts[0]) if "." in parts[0] else int(parts[0])
                    b = float(parts[1]) if "." in parts[1] else int(parts[1])
                except Exception:
                    raise ValueError("Could not parse numbers from input string for add.")
        else:
            # try positional-style in kwargs (first two values)
            values = [v for k, v in kwargs.items() if k not in ("input",)]
            if len(values) >= 2:
                a, b = values[0], values[1]
    try:
        res = float(a) + float(b)
        # Return integer if both were ints
        if float(res).is_integer():
            return str(int(res))
        return str(res)
    except Exception as e:
        raise ValueError(f"Invalid arguments for add: {e}")


@tool
def subtract(**kwargs) -> str:
    """subtract
    Subtraction function.
    Accepts either named args 'a' and 'b' or an 'input' string like "10,3".
    """
    a = kwargs.get("a")
    b = kwargs.get("b")
    if a is None or b is None:
        inp = kwargs.get("input")
        if isinstance(inp, str):
            parts = [p.strip() for p in inp.replace(",", " ").split() if p.strip()]
            if len(parts) >= 2:
                try:
                    a = float(parts[0]) if "." in parts[0] else int(parts[0])
                    b = float(parts[1]) if "." in parts[1] else int(parts[1])
                except Exception:
                    raise ValueError("Could not parse numbers from input string for subtract.")
        else:
            values = [v for k, v in kwargs.items() if k not in ("input",)]
            if len(values) >= 2:
                a, b = values[0], values[1]
    try:
        res = float(a) - float(b)
        if float(res).is_integer():
            return str(int(res))
        return str(res)
    except Exception as e:
        raise ValueError(f"Invalid arguments for subtract: {e}")


@tool
def multiply(**kwargs) -> str:
    """multiply
    Multiplication function.
    Accepts either named args 'a' and 'b' or an 'input' string like "6,7".
    """
    a = kwargs.get("a")
    b = kwargs.get("b")
    if a is None or b is None:
        inp = kwargs.get("input")
        if isinstance(inp, str):
            parts = [p.strip() for p in inp.replace(",", " ").split() if p.strip()]
            if len(parts) >= 2:
                try:
                    a = float(parts[0]) if "." in parts[0] else int(parts[0])
                    b = float(parts[1]) if "." in parts[1] else int(parts[1])
                except Exception:
                    raise ValueError("Could not parse numbers from input string for multiply.")
        else:
            values = [v for k, v in kwargs.items() if k not in ("input",)]
            if len(values) >= 2:
                a, b = values[0], values[1]
    try:
        res = float(a) * float(b)
        if float(res).is_integer():
            return str(int(res))
        return str(res)
    except Exception as e:
        raise ValueError(f"Invalid arguments for multiply: {e}")
