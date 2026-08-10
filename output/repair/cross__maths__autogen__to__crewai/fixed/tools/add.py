"""
Auto-generated tool: add
Add two integers.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class addSchema(BaseModel):
    a: int = Field(description="")
    b: int = Field(description="")


class add(BaseTool):
    name: str = "add"
    description: str = """Add two integers."""
    args_schema: Type[BaseModel] = addSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: main.add

        Implemented to perform integer addition and return the sum as a string.
        """
        a = kwargs.get("a")
        b = kwargs.get("b")
        if a is None or b is None:
            raise ValueError("add tool requires 'a' and 'b' integer arguments")
        try:
            result = int(a) + int(b)
        except Exception as e:
            raise ValueError(f"Invalid arguments for add: {e}")
        return str(result)
