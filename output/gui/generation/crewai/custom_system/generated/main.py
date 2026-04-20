"""
Auto-generated CrewAI Flow: NewsPipeline
"""

import dotenv
from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class NewsPipelineState(BaseModel):
    """Flow state — customize fields as needed."""
    write_task_output: str = ""
    research_task_output: str = ""


class NewsPipeline(Flow[NewsPipelineState]):

    @start()
    def start_research(self):
        pass  # TODO: implement step logic

    @listen()
    def review_research(self):
        pass  # TODO: implement step logic

    @listen(start_research)
    def write_article(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = NewsPipeline()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
