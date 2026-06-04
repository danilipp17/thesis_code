"""Arithmetic primitives exposed as CrewAI tools."""

from crewai.tools import tool


@tool("add")
def add(a: int, b: int) -> int:
    """This is an addition function that adds 2 numbers together."""
    return a + b


@tool("subtract")
def subtract(a: int, b: int) -> int:
    """Subtraction function."""
    return a - b


@tool("multiply")
def multiply(a: int, b: int) -> int:
    """Multiplication function."""
    return a * b
