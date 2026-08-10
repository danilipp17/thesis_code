"""
Auto-generated tool: multiply
Multiply two integers.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class multiplySchema(BaseModel):
    a: int = Field(description="")
    b: int = Field(description="")


class multiply(BaseTool):
    name: str = "multiply"
    description: str = """Multiply two integers."""
    args_schema: Type[BaseModel] = multiplySchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: main.multiply

        Implemented to perform integer multiplication and return the product as a string.
        """
        a = kwargs.get("a")
        b = kwargs.get("b")
        if a is None or b is None:
            raise ValueError("multiply tool requires 'a' and 'b' integer arguments")
        try:
            result = int(a) * int(b)
        except Exception as e:
            raise ValueError(f"Invalid arguments for multiply: {e}")
        return str(result)
