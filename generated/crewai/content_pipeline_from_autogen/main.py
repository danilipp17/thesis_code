"""
Auto-generated CrewAI Flow: AutoGenV04Flow
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel




class AutoGenV04FlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class AutoGenV04Flow(Flow[AutoGenV04FlowState]):

    @start()
    def run_asyncio(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = AutoGenV04Flow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
