from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from crews.code_review_crew import CodeReviewCrew


class CodeReviewState(BaseModel):
    code: str = ""
    approved: bool = False
    feedback: Optional[str] = None
    retry_count: int = 0


class CodeReviewFlow(Flow[CodeReviewState]):

    @start()
    def run_review(self):
        print("Starting code review...")
        result = (
            CodeReviewCrew()
            .crew()
            .kickoff(inputs={"code": self.state.code})
        )
        self.state.approved = result["approved"]
        self.state.feedback = result.get("summary", "")

    @router(run_review)
    def check_quality_gate(self):
        if self.state.retry_count > 2:
            return "max_retries"

        self.state.retry_count += 1

        if self.state.approved:
            return "approved"

        return "needs_revision"

    @listen("approved")
    def handle_approved(self):
        print("Code review PASSED.")
        print(f"Summary: {self.state.feedback}")

    @listen("needs_revision")
    def handle_revision_needed(self):
        print("Code review FAILED — changes requested.")
        print(f"Feedback: {self.state.feedback}")

    @listen("max_retries")
    def handle_max_retries(self):
        print("Maximum review iterations reached.")
        print(f"Last feedback: {self.state.feedback}")


def kickoff():
    flow = CodeReviewFlow()
    flow.state.code = '''
def process_user_input(data):
    result = eval(data)
    return result
'''
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
