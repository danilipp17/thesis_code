"""
Auto-generated CrewAI Flow: CodeReviewFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.code_review_crew.code_review_crew import CodeReviewCrew


class CodeReviewState(BaseModel):
    """Flow state — customize fields as needed."""
    code: str = ""
    report: str = ""


class CodeReviewFlow(Flow[CodeReviewState]):

    @start()
    def review(self):
        result = CodeReviewCrew().crew().kickoff()
        return result

    @listen(review)
    def publish(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = CodeReviewFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
