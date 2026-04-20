"""
Auto-generated tool: Character Counter Tool
Counts the number of characters in a given string.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class CharacterCounterToolSchema(BaseModel):
    text: str = Field(description="The string to count characters in.")


class CharacterCounterTool(BaseTool):
    name: str = "Character Counter Tool"
    description: str = """Counts the number of characters in a given string."""
    args_schema: Type[BaseModel] = CharacterCounterToolSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.CharacterCounterTool.CharacterCounterTool._run

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: tools.CharacterCounterTool.CharacterCounterTool._run"
        )
