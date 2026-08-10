"""
Auto-generated tool: add
This is an addition function that adds 2 numbers together.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class addSchema(BaseModel):
    a: int = Field(description="")
    b: int = Field(description="")


class add(BaseTool):
    name: str = "add"
    description: str = """This is an addition function that adds 2 numbers together."""
    args_schema: Type[BaseModel] = addSchema

    def _run(self, **kwargs) -> int:
        """
        Implementation reference: main.add
        """
        # Expect kwargs to contain integers for 'a' and 'b'
        a = kwargs.get("a")
        b = kwargs.get("b")
        if a is None or b is None:
            raise ValueError("Missing required arguments 'a' and 'b'")
        return int(a) + int(b)
