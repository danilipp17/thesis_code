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
    topic: str = "Agentic AI Frameworks"


class TechBlogFlow(Flow[TechBlogState]):

    @start()
    def write_blog(self):
        print("Kicking off TechBlogCrew...")
        result = TechBlogCrew().crew().kickoff(inputs={"topic": self.state.topic})
        # Save the raw crew result into flow state for later steps/listeners
        self.state.final_post = str(result.raw)
        return result

    @listen(write_blog)
    def publish(self):
        print("Tech blog complete:")
        print(self.state.final_post)


def kickoff():
    flow = TechBlogFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
