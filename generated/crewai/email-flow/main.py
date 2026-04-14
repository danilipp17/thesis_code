"""
Auto-generated CrewAI Flow: EmailAutoResponderFlow
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from crews.email_filter_crew.email_filter_crew import EmailFilterCrew


class EmailAutoResponderFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    draft_responses_task_output: str = ""
    action_required_emails_task_output: str = ""
    filter_emails_task_output: str = ""


class EmailAutoResponderFlow(Flow[EmailAutoResponderFlowState]):

    @start()
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
