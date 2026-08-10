"""
Auto-generated tool: subtract
Subtraction function.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class subtractSchema(BaseModel):
    a: int = Field(description="")
    b: int = Field(description="")


class subtract(BaseTool):
    name: str = "subtract"
    description: str = """Subtraction function."""
    args_schema: Type[BaseModel] = subtractSchema

    def _run(self, **kwargs) -> int:
        """
        Implementation reference: main.subtract
        """
        a = kwargs.get("a")
        b = kwargs.get("b")
        if a is None or b is None:
            raise ValueError("Missing required arguments 'a' and 'b'")
        return int(a) - int(b)
