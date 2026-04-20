"""
Auto-generated CrewAI Flow: EmailAutoResponderFlow
"""

import dotenv
from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.email_filter_crew.email_filter_crew import EmailFilterCrew


class EmailAutoResponderFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    emails: List[Email] = []
    checked_emails_ids: set[str] = set()


class EmailAutoResponderFlow(Flow[EmailAutoResponderFlowState]):

    @start("wait_next_run")
    def fetch_new_emails(self):
        pass  # TODO: implement step logic

    @listen(fetch_new_emails)
    def generate_draft_responses(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = EmailAutoResponderFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
