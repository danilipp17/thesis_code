"""Word count tool for content quality checks."""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class WordCountSchema(BaseModel):
    text: str = Field(description="The text to count words in.")


class WordCountTool(BaseTool):
    name: str = "Word Counter"
    description: str = "Counts the number of words in a given text."
    args_schema: Type[BaseModel] = WordCountSchema

    def _run(self, text: str) -> str:
        count = len(text.split())
        return f"Word count: {count}"
