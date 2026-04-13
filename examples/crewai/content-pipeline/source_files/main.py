from dotenv import load_dotenv

load_dotenv()

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field
import uuid

from crews.content_pipeline_crew import ContentPipelineCrew


class ContentPipelineState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    article: str = ""


class ContentPipelineFlow(Flow[ContentPipelineState]):
    initial_state = ContentPipelineState

    @start()
    def run_content_pipeline(self):
        print(f"Starting content pipeline for topic: {self.state.topic}")
        result = (
            ContentPipelineCrew().crew().kickoff(inputs={"topic": self.state.topic})
        )
        self.state.article = result.raw
        print("Content pipeline complete.")

    @listen(run_content_pipeline)
    def save_article(self):
        print("Saving article to file...")
        with open("output_article.md", "w") as f:
            f.write(self.state.article)
        print("Article saved to output_article.md")


def kickoff():
    flow = ContentPipelineFlow()
    flow.state.topic = "The Future of Renewable Energy in 2026"
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
