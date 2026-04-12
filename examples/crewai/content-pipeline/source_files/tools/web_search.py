"""Web search tool for the content pipeline."""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class WebSearchSchema(BaseModel):
    query: str = Field(description="The search query to execute.")
    num_results: int = Field(default=5, description="Number of results to return.")


class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = (
        "Search the web for information on a given query. "
        "Returns titles, snippets, and URLs of relevant results."
    )
    args_schema: Type[BaseModel] = WebSearchSchema

    def _run(self, query: str, num_results: int = 5) -> str:
        import os
        import requests

        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Error: SERPER_API_KEY not set."

        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
        )
        results = response.json().get("organic", [])
        output = []
        for r in results[:num_results]:
            output.append(f"- {r.get('title', '')}: {r.get('snippet', '')} ({r.get('link', '')})")
        return "\n".join(output) if output else "No results found."
