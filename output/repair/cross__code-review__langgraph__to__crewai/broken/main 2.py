"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class CodeReviewState(BaseModel):
    """Flow state — customize fields as needed."""
    audit: str = ""
    code: str = ""
    messages: list = []
    review: str = ""
    summary: str = ""


class StateGraph(Flow[CodeReviewState]):

    @start()
    def code_reviewer(self):
        pass  # TODO: implement step logic

    @listen(code_reviewer)
    def security_auditor(self):
        pass  # TODO: implement step logic

    @listen(security_auditor)
    def review_summarizer(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
