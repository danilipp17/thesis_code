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

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: main.add"
        )
