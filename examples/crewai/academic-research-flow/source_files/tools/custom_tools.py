from pydantic import BaseModel, Field
from crewai.tools import BaseTool

class SearchInput(BaseModel):
    query: str = Field(..., description="The query to search the academic database for.")

class AcademicSearchTool(BaseTool):
    name: str = "Academic Search Tool"
    description: str = "Search academic papers and journals to find relevant literature."
    args_schema: type[BaseModel] = SearchInput

    def _run(self, query: str) -> str:
        return f"Findings for {query}..."
