"""
Auto-generated tool: web_search_tool

"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class web_search_toolSchema(BaseModel):
    pass


class web_search_tool(BaseTool):
    name: str = "web_search_tool"
    description: str = """"""
    args_schema: Type[BaseModel] = web_search_toolSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: 

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: "
        )
