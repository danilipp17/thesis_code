"""
tech-blog — CrewAI Flow variant.

Original-of-this-family. A linear three-step blog-writing pipeline:
research → write → edit. The Flow wraps a single TechBlogCrew that
runs the three tasks sequentially using YAML-configured agents and tasks.
"""

from crewai.flow.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.tech_blog_crew import TechBlogCrew

load_dotenv()


class TechBlogState(BaseModel):
    topic: str = "Agentic AI Frameworks"
    final_post: str = ""


class TechBlogFlow(Flow[TechBlogState]):
    """CrewAI Flow that orchestrates the TechBlogCrew."""

    @start()
    def write_blog(self):
        print("Kicking off TechBlogCrew...")
        result = TechBlogCrew().crew().kickoff(inputs={"topic": self.state.topic})
        self.state.final_post = str(result.raw)

    @listen(write_blog)
    def publish(self):
        print("Tech blog complete:")
        print(self.state.final_post)


def kickoff():
    TechBlogFlow().kickoff()


if __name__ == "__main__":
    kickoff()
