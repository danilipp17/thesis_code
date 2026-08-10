"""
Auto-generated tool: multiply
Multiplication function.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class multiplySchema(BaseModel):
    pass


class multiply(BaseTool):
    name: str = "multiply"
    description: str = """Multiplication function."""
    args_schema: Type[BaseModel] = multiplySchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.arithmetic.multiply

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: tools.arithmetic.multiply"
        )
