"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """add
    Add two integers.
    """
    return int(a) + int(b)

@tool
def subtract(a: int, b: int) -> int:
    """subtract
    Subtract two integers.
    """
    return int(a) - int(b)

@tool
def multiply(a: int, b: int) -> int:
    """multiply
    Multiply two integers.
    """
    return int(a) * int(b)
