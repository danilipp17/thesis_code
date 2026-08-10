"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """add
    This is an addition function that adds 2 numbers together.
    """
    return int(a + b)

@tool
def subtract(a: int, b: int) -> int:
    """subtract
    Subtraction function.
    """
    return int(a - b)

@tool
def multiply(a: int, b: int) -> int:
    """multiply
    Multiplication function.
    """
    return int(a * b)
