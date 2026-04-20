"""
Auto-generated CrewAI Flow: CodeReviewFlow
"""

import dotenv
from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.code_review_crew.code_review_crew import CodeReviewCrew


class CodeReviewFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    id: str = ""
    code: str = ""
    approved: bool = False
    feedback: Optional[str] = None
    retry_count: int = 0


class CodeReviewFlow(Flow[CodeReviewFlowState]):

    @start()
    def run_review(self):
        pass  # TODO: implement step logic

    @router()
    def check_quality_gate(self):
        if self.state.retry_count > 2:
            return "max_retries"
        
        self.state.retry_count += 1
        
        if self.state.approved:
            return "approved"
        
        return "needs_revision"

    @listen("approved")
    def handle_approved(self):
        pass  # TODO: implement step logic

    @listen("needs_revision")
    def handle_revision_needed(self):
        pass  # TODO: implement step logic

    @listen("max_retries")
    def handle_max_retries(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = CodeReviewFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
