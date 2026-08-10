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

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: main.add

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: main.add"
        )
