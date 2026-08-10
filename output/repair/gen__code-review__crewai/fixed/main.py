"""
Auto-generated CrewAI Flow: CodeReviewFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.code_review_crew.code_review_crew import CodeReviewCrew

CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""


class CodeReviewState(BaseModel):
    """Flow state — customize fields as needed."""
    code: str = CODE_TO_REVIEW
    report: str = ""


class CodeReviewFlow(Flow[CodeReviewState]):

    @start()
    def review(self):
        print("Kicking off CodeReviewCrew...")
        result = CodeReviewCrew().crew().kickoff(inputs={"code": self.state.code})
        # store textual/raw result into state for downstream steps / publishing
        try:
            self.state.report = str(result.raw)
        except Exception:
            # fallback to str(result)
            self.state.report = str(result)
        return result

    @listen(review)
    def publish(self):
        print("Code review complete:")
        print(self.state.report)


def kickoff():
    flow = CodeReviewFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
