"""
Auto-generated tool: multiply
Multiplication function.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class multiplySchema(BaseModel):
    a: int = Field(description="")
    b: int = Field(description="")


class multiply(BaseTool):
    name: str = "multiply"
    description: str = """Multiplication function."""
    args_schema: Type[BaseModel] = multiplySchema

    def _run(self, **kwargs) -> int:
        """
        Implementation reference: main.multiply
        """
        a = kwargs.get("a")
        b = kwargs.get("b")
        if a is None or b is None:
            raise ValueError("Missing required arguments 'a' and 'b'")
        return int(a) * int(b)
