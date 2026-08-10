"""
Auto-generated CrewAI Flow: TechBlogFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.tech_blog_crew.tech_blog_crew import TechBlogCrew


class TechBlogState(BaseModel):
    """Flow state — customize fields as needed."""
    final_post: str = ""
    topic: str = ""


class TechBlogFlow(Flow[TechBlogState]):

    @start()
    def write_blog(self):
        result = TechBlogCrew().crew().kickoff()
        return result

    @listen(write_blog)
    def publish(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = TechBlogFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
