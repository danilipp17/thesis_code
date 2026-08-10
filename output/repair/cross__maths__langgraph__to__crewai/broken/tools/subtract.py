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

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: main.subtract

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: main.subtract"
        )
