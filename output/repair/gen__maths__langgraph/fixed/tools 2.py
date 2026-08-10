"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool

@tool
def add(a: int, b: int):
    """add
    This is an addition function that adds 2 numbers together.
    """
    return a + b

@tool
def subtract(a: int, b: int):
    """subtract
    Subtraction function.
    """
    return a - b

@tool
def multiply(a: int, b: int):
    """multiply
    Multiplication function.
    """
    return a * b
