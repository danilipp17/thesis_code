"""
Auto-generated CrewAI Flow: ContentPipelineFlow
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from crews.content_pipeline_crew.content_pipeline_crew import ContentPipelineCrew


class ContentPipelineFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class ContentPipelineFlow(Flow[ContentPipelineFlowState]):

    @start()
    def run_content_pipeline(self):
        pass  # TODO: implement step logic

    @listen(run_content_pipeline)
    def save_article(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = ContentPipelineFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
