"""
Auto-generated CrewAI Flow: NewsPipeline
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from crews.editorial_team.editorial_team import editorial_team


class NewsPipelineState(BaseModel):
    """Flow state — customize fields as needed."""

    write_task_output: str = ""
    research_task_output: str = ""


class NewsPipeline(Flow[NewsPipelineState]):
    @start()
    def start_research(self):
        print("Starting research phase...")
        return "research_done"

    @router(start_research)
    def review_research(self):
        return "write_article"  # Routing directly for demonstration

    @listen(start_research)
    def write_article(self):
        print("Handing off to Editorial Team Crew...")
        # Actually execute the generated crew
        result = editorial_team().crew().kickoff()
        self.state.write_task_output = result.raw
        return result.raw


def kickoff():
    flow = NewsPipeline()
    final_output = flow.kickoff()
    print("\n==================================")
    print("FINAL OUTPUT:")
    print("==================================")
    print(final_output)


if __name__ == "__main__":
    kickoff()
