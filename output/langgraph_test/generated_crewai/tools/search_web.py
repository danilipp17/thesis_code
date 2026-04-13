"""
Auto-generated tool: search_web
Search the web for information on a given topic.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class search_webSchema(BaseModel):
    query: str = Field(description="")


class search_web(BaseTool):
    name: str = "search_web"
    description: str = """Search the web for information on a given topic."""
    args_schema: Type[BaseModel] = search_webSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: research_assistant.search_web

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: research_assistant.search_web"
        )
