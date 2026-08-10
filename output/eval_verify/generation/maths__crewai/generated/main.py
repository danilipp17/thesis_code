"""
Auto-generated CrewAI Flow: MathsFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.maths_crew.maths_crew import MathsCrew


class MathsState(BaseModel):
    """Flow state — customize fields as needed."""
    answer: str = ""
    query: str = ""


class MathsFlow(Flow[MathsState]):

    @start()
    def reason_and_act(self):
        result = MathsCrew().crew().kickoff()
        return result

    @listen(reason_and_act)
    def publish(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = MathsFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
