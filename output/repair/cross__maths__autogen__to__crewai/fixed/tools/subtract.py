"""
Auto-generated tool: subtract
Subtract two integers.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class subtractSchema(BaseModel):
    a: int = Field(description="")
    b: int = Field(description="")


class subtract(BaseTool):
    name: str = "subtract"
    description: str = """Subtract two integers."""
    args_schema: Type[BaseModel] = subtractSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: main.subtract

        Implemented to perform integer subtraction and return the difference as a string.
        """
        a = kwargs.get("a")
        b = kwargs.get("b")
        if a is None or b is None:
            raise ValueError("subtract tool requires 'a' and 'b' integer arguments")
        try:
            result = int(a) - int(b)
        except Exception as e:
            raise ValueError(f"Invalid arguments for subtract: {e}")
        return str(result)
