"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> str:
    """add
    Add two integers.
    """
    return str(int(a) + int(b))

@tool
def subtract(a: int, b: int) -> str:
    """subtract
    Subtract two integers.
    """
    return str(int(a) - int(b))

@tool
def multiply(a: int, b: int) -> str:
    """multiply
    Multiply two integers.
    """
    return str(int(a) * int(b))
