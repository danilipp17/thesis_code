"""
Auto-generated tool: Web Search
Search the web for information on a given query. Returns titles, snippets, and URLs of relevant results.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class WebSearchToolSchema(BaseModel):
    query: str = Field(description="The search query to execute.")
    num_results: int = Field(description="Number of results to return.")


class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = """Search the web for information on a given query. Returns titles, snippets, and URLs of relevant results."""
    args_schema: Type[BaseModel] = WebSearchToolSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.web_search.WebSearchTool._run

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: tools.web_search.WebSearchTool._run"
        )
