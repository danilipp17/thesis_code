"""
Auto-generated CrewAI Flow: ShakespeareXPostFlow
"""

import dotenv
from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.shakespearean_xpost_crew.shakespearean_xpost_crew import ShakespeareanXPostCrew
from crews.xpost_review_crew.xpost_review_crew import XPostReviewCrew


class ShakespeareXPostFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    id: str = ""
    x_post: str = ""
    feedback: Optional[str] = None
    valid: bool = False
    retry_count: int = 0


class ShakespeareXPostFlow(Flow[ShakespeareXPostFlowState]):

    @start("retry")
    def generate_shakespeare_x_post(self):
        pass  # TODO: implement step logic

    @router()
    def evaluate_x_post(self):
        if self.state.retry_count > 3:
            return "max_retry_exceeded"
        
        result = XPostReviewCrew().crew().kickoff(inputs={"x_post": self.state.x_post})
        self.state.valid = result["valid"]
        self.state.feedback = result["feedback"]
        
        print("valid", self.state.valid)
        print("feedback", self.state.feedback)
        self.state.retry_count += 1
        
        if self.state.valid:
            return "complete"
        
        return "retry"

    @listen("complete")
    def save_result(self):
        pass  # TODO: implement step logic

    @listen("max_retry_exceeded")
    def max_retry_exceeded_exit(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = ShakespeareXPostFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
