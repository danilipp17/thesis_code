"""
Auto-generated CrewAI Flow: ShakespeareXPostFlow
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from crews.shakespearean_xpost_crew.shakespearean_xpost_crew import ShakespeareanXPostCrew
from crews.xpost_review_crew.xpost_review_crew import XPostReviewCrew


class ShakespeareXPostFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class ShakespeareXPostFlow(Flow[ShakespeareXPostFlowState]):

    @start()
    def generate_shakespeare_x_post(self):
        pass  # TODO: implement step logic

    @router(generate_shakespeare_x_post)
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

    @listen(evaluate_x_post)
    def save_result(self):
        pass  # TODO: implement step logic

    @listen(evaluate_x_post)
    def max_retry_exceeded_exit(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = ShakespeareXPostFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
