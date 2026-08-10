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

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: main.multiply"
        )
